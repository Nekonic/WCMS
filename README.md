# WCMS (Woosuk Computer Management System)

WCMS는 실습실 PC를 원격으로 관리하고 모니터링하기 위한 시스템입니다.

## 📊 프로젝트 상태

- **버전**: 0.8.6
- **최근 업데이트**: 2026-02-11
- **주요 기능**: 
  - [x] PIN 기반 인증 시스템
  - [x] RESTful API 재설계
  - [x] 네트워크 최적화 (대역폭 -60%, 폴링 2초)
  - [x] 통합 테스트 (65개 통과)
  - [x] 웹 UI 등록 토큰 관리
  - [x] 자동 IP 변경 감지
  - [x] **Chocolatey 기반 프로그램 설치**
  - [x] **안정적인 Windows 서비스 설치**

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

### 클라이언트 설치 (v0.8.0+ - PIN 인증 필수)

#### 1. 관리자 웹에서 등록 PIN 생성

서버 관리자 페이지에서 6자리 PIN을 생성합니다:

1. 웹 브라우저에서 http://your-server:5050 접속
2. 로그인 (admin/admin)
3. **🔑 등록 토큰** 메뉴 클릭
4. 토큰 생성 (1회용 또는 재사용 가능)
5. 생성된 PIN 복사

#### 2. 클라이언트 자동 설치

한 줄 명령으로 클라이언트를 자동 설치할 수 있습니다:

**Windows CMD (관리자 권한):**
```cmd
curl -fsSL http://your-server:5050/install/install.cmd -o install.cmd && install.cmd && del install.cmd
```

**PowerShell (관리자 권한):**
```powershell
iwr -Uri "http://your-server:5050/install/install.ps1" -OutFile install.ps1; .\install.ps1; del install.ps1
```

설치 중 **6자리 PIN 입력** 프롬프트가 나타나면 관리자가 생성한 PIN을 입력하세요.

**설치 과정:**
- GitHub Releases에서 최신 클라이언트 다운로드
- `C:\Program Files\WCMS` 디렉토리에 설치
- PIN을 포함한 `config.json` 자동 생성 (`C:\ProgramData\WCMS`)
- Windows 서비스(`WCMS-Client`)로 등록 및 자동 시작 (지연된 시작)

**⚠️ 사전 준비:** 설치 스크립트가 작동하려면 DB에 클라이언트 버전 정보가 필요합니다:

**로컬 서버:**
```bash
# Windows
sqlite3 db/wcms.sqlite3 "INSERT OR REPLACE INTO client_versions (version, download_url, changelog) VALUES ('0.8.6', 'https://github.com/Nekonic/WCMS/releases/download/client-v0.8.6/WCMS-Client.exe', 'v0.8.6 - Chocolatey Support');"
```

**Docker 서버:**
```bash
docker exec wcms-server sqlite3 /app/db/wcms.sqlite3 "INSERT OR REPLACE INTO client_versions (version, download_url, changelog) VALUES ('0.8.6', 'https://github.com/Nekonic/WCMS/releases/download/client-v0.8.6/WCMS-Client.exe', 'v0.8.6 - Chocolatey Support');"
```

---

자세한 내용은 [시작 가이드](docs/GETTING_STARTED.md)를 참고하세요.

## 📚 문서

모든 문서는 `docs/` 디렉토리에 있습니다.

### 빠른 온보딩
- **[AI 컨텍스트 (AI_CONTEXT.md)](AI_CONTEXT.md)**: 🤖 AI/신규 개발자를 위한 빠른 이해 가이드
- **[시작 가이드 (docs/GETTING_STARTED.md)](docs/GETTING_STARTED.md)**: 설치 및 실행 방법
- **[빠른 참조 (docs/QUICK_REFERENCE.md)](docs/QUICK_REFERENCE.md)**: 자주 사용하는 명령어 모음

