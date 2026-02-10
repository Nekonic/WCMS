# WCMS (Woosuk Computer Management System)

WCMS는 실습실 PC를 원격으로 관리하고 모니터링하기 위한 시스템입니다.

## 📊 프로젝트 상태

- **버전**: 0.7.1
- **최근 업데이트**: 2026-02-07
- **주요 기능**: 
  - [x] PreShutdown 종료 감지
  - [x] Long-polling 명령 전송
  - [x] 한 줄 설치 스크립트
  - [x] Docker 통합 테스트
  - [x] 디스크/프로세스/명령 실행 버그 수정

## 🚀 빠른 시작

### 서버 설치

통합 관리 스크립트를 사용하여 간편하게 시작할 수 있습니다.

```bash
# 1. 의존성 설치
python manage.py install

# 2. 데이터베이스 초기화
python manage.py init-db

# 3. 서버 실행
python manage.py run
```

- **서버 주소**: http://localhost:5050
- **기본 계정**: `admin` / `admin`

### 클라이언트 설치 (NEW!)

한 줄 명령으로 클라이언트를 자동 설치할 수 있습니다:

**Windows Batch (CMD):**
```cmd
curl -fsSL http://your-server:5050/install/install.cmd -o install.cmd && install.cmd && del install.cmd
```

**PowerShell:**
```powershell
iwr -Uri "http://your-server:5050/install/install.ps1" -OutFile install.ps1; .\install.ps1; del install.ps1
```

- 관리자 권한 필요
- GitHub Releases에서 최신 버전 자동 다운로드
- Windows 서비스로 자동 등록 및 시작

**⚠️ 사전 준비:** 설치 스크립트가 작동하려면 DB에 클라이언트 버전 정보가 필요합니다:

**로컬 서버:**
```bash
# Windows
sqlite3 db/wcms.sqlite3 "INSERT OR REPLACE INTO client_versions (version, download_url, changelog) VALUES ('0.7.0', 'https://github.com/Nekonic/WCMS/releases/download/client-v0.7.0/WCMS-Client.exe', 'Latest version');"

# Linux/Mac
sqlite3 db/wcms.sqlite3 "INSERT OR REPLACE INTO client_versions (version, download_url, changelog) VALUES ('0.7.0', 'https://github.com/Nekonic/WCMS/releases/download/client-v0.7.0/WCMS-Client.exe', 'Latest version');"
```

**Docker 서버:**
```bash
docker exec wcms-server sqlite3 /app/db/wcms.sqlite3 "INSERT OR REPLACE INTO client_versions (version, download_url, changelog) VALUES ('0.7.0', 'https://github.com/Nekonic/WCMS/releases/download/client-v0.7.0/WCMS-Client.exe', 'Latest version');"
```

**확인:**
```bash
curl http://localhost:5050/api/client/version
```

### Docker 통합 테스트 (NEW!)

실제 Windows 환경에서 클라이언트를 테스트하세요:

```bash
# Docker Compose 기반 통합 테스트
python manage.py docker-test
```

- **Windows 11 컨테이너** (dockurr/windows)
- **VNC 접속**: http://localhost:8006
- **자동화된 E2E 테스트**

자세한 내용은 [Docker 테스트 가이드](tests/DOCKER_TEST_GUIDE.md)를 참고하세요.

---

자세한 내용은 [시작 가이드](docs/GETTING_STARTED.md)를 참고하세요.

## 📚 문서

모든 문서는 `docs/` 디렉토리에 있습니다.

### 빠른 온보딩
- **[AI 컨텍스트 (AI_CONTEXT.md)](AI_CONTEXT.md)**: 🤖 AI/신규 개발자를 위한 빠른 이해 가이드
- **[시작 가이드 (docs/GETTING_STARTED.md)](docs/GETTING_STARTED.md)**: 설치 및 실행 방법
- **[Docker 테스트 가이드 (tests/DOCKER_TEST_GUIDE.md)](tests/DOCKER_TEST_GUIDE.md)**: 🐳 Docker 통합 테스트 사용법

### 상세 문서
- **[아키텍처 (docs/ARCHITECTURE.md)](docs/ARCHITECTURE.md)**: 시스템 구조 및 설계
- **[API 명세서 (docs/API.md)](docs/API.md)**: REST API 상세 설명
- **[변경 이력 (docs/CHANGELOG.md)](docs/CHANGELOG.md)**: 버전별 변경사항
- **[문서 목록 (docs/INDEX.md)](docs/INDEX.md)**: 전체 문서 인덱스

### 기여자용
- **[Copilot 규칙 (.github/copilot-instructions.md)](.github/copilot-instructions.md)**: AI 어시스턴트 및 코딩 규칙
- **[Git 커밋 가이드 (docs/GIT_COMMIT_GUIDE.md)](docs/GIT_COMMIT_GUIDE.md)**: 커밋 컨벤션

## 🛠 기술 스택

- **Backend**: Python, Flask
- **Database**: SQLite
- **Frontend**: HTML, CSS, JavaScript
- **Client**: Python (psutil, WMI)
- **Package Manager**: uv

## 🧪 테스트

```bash
# 단위 테스트
python manage.py test

# Docker 통합 테스트 (Windows 환경 E2E)
python manage.py docker-test
```

## 📝 라이선스

MIT License
