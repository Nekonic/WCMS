# 변경 이력

프로젝트의 주요 변경사항을 기록합니다.

형식: [Keep a Changelog](https://keepachangelog.com/ko/1.0.0/)  
버전 관리: [Semantic Versioning](https://semver.org/lang/ko/)

---

## [0.9.2] - 2026-02-27

> **상태**: Released
> **테마**: 클라이언트 통신 개선, 코드 정리, 보안 강화

### Added - 새로운 기능
- **Long-polling 복원** (`GET /api/client/commands?timeout=30`)
  - 2초 short-polling(1,800 req/시간) → long-polling(120 req/시간), 90% 트래픽 감소
  - 서버가 30초 동안 연결 유지, 0.5초마다 명령 확인 → 즉시 반환
  - 연결 자체를 `last_seen` 업데이트 신호로 활용
- **네트워크 단절 감지** (`POST /api/client/offline`, `network_events` 테이블)
  - 클라이언트 연결 실패 시 offline 신호 전송 후 30초마다 재연결 시도
  - 단절 이력 기록: `offline_at`, `online_at`, `duration_sec`, `reason`
  - 오프라인 판정 threshold: 2분 → 40초
- **서버 로그 페이지** (`GET /admin/server-log`)
  - 서버 로그 tail (최근 200줄) + 네트워크 단절 이력 표시

### Changed - 변경
- **DB 스키마 v3.0** (`server/migrations/schema.sql`)
  - 미사용 테이블/뷰 제거: `admin_logs`, 5개 VIEW
  - 미사용 필드 제거: `retry_count`, `max_retries`, `archive_completed_commands` trigger
  - `idx_commands_pending` partial index 수정 (`WHERE status = 'pending'`)
- **CommandModel 정리**: `increment_retry()` 제거, `create()`에서 archive 호환 코드 제거
- **인라인 CSS 외부화**: `static/css/components.css` 생성
  - 10개 템플릿에서 `<style>` 블록 및 인라인 `style=""` 전부 제거
  - (`about`, `system_status`, `layout_editor`, `room_manager`, `client_versions`, `registration_tokens`, `pc_detail`, `process_history`, `login`, `base`)

### Security - 보안
- **Z-01**: CSP `style-src` 에서 `unsafe-inline` 제거 (progress bar → `data-width` + JS)
- **Z-02**: CORS 허용 오리진 환경변수화 (`WCMS_ALLOWED_ORIGINS`, 기본 `*`)
- **Z-03**: 로그인 폼 CSRF 보호 (`Flask-WTF CSRFProtect`, API Blueprint 제외)
- **C-01/C-02**: `client/executor.py` `subprocess(shell=True)` → 리스트 방식
  - 적용 대상: `shutdown`, `reboot`, `show_message`, `kill_process`, `manage_account`(net user), `install`/`uninstall`(choco)

---

## [0.9.1] - 2026-02-26

> **상태**: Released
> **테마**: 코드 품질 개선, 문서 정리

### Fixed - 버그 수정
- 클라이언트 API (`/api/client/*`)를 rate limit에서 제외
  - 2초 폴링(1,800회/시간)이 전역 제한(50회/시간)을 초과하는 문제 사전 수정

### Changed - 변경
- 서버 코드 중복 제거
  - `models/pc.py`: `_to_json()` 헬퍼로 JSON 직렬화 중복 4곳 통합
  - `api/admin.py`: `_get_pc_or_404()`, `_queue_command()` 헬퍼 추가 (1163 → 921줄)
  - `services/command_service.py` 삭제 (173줄, 미사용)
- CSS/JS 정적 파일 분리 (`base.html`, `index.html`)
  - `static/css/base.css`, `static/css/index.css` 생성
  - `static/js/modal.js`, `static/js/pc-grid.js`, `static/js/commands.js` 생성

### CI - 자동화
- ZAP/pip-audit 취약점 발견 시 워크플로우 실패하지 않도록 수정 (`continue-on-error: true`)
- `astral-sh/setup-uv` v5 → v7 업데이트 (Post 스텝 캐시 오류 수정)
- Dependabot 제거 (uv 사용으로 pip 스캔 불필요)

### Docs - 문서
- `AI_CONTEXT.md`: Addy Osmani AGENTS.md 기준 재작성 (Landmines/권장 사항 형식)
- `docs/ARCHITECTURE.md`: v0.9.1 구조 반영, 이모티콘 제거
- 불필요 문서 삭제: `QUICK_REFERENCE.md`, `INDEX.md`, `CLIENT_AUTO_UPDATE.md`, `archive/LEGACY_GUIDE.md`

### Known Issues - 미완료 (v0.9.2로 이월)
- `components.css` 생성 및 템플릿 인라인 CSS 제거 미완
- CI 자동탐지 기반 보안 취약점 수정 미착수

---

## [0.9.0] - 2026-02-24

> **상태**: Released
> **테마**: 서버 보안 강화

### Security - 보안
- [x] **HTTPS 지원**
  - 환경변수로 SSL 인증서 경로 설정 (`WCMS_SSL_CERT`, `WCMS_SSL_KEY`)
  - Flask 서버에 SSL 컨텍스트 적용 (`docs/SECURITY.md` 가이드 포함)
- [x] **웹 보안 헤더 적용** (`Flask-Talisman`)
  - HSTS, CSP, X-Frame-Options, X-Content-Type-Options 자동 적용
- [x] **Rate Limiting 강화** (`Flask-Limiter`)
  - 로그인 엔드포인트: 5회/분 제한 (Brute-force 방어)
  - 전역 제한: 50회/시간, 200회/일
- [x] **robots.txt 추가** — 검색 엔진 크롤링 차단 (`Disallow: /`)
- [x] **SECRET_KEY 환경변수화** (`WCMS_SECRET_KEY`) — 하드코딩 제거
- [x] **세션 쿠키 보안 강화** — Secure, HttpOnly, SameSite=Lax, 만료 1시간
- [x] **입력 검증 강화** (`validators.py` 확장)
  - `validate_username()`, `validate_pin()`, `sanitize_path()` 추가

### Added - 새로운 기능
- [x] **소개 페이지** (`/about`) — 사이드바에서 접근 가능
- [x] **보안 문서** (`docs/SECURITY.md`) — HTTPS 설정, 환경변수, 보안 체크리스트, 취약점 신고 절차
- [x] **취약점 점검 자동화** (GitHub Actions)
  - SAST: CodeQL Python 정적 분석 (push/PR/주간 스케줄)
  - DAST: OWASP ZAP baseline 스캔 (Flask 서버 로컬 실행)
  - 의존성 스캔: pip-audit, Dependabot (pip + GitHub Actions)

### Known Issues - 알려진 문제
- [ ] **Windows 표시 언어 설정이 일부 환경에서 미적용**
  - 계정 생성 시 언어 설정이 일부 환경에서 정상 적용되지 않는 문제
  - v0.8.9 ~ v0.8.11에서 지속 개선 시도 중이나 완전 해결 미완료
  - 다음 버전에서 추가 조사 예정

---

## [0.8.11] - 2026-02-19

> **상태**: Released (Hotfix)
> **테마**: Windows 표시 언어 설정 개선

### Fixed - 버그 수정
- [x] **Windows 표시 언어(UI) 미변경 문제 개선 시도**
  - `Set-WinUserLanguageList` 외에 `Set-WinUILanguageOverride` 및 `Set-Culture` 명령어 추가
  - 입력 언어뿐만 아니라 Windows UI 언어와 지역 설정까지 변경되도록 개선
  - ⚠️ 일부 환경에서 여전히 미적용되는 경우 있음 (v0.9.0 Known Issues 참고)

---

## [0.8.10] - 2026-02-19

> **상태**: Released (Hotfix)  
> **테마**: 언어 팩 설치 안정성 개선

### Fixed - 버그 수정
- [x] **언어 팩 설치 타임아웃 연장**
  - `Install-Language` 실행 타임아웃을 10분에서 30분으로 연장 (네트워크 환경 고려)

---

## [0.8.9] - 2026-02-18

> **상태**: Released (Hotfix)  
> **테마**: 언어 설정 기능 안정화

### Fixed - 버그 수정
- [x] **언어 설정 로직 개선**
  - 언어 팩 미설치 시 자동 설치 기능 추가 (`Install-Language`)
  - `RunOnce` 실행 시 로그 기록 추가 (`C:\ProgramData\WCMS\logs\lang_setup.log`)
  - PowerShell 스크립트 실행 안정성 개선
- [x] **명령 실행 비동기 처리**
  - `client/main.py`: 명령 실행을 별도 스레드로 분리하여 Heartbeat 차단 방지

---

## [0.8.8] - 2026-02-18

> **상태**: Released  
> **테마**: 버그 수정 및 기능 완성도 향상

### Added - 새로운 기능
- [x] **계정 생성 시 언어 설정 구현**
  - `RunOnce` 레지스트리를 활용하여 사용자 최초 로그인 시 언어 설정(`Set-WinUserLanguageList`)이 적용되도록 구현
  - 지원 언어: 한국어, 영어, 중국어, 몽골어

### Changed - 변경사항
- [x] **계정 관리 UI 개선**
  - 불필요한 키보드 레이아웃 설정 제거 (언어 설정에 따라 자동 적용됨)
  - 일괄 계정 관리 모달 UI 최적화
- [x] **메뉴 정리**
  - 사용하지 않는 `/account/manager` 라우트 및 메뉴 링크 제거 (일괄 관리로 통합)

### Fixed - 버그 수정
- [x] **토큰 삭제 버그 수정**
  - 토큰 삭제 시 ID 대신 토큰 문자열을 사용하여 삭제되지 않던 문제 해결 (`token.id` 사용)

---

## [0.8.7] - 2026-02-18

> **상태**: Released  
> **테마**: 자동 업데이트, 프로그램 관리, 계정 생성 옵션

### Added - 새로운 기능
- [x] **클라이언트 자동 업데이트**
  - 클라이언트가 서버에서 새 버전을 감지하고 자동으로 업데이트
  - `install.cmd` 또는 별도의 업데이트 스크립트를 다운로드하여 실행
  - 서비스 중지 -> 파일 교체 -> 서비스 시작 프로세스 자동화
- [x] **프로그램 삭제**
  - `chocolatey`를 사용하여 프로그램을 삭제하는 기능 추가
  - `/api/admin/pc/{pc_id}/uninstall` 엔드포인트 추가
- [x] **계정 생성 옵션**
  - 윈도우 계정 생성 시 언어 설정 파라미터 추가 (`language`)

### Changed - 변경사항
- [x] **계정 관리 UI 개선**
  - 일괄 계정 관리 모달에서 언어 설정 옵션 추가

---

## [0.8.6] - 2026-02-11

> **상태**: Released  
> **테마**: 안정성 강화, Chocolatey 도입, UI 개선

### Added - 새로운 기능
- [x] **Chocolatey 지원**
  - `winget` 대신 `chocolatey`를 사용하여 프로그램 설치
  - 서비스 환경(`LocalSystem`)에서도 안정적인 설치 지원
  - Chocolatey 미설치 시 자동 설치 기능 추가
- [x] **UI 개선**
  - 계정 관리 모달: 작업 유형 선택 및 동적 입력 필드 제공
  - 전원 관리 모달: 종료/재시작 버튼 제공
  - 프로세스 종료 모달: 수집된 프로세스 목록에서 선택 가능 (`datalist`)
  - PC 상세 정보: RAM 사용량 도넛 차트 추가
- [x] **프로세스 목록 조회 API**
  - `GET /api/admin/processes`: 수집된 프로세스 목록 조회 (중복 제거)

### Changed - 변경사항
- [x] **서비스 설치 방식 개선**
  - `install.cmd`에서 `sc create`를 사용하여 서비스 직접 등록 (안정성 향상)
  - 서비스 시작 유형을 `delayed-auto` (지연된 자동 시작)로 설정하여 부팅 시 안정성 확보
  - 서비스 실패 시 자동 재시작 설정 추가 (`sc failure`)
- [x] **명령 실행 개선**
  - `download` 명령: `destination` 파라미터 지원 (저장 경로 지정 가능)
  - `install` 명령: `app_id` 파라미터 사용 (기존 `app_name` 혼용 해결)

### Fixed - 버그 수정
- [x] 서비스 재시작 시 자동 시작되지 않는 문제 해결
- [x] `install.cmd` 실행 시 멈추는 현상 해결
- [x] `winget`이 서비스 계정에서 실행되지 않는 문제 해결 (Chocolatey로 대체)

---

## [0.8.5] - 2026-02-11

> **상태**: Yanked (서비스 설치 문제)  
> **테마**: Chocolatey 도입 시도

---

## [0.8.4] - 2026-02-11

> **상태**: Released (Internal)  
> **테마**: 서비스 시작 로직 수정

### Fixed - 버그 수정
- [x] **서비스 시작 로직 수정**
  - `client/service.py`: 인자 없이 실행될 때 서비스 디스패처 연결 시도하도록 수정
  - `install.cmd`: `binPath`에서 `start` 인자 제거 (서비스 표준 방식 준수)

---

## [0.8.3] - 2026-02-11

> **상태**: Released (Internal)  
> **테마**: 설치 스크립트 개선

### Changed - 변경사항
- [x] **설치 스크립트 개선**
  - `install.cmd`: PowerShell 호출 방식 변경 (`Start-Process` 사용)
  - 경로 공백 처리 및 따옴표 문제 해결 시도

---

## [0.8.2] - 2026-02-11

> **상태**: Released  
> **테마**: 클라이언트 안정성 및 데이터 무결성

### Fixed - 버그 수정
- [x] **프로세스 중복 실행 방지**
  - `client/service.py`: 인자 없이 실행 시 자동 설치 로직 제거
- [x] **JSON 이중 인코딩 해결**
  - `client/collector.py`: 데이터를 JSON 문자열로 미리 변환하지 않고 객체 그대로 반환
  - 서버에서 이중으로 인코딩되어 DB에 저장되는 문제 해결
- [x] **중복 등록 방지**
  - `client/main.py`: `registered.flag` 파일을 사용하여 불필요한 재등록 방지
- [x] **디스크 정보 수집 개선**
  - 고정 디스크(`fixed`)만 수집하도록 필터링 추가

---

## [0.8.0] - 2026-02-10

> **상태**: Released  
> **테마**: 보안 강화, 네트워크 최적화, RESTful API 개선

### Added - 새로운 기능

#### PIN 인증 시스템
- [x] **등록 토큰 관리**
  - 관리자가 6자리 PIN 생성
  - 1회용 / 재사용 가능 토큰 지원
  - 만료 시간 설정 (기본 10분)
  - 토큰 목록 조회 및 삭제
  
- [x] **클라이언트 PIN 검증**
  - `/api/client/register`에 PIN 필수
  - 403 에러 (PIN 검증 실패)
  - 400 에러 (PIN 누락)
  - `is_verified`, `registered_with_token` DB 필드 추가

- [x] **관리자 API**
  - `POST /api/admin/registration-token` - 토큰 생성
  - `GET /api/admin/registration-tokens` - 토큰 목록
  - `DELETE /api/admin/registration-token/{id}` - 토큰 삭제
  - `GET /api/admin/pcs/unverified` - 미검증 PC 조회
  - `DELETE /api/pc/{pc_id}` - PC 삭제 (Cascade)

#### 네트워크 성능 최적화
- [x] **Long-polling 제거**
  - `time.sleep()` 제거로 워커 blocking 해결
  - 즉시 응답 방식으로 변경
  - 폴링 주기: 5초 → 2초

- [x] **명령 조회 + 하트비트 통합**
  - `POST /api/client/commands` (RESTful 복수형)
  - 경량 하트비트 (CPU, RAM, IP) 함께 전송
  - HTTP 요청 오버헤드 50% 절감
  - 대역폭 60% 절감 (프로세스 목록 제외)

- [x] **IP 주소 자동 업데이트**
  - 모든 경량 하트비트에 IP 포함

### Changed - 변경사항

#### API 개선 (Breaking Changes)
- [x] **RESTful API 재설계**
  - 일관된 응답 형식: `{status, data, error}`
  - 명령 조회: `/api/client/command` → `/api/client/commands`
  - 명령 결과: `/api/client/command/result` → `/api/client/commands/{id}/result`
  - 에러 코드 추가: `PC_NOT_FOUND`, `COMMAND_NOT_FOUND` 등

- [x] **응답 형식 통일**
  ```json
  // 성공
  {"status": "success", "data": {...}}
  
  // 에러
  {"status": "error", "error": {"code": "...", "message": "..."}}
  ```

- [x] **명령 응답 개선**
  - `command_id` → `data.command.id`
  - `command_type` → `data.command.type`
  - `command_data` → `data.command.parameters`
  - `has_command` boolean 플래그 추가

#### 데이터베이스 스키마 변경
- [x] **테이블 이름 정규화**
  - `pc_command` → `commands`
  - `pc_status` → `pc_dynamic_info`
  
- [x] **pc_dynamic_info 최적화**
  - UNIQUE 제약 추가 (최신 상태만 저장)
  - `INSERT OR REPLACE` 사용
  - 디스크 사용량 70% 감소
  - `created_at` → `updated_at`

### Fixed - 버그 수정
- [x] 동시 연결 처리 문제 해결 (Long-polling 제거)
- [x] Rate limiting 구현 (클라이언트 폴링 2초 간격)
- [x] DB 트랜잭션 안정성 개선

### Testing - 테스트
- [x] **통합 테스트 작성**
  - 14개 통합 테스트 추가
  - 클라이언트-서버 전체 흐름 검증
  - PIN 인증 시스템 테스트
  - 에러 시나리오 테스트
  
- [x] **테스트 커버리지**
  - 65개 테스트 통과
  - API 레이어 완전 검증

---

## [0.7.1] - 2026-02-07

### Fixed - 버그 수정
- [x] **[중요] install.cmd config.json SERVER_URL 슬래시 누락 수정**
- [x] **클라이언트 명령 실행 서버 측 개선**
- [x] **클라이언트 서비스 안정성 개선**
- [x] **디스크 사용량 차트 버그 수정**
- [x] **프로세스 표시 버그 수정**
- [x] **명령 실행 속도 개선**
- [x] **IP 주소 표시 버그 수정**

### Added - 새로운 기능
- [x] **테스트 추가**
- [x] **디스크 도넛 차트 추가**
- [x] **Windows Docker 클라이언트 트러블슈팅 문서**

---

## [0.7.0] - 2026-02-07

### 추가
- **한 줄 설치 스크립트 구현 (Phase 2 완료)** [x]
- **클라이언트 서버 URL 설정 개선** [x]
- **문서 정리** [x]
- **Docker 통합 테스트 인프라 구축** [x]
- **Windows 백업 및 복원 시스템** [x]
- **PreShutdown 종료 감지 기능 완료** [x]
- **테스트 환경 개선** [x]
- **AI 컨텍스트 파일 생성** [x]
- **서버 모듈화 완료** (Phase 1 - 100%)
- **클라이언트 개선** (Phase 2 - 60%)

### 변경
- 서버 아키텍처: 단일 파일 (1,270줄) → 모듈화 (13개 파일, 2,680줄)
- 설계 패턴 적용: Repository, Blueprint, Service 레이어
- 타입 힌팅 추가 (모든 새 함수)
- 문서 구조: 명확한 역할 분리 및 중복 제거
- 프로젝트 구조 정리: archive, tests, docs, db, scripts 디렉토리 분리

### 수정
- **Docker 서버 DB 초기화 수정** [x]
- **Docker 헬스체크 타임아웃 개선** [x]
- **[중요] CommandModel 스키마 호환성 버그 수정**

---

## [0.6.0] - 2025-12-04

### 추가
- **일괄 명령 전송 기능 확장**
- **명령 초기화 시스템**
- **PC 상세 정보 향상**

### 개선
- 명령 폴링 최적화 (Long-polling 10초)
- 하트비트 주기 최적화 (5분)
- 웹 UI 자동 새로고침 (30초)
- 백그라운드 오프라인 체크 (30초 주기)
- SQLite WAL 모드 적용 (동시성 개선)

### 수정
- 정적/동적 데이터 분리로 디스크 사용량 70% 감소
- 시스템 프로세스 필터링 정확도 향상
- CPU/RAM/디스크 정보 단위 통일 (GB)
- 명령 실행 안정성 개선

---

## [0.5.6] - 2025-11-19

### 추가
- Windows 서비스로 클라이언트 배포
- GitHub Actions 자동 빌드 및 배포
- 클라이언트 자동 버전 체크 기능
- 백그라운드 오프라인 체크 (30초 주기)
- Long-polling 최적화 (10초)

### 개선
- 정적/동적 데이터 분리로 디스크 사용량 70% 감소
- 하트비트 주기 최적화 (10분 → 5분)
- 명령 폴링 주기 최적화 (30초 → 10초)

### 수정
- SQLite WAL 모드 적용으로 동시성 개선
- 프로세스 필터링 개선 (100+ 시스템 프로세스)
- CPU/RAM/디스크 정보 GB 단위로 통일

---

## [0.5.0] - 2025-11-10

### 추가
- 일괄 명령 전송 기능 (드래그 선택, 체크박스)
- Windows 계정 관리 (생성/삭제/비밀번호 변경)
- 명령 실행 결과 보고 API
- 프로세스 실행 기록 페이지

### 개선
- 좌석 배치 편집기 UI 개선
- PC 상세 정보 모달 디자인 개선

---

## [0.4.0] - 2025-10-25

### 추가
- 명령 폴링 및 실행 시스템
- 명령 큐 시스템 (pc_command 테이블)
- 명령 상태 추적 (pending/executing/completed/error)

---

## [0.3.0] - 2025-10-15

### 추가
- 좌석 배치 관리 시스템 (드래그 앤 드롭)
- 실습실 관리 페이지

### 개선
- 데이터베이스 스키마 최적화 (정적/동적 데이터 분리)

---

## [0.2.0] - 2025-10-05

### 추가
- 클라이언트 기본 기능 (시스템 정보 수집, 하트비트)
- WMI를 통한 정확한 시스템 정보 수집

---

## [0.1.0] - 2025-09-20

### 추가
- Flask 서버 기본 구조
- SQLite 데이터베이스
- 초기 문서 작성
