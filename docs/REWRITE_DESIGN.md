# WCMS v0.10.0 재작성 설계

> 아키텍처와 핵심 설계 결정의 단일 참조본. 단계별 작업 체크리스트는 `docs/plan.md`.
> v0.10.0의 첫 시도(TypeScript + Hono + Svelte)는 폐기됨. 본 문서가 v0.10.0의 재정의된 방향이다.
> 버전 명명: 안정화 전까지 1.0을 쓰지 않는다. 개발 버전은 0.x로 간다.

---

## 1. 배경과 목표

### 현재 스택(v0.9.x)의 한계

- Flask 데코레이터 중첩(`@csrf.exempt`, `@limiter.limit`, `@require_admin`)으로 보안 동작 예측 어려움. 실제로 CSRF가 전 블루프린트에서 비활성화된 상태.
- Jinja2 서버 렌더링 + 정적 JS에 `window.WCMS_*` 전역 주입으로 프론트/백 혼재.
- 프록시 환경(nginx -> Apache2 -> Flask)에서 세션/CSRF 버그 반복.
- 단일 스레드 개발 서버 + 블로킹 long-poll 구조의 동시성 한계(아래 5장 참조).

### 목표

1. 보안 - 명시적이고 검증된 인증/세션, 공개키 기반 클라이언트 신원.
2. 안정 운영 - 동시 연결에서 무너지지 않는 실시간 채널.
3. 관리 편의 - 중앙 로그 수집과 명령 감사로 운영 가시성 확보.
4. 학습/포트폴리오 품질.

### 규모 전제 (중요)

실습실 2개 / 실습실당 PC 약 40대 / 총 80여 대 / 동시 관리자 1~2명 / 유지보수 1인.

부하 자체는 작다. Rust, API 분리, PostgreSQL 선택은 **성능이 필요해서가 아니라** 보안/안정/학습/포트폴리오 품질이 동기다. 이 사실을 명시해 둔다. 향후 작업 시 "성능 때문"이라는 잘못된 전제로 과설계하지 말 것.

---

## 2. 목표 스택

