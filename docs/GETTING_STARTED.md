# WCMS 시작하기

WCMS 프로젝트를 설치하고 실행하는 가이드입니다.

---

## 🚀 빠른 시작

### 1. 필수 요구사항
- Python 3.9 이상
- Git

### 2. 저장소 클론 및 실행

```bash
# 저장소 클론
git clone https://github.com/Nekonic/WCMS.git
cd WCMS

# 서버 실행 (의존성 자동 설치)
python manage.py run
```

- **서버 주소**: http://localhost:5050
- **기본 계정**: `admin` / `admin`

---

## 🛠 관리 명령어

| 명령어 | 설명 |
|--------|------|
| `python manage.py run` | 서버 실행 (개발 모드) |
| `python manage.py test` | 단위 테스트 실행 |
| `python manage.py docker-test` | Docker 환경 테스트 |
| `python manage.py build` | 클라이언트 EXE 빌드 (Windows 전용) |
| `python manage.py init-db` | DB 초기화 |

---

## ⚠️ 자주 하는 실수

### 1. 관리자 비밀번호 틀림
- ❌ `admin123` (구버전)
- ✅ `admin` (현재 버전)

### 2. 포트가 이미 사용 중
```bash
# Windows
netstat -ano | findstr :5050
taskkill /PID <PID> /F

# Linux/macOS
lsof -i :5050
kill -9 <PID>
```

### 3. Docker 테스트 시 ISO 파일 필요
- `iso/win11.iso` 파일이 없으면 Docker Windows 컨테이너가 시작되지 않음
- 다운로드: https://www.microsoft.com/software-download/windows11

### 4. 클라이언트 빌드는 Windows에서만 가능
- `python manage.py build`는 Windows 환경에서만 실행 가능
- pywin32, WMI 의존성 필요

---

## 🧪 동작 확인

### API 테스트
```bash
# 버전 정보 확인
curl http://localhost:5050/api/client/version

# 헬스체크
curl http://localhost:5050/
```

### 단위 테스트
```bash
python manage.py test
```

---

## 📚 다음 단계

- **[API 명세](API.md)** - REST API 상세 설명
- **[아키텍처](ARCHITECTURE.md)** - 시스템 구조 이해
- **[변경 이력](CHANGELOG.md)** - 최신 변경사항 확인
- **[Docker 테스트](DOCKER_CLIENT_SETUP.md)** - Windows 컨테이너 테스트

---

## 💡 추가 정보

### 수동 설정 (고급)
```bash
# uv 설치
pip install uv

# 의존성 설치
uv sync --project server

# 서버 직접 실행
cd server
uv run python app.py
```

### DB 위치
- 로컬: `db/wcms.sqlite3`
- Docker: `/app/db/wcms.sqlite3`