### 상세 문서
- **[아키텍처 (docs/ARCHITECTURE.md)](docs/ARCHITECTURE.md)**: 시스템 구조 및 설계
- **[API 명세서 (docs/API.md)](docs/API.md)**: REST API 상세 설명 (v0.8.6)
- **[변경 이력 (docs/CHANGELOG.md)](docs/CHANGELOG.md)**: 버전별 변경사항
- **[문서 목록 (docs/INDEX.md)](docs/INDEX.md)**: 전체 문서 인덱스

### 기여자용
- **[Copilot 규칙 (.github/copilot-instructions.md)](.github/copilot-instructions.md)**: AI 어시스턴트 및 코딩 규칙
- **[Git 커밋 가이드 (docs/GIT_COMMIT_GUIDE.md)](docs/GIT_COMMIT_GUIDE.md)**: 커밋 컨벤션

## 🛠 기술 스택

- **Backend**: Python 3.8+, Flask
- **Database**: SQLite (WAL mode)
- **Frontend**: HTML, CSS, JavaScript
- **Client**: Python (psutil, requests, pywin32)
- **Package Manager**: uv

## 🔒 보안 (v0.8.0+)

- **PIN 인증**: 6자리 숫자 PIN으로 클라이언트 등록 인증
- **토큰 관리**: 1회용/재사용 가능 토큰, 만료 시간 설정
- **웹 UI**: 관리자만 토큰 생성/삭제 가능
- **검증 상태**: 미검증 PC 자동 차단

## ⚡ 성능 (v0.8.0+)

- **네트워크**: 대역폭 -60%, HTTP 오버헤드 -50%
- **폴링**: 2초 간격 (기존 5초)
- **디스크**: 사용량 -70% (최신 상태만 저장)
- **동시 연결**: Long-polling 제거로 100대 지원

## ❓ 트러블슈팅

### 1. 서비스 시작 실패 (Exit code 2)
- **원인**: 서비스 실행 파일 경로 문제 또는 권한 문제.
- **해결**: v0.8.6 이상 버전을 사용하세요. `install.cmd`가 `sc create`를 사용하여 경로 문제를 해결했습니다.

### 2. 프로그램 설치 실패 (Chocolatey)
- **원인**: Chocolatey가 설치되지 않았거나 네트워크 문제.
- **해결**: 클라이언트 로그(`C:\ProgramData\WCMS\logs\client.log`)를 확인하세요. Chocolatey 자동 설치가 실패했다면 수동으로 설치해야 할 수 있습니다.

### 3. PIN 인증 실패 (403 Forbidden)
- **원인**: PIN이 만료되었거나 이미 사용됨.
- **해결**: 관리자 페이지에서 새 토큰을 생성하여 다시 시도하세요.

## 🧪 테스트

```bash
# 전체 테스트 (65개)
python manage.py test

# 서버 테스트만
python manage.py test server

# 클라이언트 테스트만
python manage.py test client

# Docker 통합 테스트 (Windows 환경 E2E)
python manage.py docker-test
```

## 🚀 v0.8.6 주요 변경사항

### 새로운 기능
- **Chocolatey 지원**: `winget` 대신 `chocolatey`를 사용하여 프로그램 설치 (서비스 환경 호환성 개선)
- **서비스 설치 개선**: `sc create`를 사용하여 안정적인 서비스 등록 및 시작
- **UI 개선**: 계정 관리, 전원 관리, 프로세스 종료 모달 개선
- **RAM 차트**: PC 상세 정보에 RAM 사용량 도넛 차트 추가

### 버그 수정
- 서비스 재시작 시 자동 시작 안 되는 문제 해결 (`delayed-auto`)
- 파일 다운로드 시 경로 지정 기능 추가
- JSON 이중 인코딩 문제 해결

자세한 내용은 [CHANGELOG.md](docs/CHANGELOG.md)를 참고하세요.

## 📝 라이선스

MIT License
