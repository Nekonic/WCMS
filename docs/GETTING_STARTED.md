# WCMS 시작 가이드

WCMS 프로젝트를 설치하고 실행하는 가이드입니다.

---

## 빠른 시작

### 1. 필수 요구사항

- Python 3.9 이상
- Git
- uv (패키지 관리자)

### 2. 저장소 클론 및 실행

```bash
git clone https://github.com/Nekonic/WCMS.git
cd WCMS

# 의존성 설치
python manage.py install

# 데이터베이스 초기화
python manage.py init-db

# 서버 실행
python manage.py run
```

접속 주소: `http://localhost:5050` | 기본 계정: `admin` / `admin`

---

## 클라이언트 설치

### 1. 등록 PIN 생성

1. 서버 관리자 페이지(`http://localhost:5050`) 접속
2. 로그인 (`admin` / `admin`)
3. **등록 토큰** 메뉴 클릭
4. 토큰 생성 후 6자리 PIN 복사

### 2. 자동 설치 (관리자 권한)

**Windows CMD:**
```cmd
curl -fsSL http://서버주소:5050/install/install.cmd -o install.cmd && install.cmd && del install.cmd
```

**PowerShell:**
```powershell
iwr -Uri "http://서버주소:5050/install/install.ps1" -OutFile install.ps1; .\install.ps1; del install.ps1
```

설치 중 PIN을 입력하면 자동으로 등록되고 서비스가 시작됩니다.

### 3. 자동 업데이트

클라이언트는 시작 시 자동으로 최신 버전을 확인하고 업데이트합니다.
서버 관리자 페이지 → **클라이언트 버전** 메뉴에서 버전을 등록하면 클라이언트가 감지하여 자동 교체합니다.

---

## 관리 명령어

| 명령어 | 설명 |
|--------|------|
| `python manage.py run` | 서버 실행 (개발 모드) |
| `python manage.py run --prod` | 서버 실행 (Gunicorn, 프로덕션) |
| `python manage.py test` | 단위 테스트 실행 |
| `python manage.py build` | 클라이언트 EXE 빌드 (Windows 전용) |
| `python manage.py init-db` | DB 초기화 |
| `python manage.py install` | 의존성 설치 |

---

## 자주 하는 실수

**포트가 이미 사용 중**
```bash
# Windows
netstat -ano | findstr :5050
taskkill /PID <PID> /F
```

**클라이언트 빌드는 Windows에서만 가능**
`python manage.py build`는 Windows 환경에서만 실행 가능합니다 (pywin32, WMI 의존성 필요).

**서비스 시작 실패 (Exit code 2)**
`install.cmd`를 관리자 권한으로 다시 실행하세요.

**프로그램 설치/삭제 실패**
WCMS는 Chocolatey를 사용합니다. 네트워크 문제로 실패한 경우 수동으로 Chocolatey를 설치하세요.

---

## 동작 확인

```bash
# 버전 정보 확인
curl http://localhost:5050/api/client/version

# 단위 테스트
python manage.py test
```

---

## 다음 단계

- [API 명세](API.md) — REST API 상세 설명
- [아키텍처](ARCHITECTURE.md) — 시스템 구조 이해
- [보안](SECURITY.md) — HTTPS 설정 및 보안 정책
- [변경 이력](CHANGELOG.md) — 최신 변경사항 확인