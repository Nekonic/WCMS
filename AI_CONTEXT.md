# AI 컨텍스트: WCMS

> 실습실 PC 원격 관리 시스템 (Woosuk Computer Management System)

---

## 현재 작업 상태

- **v0.9.0**: 작업 완료, 테스트 후 릴리스 예정
  - 보안 강화 (HTTPS, Flask-Talisman, Flask-Limiter, 입력 검증)
  - 소개 페이지 (`/about`), 취약점 점검 자동화 (CodeQL, ZAP, pip-audit)
- **다음 목표**: v0.9.0 릴리스

자세한 변경 이력: [docs/CHANGELOG.md](docs/CHANGELOG.md)

---

## 아키텍처

```
클라이언트 (Windows Service) ←─ HTTP ─→ 서버 (Flask) ←→ 웹 UI (브라우저)
```

**클라이언트 통신 흐름:**
1. 등록: PIN 인증 필수 (`/api/client/register`)
2. 전체 하트비트: 5분마다 시스템 정보 전송 (`/api/client/heartbeat`)
3. 명령 폴링 + 경량 하트비트: 2초마다 CPU/RAM/IP 전송 (`/api/client/commands`)
4. 종료 감지: PreShutdown 서비스 이벤트로 오프라인 상태 서버에 알림

**보안 레이어 (v0.9.0):**
- `Flask-Talisman`: HTTPS 강제, HSTS, CSP, X-Frame-Options (프로덕션)
- `Flask-Limiter`: 로그인 5회/분, 전역 50회/시간·200회/일
- 세션 쿠키: Secure, HttpOnly, SameSite=Lax, 만료 1시간

---

## 디렉토리 구조

```
server/
├── app.py                  # Flask 앱 진입점 (Talisman, Limiter, 라우트)
├── config.py               # 환경 설정 (Dev/Prod/Test)
├── api/
│   ├── client.py           # 클라이언트 API (등록, 하트비트, 명령 폴링)
│   ├── admin.py            # 관리자 API (토큰, 계정, 프로세스, PC 관리)
│   └── install.py          # 설치 스크립트 제공 (install.cmd 등)
├── models/
│   ├── registration.py     # 등록 토큰 모델
│   ├── pc.py               # PC 모델
│   └── command.py          # 명령 모델
├── services/               # 비즈니스 로직
├── utils/
│   └── validators.py       # 입력 검증 (username, PIN, path, hostname, IP, MAC)
└── templates/
    ├── base.html           # 공통 레이아웃 (사이드바 포함)
    ├── about.html          # 소개 페이지
    └── ...

client/
├── main.py                 # 메인 루프 (PIN 인증, registered.flag, 자동 업데이트)
├── service.py              # Windows 서비스 래퍼 (StartServiceCtrlDispatcher)
├── collector.py            # 시스템 정보 수집 (고정 디스크만, WMI)
├── executor.py             # 명령 실행 (Chocolatey, PowerShell, RunOnce)
├── updater.py              # 자동 업데이트
└── config.py               # 클라이언트 설정

docs/
├── CHANGELOG.md            # 버전별 변경 이력
├── plan.md                 # 개발 계획
├── SECURITY.md             # 보안 설정 가이드 (HTTPS, 환경변수)
└── GIT_COMMIT_GUIDE.md     # 커밋 규칙 (Conventional Commits)

.github/
├── workflows/
│   ├── build_client.yml    # 클라이언트 EXE 빌드 및 릴리스 (tag: client-v*)
│   ├── codeql.yml          # SAST - Python 정적 분석
│   ├── zap.yml             # DAST - OWASP ZAP baseline 스캔
│   └── security_scan.yml   # 의존성 스캔 (pip-audit)
├── dependabot.yml          # pip + GitHub Actions 주간 업데이트
└── zap-rules.tsv           # ZAP false-positive 무시 규칙
```

---

## 환경변수

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `WCMS_SECRET_KEY` | Flask 세션 암호화 키 (프로덕션 필수) | dev용 하드코딩값 |
| `WCMS_DB_PATH` | SQLite DB 파일 경로 | `db.sqlite3` |
| `WCMS_SSL_CERT` | SSL 인증서 경로 (HTTPS 활성화) | 없음 |
| `WCMS_SSL_KEY` | SSL 개인키 경로 | 없음 |
| `FLASK_ENV` | `development` / `production` | `production` |

---

## 빠른 참조

```bash
# 서버 실행 (개발)
cd server && uv run python app.py

# 또는 manage.py 사용
uv run python manage.py run

# 테스트 실행
uv run python manage.py test
uv run python manage.py test server   # 서버만
uv run python manage.py test client  # 클라이언트만

# 클라이언트 빌드 (Windows만)
uv run python manage.py build
```

**관리자 계정**: `admin` / `admin`

---

## 데이터베이스 주요 테이블

| 테이블 | 설명 |
|--------|------|
| `pcs` | PC 정적 정보 (hostname, IP, MAC, CPU, OS 등) |
| `pc_dynamic_info` | PC 동적 정보 (CPU%, RAM%, 최신 1건만 유지) |
| `commands` | 명령 큐 (pending → executing → completed/error) |
| `registration_tokens` | 6자리 PIN 토큰 (1회용/재사용, 만료시간) |
| `rooms` | 실습실 정보 |
| `layouts` | 좌석 배치 (JSON) |

SQLite WAL 모드 사용 (동시 쓰기 처리).

---

## API 인증

- **클라이언트 API** (`/api/client/*`): `hostname` + `token` (등록 시 발급)
- **관리자 API** (`/api/admin/*`): Flask 세션 (`session['username']`)
- **버전 업데이트 API**: `Authorization: Bearer <UPDATE_TOKEN>` (GitHub Actions Secret)

---

## 자주 하는 실수

### 서비스 설치
- `install.cmd`만 사용 (`sc create` 방식)
- `WCMS-Client.exe install` 직접 실행 금지 (pywin32 install 명령 아님)
- 서비스 시작 유형: `delayed-auto`

### 프로그램 설치
- **Chocolatey** 사용 (winget은 LocalSystem 계정에서 동작 안 함)
- 없으면 자동 설치됨

### 클라이언트 등록
- v0.8.0부터 6자리 PIN 필수
- 관리자가 웹 UI `/registration-tokens`에서 PIN 생성 후 제공

### 언어 설정 (Known Issue)
- `RunOnce` 레지스트리로 사용자 최초 로그인 시 적용
- 일부 환경에서 미적용 문제 조사 중 (v0.8.9~v0.8.11 개선 시도, 미완)

### 패키지 관리
- **uv** 사용 (`pip` 직접 사용 금지)
- `uv sync` 로 의존성 설치, `uv run` 으로 실행

---

## 코드 규칙

- 타입 힌팅 필수 (신규 함수)
- 에러 핸들링 필수
- 체크박스: `- [x]` / `- [ ]` (이모티콘 금지)
- 커밋: Conventional Commits 형식 (영어 제목, 한국어 본문 가능)
- 클라이언트는 Windows 전용 (pywin32, WMI 의존)