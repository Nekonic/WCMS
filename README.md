# WCMS (Woosuk Computer Management System)

WCMS는 실습실 PC를 원격으로 관리하고 모니터링하기 위한 시스템입니다.

## 🚀 시작하기

통합 관리 스크립트를 사용하여 간편하게 시작할 수 있습니다.

```bash
# 서버 실행
python manage.py run
```

- **서버 주소**: http://localhost:5050
- **기본 계정**: `admin` / `admin123`

자세한 내용은 [시작 가이드 (docs/GETTING_STARTED.md)](docs/GETTING_STARTED.md)를 참고하세요.

## 📚 문서

모든 문서는 `docs/` 디렉토리에 있습니다.

- **[시작 가이드](docs/GETTING_STARTED.md)**: 설치 및 실행 방법
- **[아키텍처](docs/ARCHITECTURE.md)**: 시스템 구조 및 설계
- **[API 명세서](docs/API.md)**: REST API 상세 설명
- **[프로젝트 상태](docs/PROJECT_STATUS.md)**: 개발 진행 상황

## 🛠 기술 스택

- **Backend**: Python, Flask
- **Database**: SQLite
- **Frontend**: HTML, CSS, JavaScript
- **Client**: Python (psutil, WMI)
- **Package Manager**: uv

## 🧪 테스트

```bash
python manage.py test
```

## 📝 라이선스

MIT License
