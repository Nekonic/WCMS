# WCMS 개발 계획

> 완료된 버전 이력: `docs/CHANGELOG.md`

---

## [v0.10.0] - 전체 재작성 (TypeScript + Svelte)

### 배경

v0.9.x Flask 스택의 한계:
- 데코레이터 중첩(`@csrf.exempt`, `@limiter.limit`, `@require_admin`)으로 보안 동작 예측 어려움
- Jinja2 서버 렌더링 → 프론트/백 혼재로 AI 유지보수 어려움
- 프록시 환경(nginx → Apache2 → Flask)에서 세션/CSRF 버그 반복 발생

### 새 스택

| 역할 | 기술 |
|------|------|
| API 서버 | TypeScript + Hono (`api/`) |
| 요청 검증 | Zod |
| DB | SQLite (기존 스키마 그대로) + Drizzle ORM |
| 프론트엔드 | Svelte (`frontend/`) |
| 클라이언트 | Python + PyInstaller (변경 없음) |

### DB 스키마

기존 스키마 그대로 사용. Drizzle로 타입 생성만 추가.

```
admins
pc_registration_tokens
pc_info
pc_specs
pc_dynamic_info
commands
seat_layout
seat_map
network_events
client_versions
```

### 테스트

```bash
python manage.py test api   # vitest (루트에서 실행)
python manage.py test all   # api + server + client
```

---

### Phase 1 - API 서버 (Hono)

> 클라이언트(Windows 서비스)가 바라보는 엔드포인트 URL 호환 유지

#### 클라이언트 API `/api/client`

- [-] `POST   /api/client/register` — PC 등록 (PIN 인증)
- [-] `POST   /api/client/heartbeat` — 상태 업데이트
- [-] `GET    /api/client/commands` — 명령 대기 (Long-poll)
- [-] `POST   /api/client/commands/:id/result` — 명령 결과 제출
- [-] `POST   /api/client/offline` — 네트워크 오프라인 신호
- [-] `POST   /api/client/shutdown` — 종료 신호
- [-] `GET    /api/client/version` — 최신 클라이언트 버전 조회
- [-] `POST   /api/client/version` — 버전 등록 (GitHub Actions 토큰 인증)

#### 관리자 API - 인증

- [-] `POST   /api/admin/login` — 로그인 (세션 발급)
- [-] `POST   /api/admin/logout` — 로그아웃
- [-] `GET    /api/admin/me` — 현재 세션 확인

#### 관리자 API - PC 조회

- [-] `GET    /api/pcs` — PC 전체 목록 (필터 지원)
- [-] `GET    /api/pcs/public` — PC 기본 정보 (인증 불필요)
- [-] `GET    /api/pcs/duplicates` — 중복 호스트명 PC
- [-] `GET    /api/pcs/unverified` — 미검증 PC
- [-] `GET    /api/pcs/:id` — PC 상세 정보
- [-] `GET    /api/pcs/:id/history` — 네트워크 이벤트 기록
- [-] `DELETE /api/pcs/:id` — PC 삭제

#### 관리자 API - PC 명령

- [-] `POST   /api/pcs/:id/command` — 범용 명령 전송
- [-] `POST   /api/pcs/:id/shutdown` — 종료
- [-] `POST   /api/pcs/:id/restart` — 재시작
- [-] `POST   /api/pcs/:id/message` — 메시지 전송
- [-] `POST   /api/pcs/:id/kill-process` — 프로세스 종료
- [-] `POST   /api/pcs/:id/install` — 프로그램 설치
- [-] `POST   /api/pcs/:id/uninstall` — 프로그램 삭제
- [-] `POST   /api/pcs/:id/account/create` — Windows 계정 생성
- [-] `POST   /api/pcs/:id/account/delete` — Windows 계정 삭제
- [-] `POST   /api/pcs/:id/account/password` — 비밀번호 변경
- [-] `DELETE /api/pcs/:id/commands` — 명령 큐 삭제

#### 관리자 API - 일괄 명령

- [-] `GET    /api/commands/pending` — 대기 명령 목록
- [-] `POST   /api/commands/results` — 명령 결과 조회 (폴링)
- [-] `POST   /api/commands/bulk` — 여러 PC 동시 명령
- [-] `DELETE /api/commands/bulk` — 여러 PC 명령 큐 삭제

#### 관리자 API - 실습실

- [-] `GET    /api/rooms` — 실습실 목록
- [-] `POST   /api/rooms` — 실습실 생성
- [-] `PUT    /api/rooms/:id` — 실습실 수정
- [-] `DELETE /api/rooms/:id` — 실습실 삭제
- [-] `GET    /api/rooms/:room/layout` — 좌석 배치 조회
- [-] `POST   /api/rooms/:room/layout` — 좌석 배치 저장

#### 관리자 API - 등록 토큰

- [-] `GET    /api/admin/tokens` — 토큰 목록
- [-] `POST   /api/admin/tokens` — 토큰 생성
- [-] `DELETE /api/admin/tokens/:id` — 토큰 삭제

#### 관리자 API - 버전 관리

- [-] `GET    /api/admin/versions` — 클라이언트 버전 목록 (관리자용)
- [-] `DELETE /api/admin/versions/:id` — 버전 삭제

#### 관리자 API - 기타

- [-] `GET    /api/admin/processes` — 모든 PC 프로세스 목록

#### 설치 API `/install`

- [-] `GET    /install/install.cmd` — Windows Batch 스크립트
- [-] `GET    /install/install.ps1` — PowerShell 스크립트
- [-] `GET    /install/version` — 버전 조회 (→ /api/client/version 리다이렉트)

---

### Phase 2 - 프론트엔드 (Svelte)

> `frontend/` 디렉토리. `cd frontend && npm install && npm run dev`

#### 페이지 목록

- [-] 로그인 (`/login`)
- [-] 메인 — 실습실 선택 + PC 그리드 (`/`)
- [-] PC 모달 — 정보 + 명령 (메인 페이지 내 모달)
- [-] 실습실 관리 (`/rooms`)
- [-] 좌석 배치 편집기 (`/seats`)
- [-] 등록 토큰 관리 (`/tokens`)
- [-] 클라이언트 버전 관리 (`/versions`)
- [-] 서버 로그 / 네트워크 이벤트 (`/logs`)

---

### Phase 3 - 클라이언트 정리 (Python)

- [-] `executor.py` 분리: `client/commands/` 디렉토리로 명령별 파일 분리
- [-] `reporter.py` 생성: 명령 결과 서버 전송 헬퍼
- [-] 언어 설정: `PreferredUILanguageOverride` 레지스트리 키 유지 (v0.9.8 복원 확인됨)

---

### 공통 - 인프라

- [-] `CLAUDE.md` 작성 (아키텍처, 배포 환경, 주요 결정 사항)
- [-] `docs/API.md` v0.10.0 기준으로 재작성
- [-] GitHub Actions: API 테스트 + 빌드 워크플로우 (`deploy-api.yml`)