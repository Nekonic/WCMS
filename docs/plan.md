# WCMS 개발 계획

> 완료된 버전 이력: `docs/CHANGELOG.md`
> v0.10.0 재작성 아키텍처·설계: `docs/REWRITE_DESIGN.md`
>
> v0.10.0의 첫 시도(TypeScript + Hono + Svelte)는 폐기됨. v0.10.0를 Django + Rust + C# + PostgreSQL로 재정의.

---

## 브랜치 구조

| 브랜치 | 내용 |
|--------|------|
| `main` | Flask v0.9.x — 프로덕션 운영 중. 치명적 버그만 핫픽스 |
| 재작성 브랜치 | v0.10.0 전체 재작성 — 대규모 공사 중 |

---

## [main] 긴급 버그 수정 (Flask v0.9.x)

> 재작성 전환 전까지 main에서만 처리. 수정 후 즉시 커밋.

현재 미해결 항목 없음.

---

## [v0.10.0] 전체 재작성 (Django + Rust + C# + PostgreSQL)

> 설계 단일 참조본: `docs/REWRITE_DESIGN.md`
> 원칙: 프로덕션 v0.9.x를 살려둔 채 한 조각씩 전환. 실습실 2개를 천연 카나리아로 활용.

### Phase 0 - 계약 동결 + 기반

- [-] 현재 클라이언트<->서버 동작을 계약으로 고정 (재연결, long-poll 형식, 명령 결과 스키마 등 엣지케이스 포함) — `tests/contract/` (45개, HTTP 레벨/재작성 재사용 가능). admin 계약은 재설계 대상이라 제외.
- [-] protobuf 스키마 정의 (PC<->게이트웨이 메시지, 공유 타입) — `proto/wcms/v1/` (common + realtime, protoc 검증). buf codegen 설정 포함.
- [-] PostgreSQL + Django 스캐폴드 + ORM 스키마/마이그레이션 — `backend/` (fleet/enrollment/commands/clientlogs, Django auth, env-driven DB + dev compose). Postgres 미기동 시 SQLite 폴백.
- [-] SQLite -> PostgreSQL 데이터 이관 스크립트 — `backend` 의 `migrate_legacy` 관리 명령 (+ 검증 테스트 2개). 레거시 machine_id -> Client.legacy_machine_id 보존.

### Phase 1 - Django 관리 백엔드

- [-] 관리자 인증/세션 (세션 쿠키 + CSRF) — `backend/accounts` login/logout/me/csrf (테스트 7)
- [-] admin REST API — PC 조회/명령/실습실+좌석레이아웃/등록토큰/버전/로그조회 완료
- [-] 명령 발행 + 감사 추적 (발행자/시각/대상/모드/결과) — `backend/commands` 발행/일괄/이력/감사 (테스트 9)
- [-] 신원 기준 rate limit — login/enroll throttle (DRF ScopedRateThrottle). 실시간 경로 per-client throttle 은 게이트웨이(Phase 2)
- [-] enrollment REST: PIN 인증 -> CSR -> client_id + 인증서 발급 — POST /api/client/enroll/ (자체 CA 서명, 테스트 8)
- [-] 로그 배치 업로드 수신 + `client_logs` 저장 — POST /api/client/logs/ (클라이언트 인증서 인증) + admin 조회 GET /api/logs/

### Phase 2 - Rust 실시간 게이트웨이

- [-] WS 서버 + 연결 레지스트리(권위 있는 presence) — `gateway/` (axum WS + DashMap, 재연결 supersede, 테스트 10)
- [ ] mTLS 클라이언트 인증
- [ ] ping/pong 생존 확인 + 죽은 소켓 즉시 오프라인 (WS ping 처리 완료; 주기 ping + 미응답 축출 남음)
- [ ] 명령 push(서버->PC) + 결과/heartbeat 수신 (push/수신 루프 기반 완료; Django 연동 남음)
- [ ] 명령 전달 모드(drop/queue + TTL + ack)
- [ ] Django<->Rust 경계 구현 (무상태 게이트웨이: Django 내부 API, 양방향)
- [-] async 안티패턴 점검(블로킹 호출 금지) — 전 경로 async, 블로킹 호출 없음

### Phase 3 - C# 클라이언트

- [ ] Windows Worker Service 골격 + 자가업데이트(REST 바이너리 교체)
- [ ] OS 의존 인터페이스 격리(ISystemInfo/ICommandRunner/IRegistryAccess/IWebSocketTransport/IClock)
- [ ] 키쌍 생성 + enrollment + 인증서 저장(ProgramData)
- [ ] WS 컨트롤 채널 + 4겹 재연결 방어(워치독, 전원/네트워크 이벤트, 백오프+jitter)
- [ ] 명령 실행기: 전원/메시지/프로세스/설치(Chocolatey)/계정/언어팩
- [ ] 시스템 정보 수집(WMI/레지스트리)
- [ ] 구조화 로그 + 서버 업로드 + critical WS push

### Phase 4 - 테스트 & 부하

- [ ] 재연결 상태머신 결정론 단위테스트(가짜 시계/transport)
- [ ] 명령 디스패치 단위테스트
- [ ] 헤드리스 클라이언트 코어 = 부하 시뮬레이터(N=80/200/500)
- [ ] 부하 테스트가 옛 드롭 시나리오(연결 램프업) 재현 + 통과 증명
- [ ] protobuf 계약 테스트
- [ ] Django pytest / Rust 통합 테스트

### Phase 5 - 카나리 전환

- [ ] 실습실 A PC를 신규 클라이언트+게이트웨이로 전환, 실습실 B는 Flask 유지
- [ ] 검증 후 실습실 B 전환

### Phase 6 - 프론트엔드 SPA

> API 계약 동결 후 본격 착수

- [ ] SvelteKit + 디자인 시스템(색감/UI 전면 개편)
- [ ] 페이지: 로그인 / PC 그리드 / PC 상세 / 실습실·좌석 편집 / 등록 토큰 / 버전 / 로그·네트워크 이벤트 / fleet health
- [ ] 컴포넌트 테스트(Vitest) + E2E(Playwright)

### Phase 7 - 관측성(프리미엄) + 정리

- [ ] Prometheus 메트릭(active connection 등) + Grafana
- [ ] 알림(연속 명령 실패 / 실습실 오프라인 / 재연결 폭주)
- [ ] `api/`(구 Hono 시도) 제거
- [ ] Flask 서버 디커미션

---

## 공통 - 인프라

- [ ] Docker compose (Postgres + Django + Rust + 프론트 + 단일 리버스 프록시)
- [ ] GitHub Actions: 빌드/배포 워크플로우
- [ ] `docs/ARCHITECTURE.md` 갱신(전환 완료 시점)
