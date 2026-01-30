# WCMS (Woosuk Computer Management System)

WCMS는 실습실 PC를 원격으로 관리하고 모니터링하기 위한 시스템입니다.

## 📊 프로젝트 상태

- **버전**: 0.7.0 (개발 중)
- **최근 업데이트**: 2026-01-30
- **주요 기능**: 
  - [x] PreShutdown 종료 감지
  - [x] Long-polling 명령 전송
  - [x] 자동 업데이트

## 🚀 빠른 시작

통합 관리 스크립트를 사용하여 간편하게 시작할 수 있습니다.

```bash
# 서버 실행
python manage.py run
```

- **서버 주소**: http://localhost:5050
- **기본 계정**: `admin` / `admin123`

자세한 내용은 [시작 가이드](docs/GETTING_STARTED.md)를 참고하세요.

## 📚 문서

모든 문서는 `docs/` 디렉토리에 있습니다.

### 빠른 온보딩
- **[AI 컨텍스트 (AI_CONTEXT.md)](AI_CONTEXT.md)**: 🤖 AI/신규 개발자를 위한 빠른 이해 가이드
- **[시작 가이드 (docs/GETTING_STARTED.md)](docs/GETTING_STARTED.md)**: 설치 및 실행 방법

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
python manage.py test
```

## 📝 라이선스

MIT License
