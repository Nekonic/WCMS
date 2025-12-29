# WCMS 시작하기 (Getting Started)

이 문서는 WCMS 프로젝트를 설치하고 실행하는 방법을 안내합니다.
복잡한 설정 없이 통합 관리 스크립트(`manage.py`)를 사용하여 쉽게 시작할 수 있습니다.

---

## 🚀 빠른 시작 (Quick Start)

### 1. 필수 요구사항
- Python 3.9 이상
- Git

### 2. 프로젝트 실행

프로젝트 루트에서 다음 명령어를 실행하세요. 필요한 도구(`uv`)와 의존성을 자동으로 설치하고 서버를 시작합니다.

```bash
python manage.py run
```

- **서버 주소**: http://localhost:5050
- **기본 계정**: `admin` / `admin123`

---

## 🛠 관리 스크립트 사용법

`manage.py`는 프로젝트 관리를 위한 통합 도구입니다.

| 명령어 | 설명 |
|--------|------|
| `python manage.py run` | 서버를 개발 모드로 실행합니다. (기본값) |
| `python manage.py test` | 단위 테스트를 실행합니다. |
| `python manage.py help` | 도움말을 표시합니다. |

### 수동 설정 (참고용)

만약 `manage.py`를 사용하지 않고 수동으로 설정하려면 다음 단계를 따르세요.

1. **uv 설치**:
   ```bash
   # macOS/Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # Windows
   powershell -Command "irm https://astral.sh/uv/install.ps1 | iex"
   ```

2. **의존성 설치**:
   ```bash
   uv sync
   ```

3. **서버 실행**:
   ```bash
   uv run python server/app.py
   ```

---

## 🧪 테스트 및 검증

### API 테스트
서버가 실행 중일 때, 새 터미널에서 다음 명령어로 API 상태를 확인할 수 있습니다.

```bash
curl http://localhost:5050/api/client/version
```

### 단위 테스트 실행
```bash
python manage.py test
```

---

## 📂 주요 문서 링크

- [시스템 아키텍처 (ARCHITECTURE.md)](ARCHITECTURE.md): 시스템 구조 및 설계
- [API 명세서 (API.md)](API.md): API 엔드포인트 상세 설명
- [프로젝트 상태 (PROJECT_STATUS.md)](PROJECT_STATUS.md): 현재 개발 진행 상황

---

**참고**: 이 문서는 기존의 `SERVER_START.md`, `UV_SETUP.md`, `SERVER_STARTUP_AND_TEST.md`를 통합한 문서입니다.