| 역할 | 기술 |
|------|------|
| 관리(admin) 백엔드 | Django (+ DRF), Python |
| 실시간 게이트웨이 | Rust (tokio + axum/WebSocket) |
| DB | PostgreSQL |
| 프론트엔드 | SPA (프레임워크 미정, 9장 참조) + 디자인 시스템 |
| 클라이언트 | C# (.NET, Windows Worker Service) |
| 와이어 계약 | protobuf (Rust/C#/TS/Python 공유) |
| 배포 | Docker (compose) |

---

## 3. 아키텍처

```
                         ┌──────────────────────────┐
   80여 대 PC  ──WS──────│  Rust 실시간 게이트웨이    │
   (C# 클라이언트)        │  - WS 연결 레지스트리      │
        │                │  - presence/ping-pong     │
        │  ──REST──┐     │  - 명령 push / 결과 수신    │
        │          │     └─────────────┬────────────┘
        │          │                   │
   (enrollment,    │              PostgreSQL
    바이너리 다운,  │                   │
    로그 배치)      │     ┌─────────────┴────────────┐
        └──────────┼─────│  Django (admin API/인증)  │
                   │     │  - ORM, 마이그레이션 소유  │
   관리자 브라우저 ─┴─────│  - 명령 발행, 감사         │
   (SPA) ──REST──────────│  - admin 비즈니스 로직     │
                         └──────────────────────────┘
```

### 컴포넌트 책임

- **Django**: DB 스키마와 마이그레이션 단독 소유. admin REST API, 관리자 인증/세션, 명령 발행, 감사/조회, 비즈니스 로직. 장수명(long-lived) 연결은 절대 서빙하지 않는다.
- **Rust 게이트웨이**: 80여 개 WebSocket 연결을 한 프로세스에서 유지. 이 연결 레지스트리가 **권위 있는 presence**다. 명령 push, heartbeat/결과 수신, ping/pong 생존 확인.
- **C# 클라이언트**: Windows 서비스. WS 컨트롤 채널 유지, 명령 실행(전원/계정/언어/설치 등), 시스템 정보 수집, 자가업데이트.
- **PostgreSQL**: 단일 데이터 저장소. 두 백엔드가 공유.

### Django <-> Rust 경계 (결정: Rust 무상태 게이트웨이)

DB는 Django가 단독 소유. Rust는 DB에 직접 접근하지 않고 Django 내부 API로 통신한다.

- 명령 발행(아웃바운드): admin 명령 -> Django가 command row insert(영속/감사) -> Django가 Rust 내부 API 호출("client_id로 push") -> Rust가 해당 WS로 전달.
- 텔레메트리(인바운드): PC가 WS로 보낸 heartbeat/결과/로그 -> Rust가 Django 내부 API로 전달 -> Django가 영속화.
- presence: Rust가 in-memory 연결 레지스트리를 권위적으로 보유. 연결 open/close 시 Django 내부 API로 통지 -> Django가 is_online/network_events 갱신.
- 근거: Rust에 DB 결합이 없어 책임 분리가 명확하고 솔로 유지보수가 단순. 80대 규모라 내부 API 왕복 레이턴시는 무의미.
- 공통 원칙: **마이그레이션 소유권은 Django 하나로 못박는다.** 두 곳에서 스키마를 만지면 갈라진다.

---

## 4. 핵심 설계 결정

### 4.1 이벤트 기반 presence (wake 미감지 버그의 구조적 해결)

옛 구조는 타임아웃 스윕(백그라운드 스레드가 40초 무신호 시 오프라인) 방식이라, PC가 절전에서 깨면 half-open 소켓에 매달려 "실시간 미감지" 또는 "영구 stuck"이 발생했다.

새 모델은 presence를 **연결 생명주기 이벤트**로 뒤집는다.

```
WS 연결됨        -> 즉시 online   (push, 실시간)
끊김/pong 누락   -> 즉시 offline  (push, 실시간)
타임아웃 스윕    -> 게이트웨이 크래시 대비 백스톱으로만
```

4겹 방어:

1. **WS 양방향 ping/pong (10~15초 주기)**: 서버가 pong 2회 놓치면 소켓을 죽은 것으로 보고 즉시 오프라인. half-open을 수 분이 아니라 약 30초 내 감지.
2. **클라이언트 워치독 타이머**: 소켓 상태를 신뢰하지 않고, N초 내 성공 왕복(pong)이 없으면 강제로 연결을 폐기하고 새로 만든다.
3. **Windows 전원/네트워크 이벤트 능동 재연결**: C#에서 `SystemEvents.PowerModeChanged`(Resume), `NetworkChange.NetworkAddressChanged` 구독. 깨어나는 즉시 기존 연결 폐기 + 재연결. 타임아웃을 기다리지 않는다.
4. **재연결 백오프 + jitter**: 80대가 동시에 깰 때(수업 시작) 서버를 동시에 때리지 않도록 jitter.

### 4.2 공개키 기반(PKC) 클라이언트 신원·인증

개념 전환: **하드웨어 속성(MAC, 호스트명)은 신원이 아니라 메타데이터다.** 신원은 서버가 발급한 영속 ID.

```
enrollment(최초 1회):
  PC가 키쌍 생성 -> PIN(단기·일회성) 인증으로 CSR 제출
  -> 서버가 영속 client_id(UUID) + 클라이언트 인증서 발급
  -> 개인키와 client_id를 C:\ProgramData\WCMS\ 에 저장(재부팅·NIC변경 생존)

이후 모든 WS/REST:
  클라이언트 인증서로 mTLS 인증 (또는 개인키로 연결 챌린지 서명)
  서버는 clients 테이블의 인증서 상태로 검증 -> 수락/거부
  취소(revoke) = 상태 플래그 -> 다음 재연결부터 거부
```

- 재설치/재이미징 시 개인키가 소실되면 새 PIN으로 재enrollment -> 새 client_id 발급. 자동 병합은 위험(서로 다른 PC 병합 가능)하므로 금지. 대신 admin UI가 "호스트명·좌석 동일한 기존 client 있음, 교체?"를 제안. 이것이 중복 레코드 버그의 근본 해결.
- 인증서 갱신/폐기: 장기 인증서(2년) + DB 상태 기반 즉시 폐기. Rust가 매 연결마다 `clients` 상태(active/revoked)를 확인하므로 CRL/OCSP 같은 PKI 인프라 불필요(폐기 = 플래그). 만료 임박 시 클라이언트가 재CSR로 자동 재발급.
- **admin 인증은 별개 스킴**: Django 세션 쿠키 + CSRF(SameSite). 클라이언트 인증서 스킴과 섞지 않는다.

### 4.3 하이브리드 전송

- **WebSocket(라이브 컨트롤 플레인)**: presence/liveness, 명령 push(서버->PC), 명령 결과·heartbeat 텔레메트리(PC->서버), 실시간 상태.
- **REST(부트스트랩·벌크)**: enrollment(세션·토큰 없는 상태), 자가업데이트 바이너리 다운로드, `/install/*` 스크립트, 로그 배치 업로드.

### 4.4 명령 전달 모드 (선택 가능)

각 명령에 전달 정책을 부착한다.

- `drop_if_offline`(at-most-once): 연결 안 돼 있으면 버리고 "오프라인, 미전송" 표시. 시간 민감 명령(종료/재시작/메시지)의 기본값.
- `queue`(at-least-once): pending으로 저장, 재연결 시 게이트웨이가 drain해서 push. TTL(`expires_at`) 동반. 설치/계정/설정 등 "언젠가는 꼭 적용" 명령의 기본값.
- exactly-once는 약속하지 않는다. at-least-once + 멱등 핸들러 + ack가 현실적 천장.

ack 생명주기(실행 결과와 분리):

```
pending -> sent -> executing -> completed | failed | expired
```

"sent 후 ack 없음"은 다음 재연결 때 재전송. at-most-once가 안전한 이유는 4.1의 이벤트 기반 presence로 online 판정이 신뢰 가능해졌기 때문.

타입별 기본값(admin UI에서 명령별 override 가능):

- `drop_if_offline`: shutdown, restart, message, kill_process, execute(임의 명령)
- `queue` + TTL 24h: install, uninstall, 계정 생성/삭제/비번변경, download

### 4.5 신원 기준 rate limit

옛 시스템은 per-IP rate limit이라, 80대가 프록시 뒤 단일 IP로 보여 정상 등록이 차단됐다(핫픽스 `1f04967`). 새 설계는 **클라이언트 신원(인증서/토큰) 기준**으로 제한한다. WS는 연결이 1회뿐이라 폴링 rate limit 자체가 거의 무의미해지는 것도 이점.

### 4.6 계약 우선 (protobuf)

언어가 4개(Django/Rust/C#/프론트)로 갈라지면 와이어 계약이 최대 회귀 지점이다. PC<->Rust(WS), 그리고 핵심 메시지를 **protobuf로 한 곳에 정의** -> 각 언어 타입 자동 생성. 계약 변경이 컴파일 단계에서 잡히게 한다.

---

## 5. 반드시 피할 안티패턴 (연결 드롭 버그의 교훈)

옛 버그("1대는 되는데 4~5대에서 전부 끊김")의 원인은 **단일 스레드 개발 서버 + 30초 블로킹 long-poll**이었다(`server/app.py:448`의 `app.run()`에 `threaded` 없음, `server/api/client.py:276`의 `time.sleep(0.5)` 루프). 한 클라이언트의 long-poll이 유일한 스레드를 점유해 나머지 연결이 큐에 쌓여 타임아웃됐다.

새 스택에서 같은 클래스의 버그를 막기 위한 철칙:

- **async 핸들러 안의 블로킹 호출 금지(Rust)**: 동기 DB 드라이버나 `std::thread::sleep`를 async 컨텍스트에서 부르면 tokio 워커가 통째로 멈춰 동일 증상 재현. sqlx(async) 사용, 블로킹 작업은 `spawn_blocking`.
- **Django는 장수명 연결을 서빙하지 않는다**: 모든 지속 연결은 Rust 게이트웨이로. Django는 짧은 REST 요청만.
- **per-IP rate limit 금지**: 신원 기준으로(4.5).
- **단일 Rust 게이트웨이가 연결 레지스트리를 소유**: 권위 있는 presence를 한 곳에 둔다.

---

## 6. 데이터 / 스키마 방향

- PostgreSQL 단일 저장소. Django ORM이 스키마/마이그레이션 단독 소유.
- 기존 SQLite 데이터는 마이그레이션 스크립트로 이관.
- 주요 테이블(방향):
  - `clients` - 영속 client_id, 공개키/인증서, 상태(enrolled/revoked)
  - `enrollment_tokens` - PIN(단기·일회성/재사용)
  - `pc_info` / `pc_specs` / `pc_dynamic_info` - 식별/정적/동적 텔레메트리
  - `commands` - 큐. `delivery_mode`, `expires_at`, `issuer(admin_id)`, ack 상태 컬럼 추가
  - `client_logs` - 수집 로그(보존기간 설정)
  - `network_events` - 연결 전이(연결/끊김/재연결 + 사유)
  - `rooms` / `seat_layout` / `seat_map` - 실습실/좌석
  - `client_versions` - 클라이언트 버전
  - `admins` - 관리자

---

## 7. 테스트 & 부하 전략

- **OS 의존을 인터페이스 뒤로 격리(C#)**: `ISystemInfo`, `ICommandRunner`, `IRegistryAccess`, `IWebSocketTransport`, `IClock` 등. 명령 디스패치 로직과 **재연결 상태머신**을 가짜 시계/transport로 결정론적 단위테스트. 버그가 사는 곳이라 최우선.
- **헤드리스 클라이언트 코어 = 부하 시뮬레이터**: OS 호출을 가짜로 바꾼 코어 N개를 실제 서버에 연결. 단위테스트용 코어가 부하테스트 하니스로 재활용. N=80/200/500 한계 탐색, CI에서도 실행 가능.
- **부하 테스트는 옛 실패 시나리오(연결 수 램프업)를 재현**해 새 설계가 안 무너짐을 증명한다. 회귀 가드.
- protobuf 계약 테스트(언어 간 타입 일치).
- 계층별: Django `pytest-django` + API 계약 테스트 / Rust `cargo test` + WS 통합 테스트 / 프론트 Vitest + Playwright.
- 실제 OS 통합(WMI/레지스트리/언어팩)은 VM 통합 테스트로 검증(운영자가 수행).

---

## 8. 보안 모델 요약

- 클라이언트: 공개키 기반 신원 + mTLS(4.2). enrollment에서만 PIN 사용.
- 관리자: Django 세션 + CSRF.
- rate limit: 신원 기준(4.5).
- 명령 감사: 모든 명령에 발행자/시각/대상/모드/결과/소요시간 기록.
- 전송: TLS. WS도 TLS 위.

---

## 9. 관측성

필수(적은 노력, 가치 대부분) - Postgres 테이블 + admin UI로 충분:

- 클라이언트 로그 수집: 구조화 JSON, REST 배치 업로드, critical은 WS 즉시 push.
- 명령 감사 추적: 8장.
- 연결 이벤트 로그: connect/disconnect/reconnect를 사유와 함께. 프로덕션 드롭 버그 재발 진단의 핵심 데이터.
- fleet health 뷰: 온/오프라인 수, 명령 실패 중인 PC, 미체크인 PC, 버전 분포.

프리미엄(코어 완성 후, 포트폴리오):

- Rust 게이트웨이 Prometheus 메트릭(active connection 수 등), Django 요청 메트릭, Grafana.
- 알림: 연속 명령 실패 / 실습실 전체 오프라인 / 재연결 폭주 시 webhook·메일.

보존 기간: `client_logs` 90일 / `network_events` 90일 / 명령 감사 1년. Postgres 파티셔닝 + 주기 삭제 잡.

프론트엔드: **SvelteKit**. SPA + 디자인 시스템 + 색감/UI 전면 개편 + 컴포넌트(Vitest)/E2E(Playwright) 테스트. API 계약 동결 후 본격 착수.

---

## 10. 배포

- Docker(compose): Postgres + Django + Rust 게이트웨이 + 프론트 + 단일 리버스 프록시.
- 옛 프록시 체인(nginx -> Apache2 -> Flask)의 세션/CSRF 고통을 단일 리버스 프록시로 정리.
- 시크릿(DB 크리덴셜, 서명키, 업데이트 토큰)은 환경변수/도커 시크릿.

---

## 11. 미정 결정 항목

현재 없음. 결정 요약(본문 반영됨):

- 프론트엔드 = SvelteKit (9장)
- Django <-> Rust = Rust 무상태 게이트웨이, Django 내부 API (3장)
- 명령 전달 기본값 = 타입별 drop/queue + 명령별 override (4.4)
- 로그 보존 = client_logs/network_events 90일, 감사 1년 (9장)
- 인증서 = 장기(2년) + DB 상태 기반 폐기, 자동 재발급 (4.2)

---

## 12. 폐기/정리 대상

- 이전 v0.10.0 시도(`api/` Hono TypeScript) - 본 재작성으로 대체. 단계 후반에 제거.
- Flask 서버 - 전환 완료 후 디커미션.
