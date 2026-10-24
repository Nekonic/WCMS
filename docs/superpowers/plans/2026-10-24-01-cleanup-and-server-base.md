# WCMS 2026.1 계획 1: 저장소 정리 + 서버 기반 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 기존 v0.9.x 코드를 걷어내고, PC가 PIN으로 등록해 WebSocket으로 상태를 보내면 관리자(TOTP 로그인)와 비로그인 사용자가 실습실 좌석 그리드에서 실시간으로 보는 Django 서버를 만든다.

**Architecture:** `server/` 아래 Django 5.2 + Channels 프로젝트 하나. 앱은 `accounts`(관리자 인증), `labs`(실습실, PC, 등록 PIN), `clientapi`(클라이언트 등록 HTTP + 클라이언트 WebSocket), `web`(화면, 브라우저 WebSocket)으로 나눈다. 화면은 Django 템플릿 + 빌드 없는 바닐라 JS. 채널 레이어와 캐시는 `WCMS_REDIS_URL`이 있으면 Redis, 없으면 메모리(개발, 테스트).

**Tech Stack:** Python 3.13, uv, Django 5.2, channels 4, channels-redis, daphne, pyotp, segno, pytest + pytest-django + pytest-asyncio, websockets(개발용 가짜 클라이언트)

**설계 문서:** `docs/superpowers/specs/2026-10-24-wcms-2026-1-design.md`

## 전체 계획 순서

| 순서 | 계획 | 결과물 |
|---|---|---|
| 1 | 저장소 정리 + 서버 기반 (이 문서) | 등록, 상시 연결, 실시간 그리드, TOTP 로그인, 실습실·PIN 관리 |
| 2 | 원격 명령 (서버) | CMD/PowerShell, 전원, 메시지, 파일 배포, 결과 화면, 저장된 명령, 확인 창, 감사 로그 |
| 3 | C++ 클라이언트 기반 | 서비스, 등록, WebSocket, 상태 보고, 명령 실행, 설치 스크립트, 코드 서명, 자동 업데이트 |
| 4 | 화면 | 세션 에이전트, 썸네일, 크게 보기, 스크린샷 |
| 5 | 정책 | 금지 프로그램, 원상복구 |
| 6 | 프로그램 | 설치 목록 수집, 패키지 배포, 삭제 |
| 7 | 예약 작업 + 배포 | 스케줄러, Docker, nginx 두 경로, Cloudflare |

## Global Constraints

- 버전 형식 `2026.1`. 루트 `VERSION` 파일이 기준이다.
- 패키지 관리는 uv만 쓴다 (`uv add`, `uv sync`, `uv run`). `pip` 직접 사용 금지.
- 모든 명령은 `server/` 디렉터리에서 실행한다 (`cd server`).
- 학생이 조작할 수 있는 값(창 제목, 프로세스 이름, 사용자 이름, 호스트 이름, 명령 출력)은 템플릿에서 `|safe` 금지, JS에서는 `textContent`로만 넣는다.
- 비로그인 사용자에게는 PC 이름(좌석 라벨), 온라인 여부, 사용 여부만 보인다. 호스트 이름, 사용자, 프로세스, 창 제목, IP는 보이지 않는다.
- 관리자 = `is_staff` 사용자. 로그인은 비밀번호 + TOTP 두 단계를 모두 통과해야 세션이 생긴다.
- 클라이언트 WebSocket은 `Authorization: Bearer <token>` 헤더로 인증한다. 토큰은 DB에 SHA-256 해시로만 저장한다.
- 폴링 금지. 브라우저 화면 갱신은 WebSocket(`/ws/live`)으로 한다.
- 커밋 메시지에 작성자 표기(Co-Authored-By 등)를 넣지 않는다.

---

## 파일 구조

```
VERSION                         2026.1
README.md                       짧은 소개 + 서버 실행법
CLAUDE.md                       최소 작업 규칙
.gitignore
docs/protocol.md                클라이언트-서버 프로토콜 (C++ 클라이언트 구현 기준)
server/
  pyproject.toml, uv.lock, .python-version
  manage.py
  wcms/       settings.py, urls.py, asgi.py, routing.py, views.py(healthz)
  accounts/   models.py(TOTPDevice), views.py(로그인 3단계), permissions.py(is_admin, admin_required), urls.py
              templates/accounts/{login,otp,otp_setup}.html
  labs/       models.py(Room, PC, RegistrationPin), live.py(pc_payload, broadcast_pc),
              forms.py, views.py(실습실 관리, PIN), urls.py, templates/labs/*.html
  clientapi/  protocol.py(bearer_token, clean_status, pc_group), views.py(register), consumers.py(ClientConsumer), urls.py
  web/        context.py, views.py(home, room), consumers.py(LiveConsumer), urls.py,
              templates/base.html, templates/web/{room,tile,empty}.html, static/web/{app.css,grid.js}
  tests/      conftest.py, test_*.py
  tools/      fake_client.py
```

---

### Task 1: 저장소 정리

**Files:**
- Delete: `server/`, `client/`, `api/`, `archive/`, `tests/`, `scripts/`, `manage.py`, `AI_CONTEXT.md`, `pyproject.toml`, `.flake8`, `.env.docker`, `Dockerfile.server`, `docker-compose.yml`, `docker-entrypoint.sh`, `.github/`, `docs/API.md`, `docs/ARCHITECTURE.md`, `docs/CHANGELOG.md`, `docs/DOCKER_CLIENT_SETUP.md`, `docs/GETTING_STARTED.md`, `docs/GIT_COMMIT_GUIDE.md`, `docs/PRODUCTION.md`, `docs/README.md`, `docs/SECURITY.md`, `docs/SECURITY_FINDINGS.md`, `docs/plan.md`
- Modify: `VERSION`, `README.md`, `.gitignore`
- Create: `CLAUDE.md`

**Interfaces:**
- Consumes: 없음
- Produces: 빈 `server/` 자리, `VERSION` 내용 `2026.1`

- [ ] **Step 1: 기존 파일 삭제**

```bash
git rm -r -q server client api archive tests scripts manage.py AI_CONTEXT.md pyproject.toml .flake8 .env.docker Dockerfile.server docker-compose.yml docker-entrypoint.sh .github docs/API.md docs/ARCHITECTURE.md docs/CHANGELOG.md docs/DOCKER_CLIENT_SETUP.md docs/GETTING_STARTED.md docs/GIT_COMMIT_GUIDE.md docs/PRODUCTION.md docs/README.md docs/SECURITY.md docs/SECURITY_FINDINGS.md docs/plan.md
rm -rf server client api archive tests scripts
```

`rm -rf`는 git이 추적하지 않던 잔여물(`__pycache__`, `node_modules`, 로컬 DB)을 지운다.

- [ ] **Step 2: VERSION 교체**

`VERSION` 전체 내용:

```
2026.1
```

- [ ] **Step 3: .gitignore 교체**

`.gitignore` 전체 내용:

```
__pycache__/
*.py[cod]
.venv/
.pytest_cache/
*.sqlite3
*.sqlite3-*
server/staticfiles/
server/tools/.fake_clients.json
.env
.DS_Store
.idea/
.vscode/
build/
```

- [ ] **Step 4: README.md 교체**

`README.md` 전체 내용:

```markdown
# WCMS

실습실 PC 원격 관리 시스템.

- 서버: Django (`server/`)
- 클라이언트: C++ Windows 서비스 (`client/`, 작업 예정)

설계 문서: `docs/superpowers/specs/2026-10-24-wcms-2026-1-design.md`
```

- [ ] **Step 5: CLAUDE.md 작성**

`CLAUDE.md` 전체 내용:

```markdown
# WCMS

설계: docs/superpowers/specs/2026-10-24-wcms-2026-1-design.md
계획: docs/superpowers/plans/
프로토콜: docs/protocol.md

- server/: Django + Channels. 명령은 server/ 에서 `uv run ...`. 패키지 추가는 `uv add` (pip 직접 사용 금지)
- 테스트: `cd server && uv run pytest`
- 버전: 루트 VERSION 파일 (형식 2026.1)
- 학생이 조작할 수 있는 값(창 제목, 프로세스 이름, 사용자 이름, 호스트 이름, 명령 출력)은 템플릿에서 `|safe` 금지, JS에서는 textContent만 사용
```

- [ ] **Step 6: 결과 확인**

Run: `git status --short | head -50 && ls -A`
Expected: 삭제(`D`)와 수정(`M`) 목록, 새 파일 `CLAUDE.md`. 추적 파일 기준으로 루트에는 `.gitignore CLAUDE.md LICENSE README.md VERSION docs`만 남는다.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "chore: remove v0.9.x code and docs for 2026.1 rewrite"
```

---

### Task 2: Django 프로젝트 골격

**Files:**
- Create: `server/pyproject.toml`, `server/manage.py`, `server/wcms/__init__.py`, `server/wcms/settings.py`, `server/wcms/urls.py`, `server/wcms/asgi.py`, `server/wcms/routing.py`, `server/wcms/views.py`
- Create: 앱 골격 `server/{accounts,labs,clientapi,web}/__init__.py`, `apps.py`, `migrations/__init__.py`
- Create: `server/web/context.py`
- Test: `server/tests/__init__.py`, `server/tests/conftest.py`, `server/tests/test_project.py`

**Interfaces:**
- Consumes: `VERSION`
- Produces:
  - `settings.WCMS_VERSION: str`, `settings.WCMS_CLIENT_STALE_SECONDS: int = 30`, `settings.WCMS_CLIENT_IP_HEADER: str` (빈 문자열이면 `REMOTE_ADDR` 사용)
  - `wcms.routing.websocket_urlpatterns: list` (이후 Task가 항목 추가)
  - `wcms.asgi.application`
  - 템플릿 변수 `wcms_version`
  - `GET /healthz` → `ok`

- [ ] **Step 1: pyproject.toml 작성**

`server/pyproject.toml`:

```toml
[project]
name = "wcms-server"
version = "2026.1"
requires-python = ">=3.13,<3.14"
dependencies = []

[dependency-groups]
dev = []

[tool.uv]
package = false

[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "wcms.settings"
testpaths = ["tests"]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
```

- [ ] **Step 2: 의존성 설치**

```bash
cd server
uv python pin 3.13
uv add "django>=5.2,<5.3" "channels>=4.2" "channels-redis>=4.2" "daphne>=4.1" "pyotp>=2.9" "segno>=1.6"
uv add --dev "pytest>=8" "pytest-django>=4.9" "pytest-asyncio>=0.24" "websockets>=14"
```

Expected: `uv.lock`, `.python-version` 생성, `.venv` 생성. uv가 Python 3.13을 자동으로 내려받는다.

- [ ] **Step 3: manage.py 작성**

`server/manage.py`:

```python
#!/usr/bin/env python
import os
import sys


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wcms.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 앱 골격 작성**

각 앱에 같은 형태로 세 파일을 만든다. `server/accounts/__init__.py`, `server/accounts/migrations/__init__.py`는 빈 파일.

`server/accounts/apps.py`:

```python
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = "accounts"
```

`server/labs/apps.py`:

```python
from django.apps import AppConfig


class LabsConfig(AppConfig):
    name = "labs"
```

`server/clientapi/apps.py`:

```python
from django.apps import AppConfig


class ClientapiConfig(AppConfig):
    name = "clientapi"
```

`server/web/apps.py`:

```python
from django.apps import AppConfig


class WebConfig(AppConfig):
    name = "web"
```

`labs`, `clientapi`, `web`에도 빈 `__init__.py`, `migrations/__init__.py`를 만든다. `server/wcms/__init__.py`, `server/tests/__init__.py`도 빈 파일.

- [ ] **Step 5: settings.py 작성**

`server/wcms/settings.py`:

```python
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BASE_DIR.parent


def _env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


def _read_version() -> str:
    path = REPO_DIR / "VERSION"
    return path.read_text(encoding="utf-8").strip() if path.exists() else "dev"


SECRET_KEY = os.environ.get("WCMS_SECRET_KEY", "dev-only-insecure-key")
DEBUG = os.environ.get("WCMS_DEBUG", "1") == "1"
ALLOWED_HOSTS = _env_list("WCMS_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = _env_list("WCMS_CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "daphne",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "channels",
    "accounts",
    "labs",
    "clientapi",
    "web",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "wcms.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "web.context.version",
            ],
        },
    },
]

ASGI_APPLICATION = "wcms.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("WCMS_DB_PATH", str(BASE_DIR / "db.sqlite3")),
        "OPTIONS": {
            "init_command": "PRAGMA journal_mode=WAL;",
            "transaction_mode": "IMMEDIATE",
        },
    }
}

REDIS_URL = os.environ.get("WCMS_REDIS_URL", "")
if REDIS_URL:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [REDIS_URL]},
        }
    }
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
        }
    }
else:
    CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
]
LOGIN_URL = "accounts:login"
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

LANGUAGE_CODE = "ko-kr"
TIME_ZONE = "Asia/Seoul"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

WCMS_VERSION = _read_version()
WCMS_CLIENT_STALE_SECONDS = 30
WCMS_CLIENT_IP_HEADER = os.environ.get("WCMS_CLIENT_IP_HEADER", "")
```

- [ ] **Step 6: urls, views, routing, asgi, context 작성**

`server/wcms/views.py`:

```python
from django.http import HttpRequest, HttpResponse


def healthz(request: HttpRequest) -> HttpResponse:
    return HttpResponse("ok", content_type="text/plain")
```

`server/wcms/urls.py`:

```python
from django.urls import path

from wcms.views import healthz

urlpatterns = [
    path("healthz", healthz),
]
```

`server/wcms/routing.py`:

```python
websocket_urlpatterns: list = []
```

`server/wcms/asgi.py`:

```python
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wcms.settings")
django_asgi_app = get_asgi_application()

from channels.auth import AuthMiddlewareStack  # noqa: E402
from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402

from wcms.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
    }
)
```

`server/web/context.py`:

```python
from django.conf import settings
from django.http import HttpRequest


def version(request: HttpRequest) -> dict[str, str]:
    return {"wcms_version": settings.WCMS_VERSION}
```

- [ ] **Step 7: 테스트 작성**

`server/tests/conftest.py`:

```python
import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()
```

`server/tests/test_project.py`:

```python
from django.conf import settings


def test_version_comes_from_version_file():
    assert settings.WCMS_VERSION == "2026.1"


def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.content == b"ok"
```

- [ ] **Step 8: 테스트 실행**

Run: `uv run pytest -v`
Expected: 2 passed

- [ ] **Step 9: 개발 서버가 뜨는지 확인**

Run: `uv run python manage.py check`
Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 10: Commit**

```bash
git add server
git commit -m "feat(server): Django + Channels project skeleton"
```

---

### Task 3: 실습실, PC, 등록 PIN 모델

**Files:**
- Create: `server/labs/models.py`
- Create: `server/labs/migrations/0001_initial.py` (makemigrations로 생성)
- Test: `server/tests/test_labs_models.py`

**Interfaces:**
- Consumes: `settings.WCMS_CLIENT_STALE_SECONDS`
- Produces:
  - `Room(name: str, rows: int, cols: int, aisle_after: int | None, sort_order: int)`. `aisle_after`는 1부터 센 열 번호: 그 열 뒤에 통로를 그린다.
  - `PC` 필드: `hostname, machine_guid, token_hash, client_version, specs: dict, status: dict, room: Room | None (related_name="pcs"), row: int | None, col: int | None, online: bool, connection: str, last_seen: datetime | None, registered_at`
  - `PC.hash_token(token: str) -> str`
  - `PC.register(*, hostname: str, machine_guid: str, specs: dict, version: str) -> tuple[PC, str]` (같은 `machine_guid`면 기존 레코드를 갱신하고 토큰을 새로 발급, 자리는 유지)
  - `PC.from_token(token: str) -> PC | None`
  - `PC.label -> str` (자리 있으면 `"{room.name}-{번호:02d}"`, 번호 = `row * room.cols + col + 1`, 없으면 `hostname`)
  - `PC.is_online -> bool` (`online`이고 `last_seen`이 `WCMS_CLIENT_STALE_SECONDS` 이내)
  - `RegistrationPin.issue(*, user, multi_use: bool, minutes: int) -> RegistrationPin`
  - `RegistrationPin.is_usable(now: datetime | None = None) -> bool`
  - `RegistrationPin.consume(pin: str) -> bool`

- [ ] **Step 1: 실패하는 테스트 작성**

`server/tests/test_labs_models.py`:

```python
from datetime import timedelta

import pytest
from django.utils import timezone

from labs.models import PC, RegistrationPin, Room

pytestmark = pytest.mark.django_db


def make_pc(guid: str = "guid-1", hostname: str = "LAB-01") -> tuple[PC, str]:
    return PC.register(hostname=hostname, machine_guid=guid, specs={}, version="2026.1")


def test_pin_is_six_digits():
    pin = RegistrationPin.issue(user=None, multi_use=False, minutes=10)
    assert len(pin.pin) == 6
    assert pin.pin.isdigit()


def test_single_use_pin_works_once():
    pin = RegistrationPin.issue(user=None, multi_use=False, minutes=10)
    assert RegistrationPin.consume(pin.pin) is True
    assert RegistrationPin.consume(pin.pin) is False


def test_multi_use_pin_works_many_times():
    pin = RegistrationPin.issue(user=None, multi_use=True, minutes=10)
    assert all(RegistrationPin.consume(pin.pin) for _ in range(5))


def test_expired_pin_rejected():
    pin = RegistrationPin.issue(user=None, multi_use=True, minutes=10)
    pin.expires_at = timezone.now() - timedelta(seconds=1)
    pin.save()
    assert RegistrationPin.consume(pin.pin) is False


def test_revoked_pin_rejected():
    pin = RegistrationPin.issue(user=None, multi_use=True, minutes=10)
    pin.revoked = True
    pin.save()
    assert RegistrationPin.consume(pin.pin) is False


def test_unknown_pin_rejected():
    assert RegistrationPin.consume("123456") is False


def test_register_token_resolves_and_is_stored_hashed():
    pc, token = make_pc()
    assert PC.from_token(token) == pc
    assert pc.token_hash != token
    assert pc.token_hash == PC.hash_token(token)


def test_reregister_keeps_seat_and_rotates_token():
    room = Room.objects.create(name="301", rows=5, cols=8)
    pc, old_token = make_pc()
    pc.room, pc.row, pc.col = room, 1, 4
    pc.save()

    again, new_token = make_pc(hostname="LAB-01-NEW")

    assert again.pk == pc.pk
    assert again.room == room
    assert again.hostname == "LAB-01-NEW"
    assert new_token != old_token
    assert PC.from_token(old_token) is None
    assert PC.from_token(new_token) == pc


def test_label_uses_seat_number():
    room = Room.objects.create(name="301", rows=5, cols=8)
    pc, _ = make_pc()
    assert pc.label == "LAB-01"
    pc.room, pc.row, pc.col = room, 1, 4
    pc.save()
    assert pc.label == "301-13"


def test_is_online_requires_recent_last_seen():
    pc, _ = make_pc()
    pc.online = True
    pc.last_seen = timezone.now()
    assert pc.is_online is True
    pc.last_seen = timezone.now() - timedelta(seconds=31)
    assert pc.is_online is False
    pc.online = False
    pc.last_seen = timezone.now()
    assert pc.is_online is False
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `uv run pytest tests/test_labs_models.py -v`
Expected: FAIL, `ImportError: cannot import name 'PC' from 'labs.models'`

- [ ] **Step 3: 모델 구현**

`server/labs/models.py`:

```python
import hashlib
import secrets
from datetime import datetime, timedelta

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone


class Room(models.Model):
    name = models.CharField(max_length=50, unique=True)
    rows = models.PositiveSmallIntegerField(default=5)
    cols = models.PositiveSmallIntegerField(default=8)
    aisle_after = models.PositiveSmallIntegerField(null=True, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self) -> str:
        return self.name


class PC(models.Model):
    hostname = models.CharField(max_length=64)
    machine_guid = models.CharField(max_length=64, unique=True)
    token_hash = models.CharField(max_length=64, unique=True)
    client_version = models.CharField(max_length=20, blank=True)
    specs = models.JSONField(default=dict)
    status = models.JSONField(default=dict)
    room = models.ForeignKey(
        Room, null=True, blank=True, on_delete=models.SET_NULL, related_name="pcs"
    )
    row = models.PositiveSmallIntegerField(null=True, blank=True)
    col = models.PositiveSmallIntegerField(null=True, blank=True)
    online = models.BooleanField(default=False)
    connection = models.CharField(max_length=128, blank=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["hostname"]
        constraints = [
            models.UniqueConstraint(fields=["room", "row", "col"], name="unique_seat"),
        ]

    def __str__(self) -> str:
        return self.label

    @staticmethod
    def hash_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    @classmethod
    def register(
        cls, *, hostname: str, machine_guid: str, specs: dict, version: str
    ) -> tuple["PC", str]:
        token = secrets.token_urlsafe(32)
        pc, _ = cls.objects.update_or_create(
            machine_guid=machine_guid,
            defaults={
                "hostname": hostname,
                "specs": specs,
                "client_version": version,
                "token_hash": cls.hash_token(token),
            },
        )
        return pc, token

    @classmethod
    def from_token(cls, token: str) -> "PC | None":
        return cls.objects.select_related("room").filter(token_hash=cls.hash_token(token)).first()

    @property
    def label(self) -> str:
        if self.room is not None and self.row is not None and self.col is not None:
            return f"{self.room.name}-{self.row * self.room.cols + self.col + 1:02d}"
        return self.hostname

    @property
    def is_online(self) -> bool:
        if not self.online or self.last_seen is None:
            return False
        return timezone.now() - self.last_seen < timedelta(seconds=settings.WCMS_CLIENT_STALE_SECONDS)


class RegistrationPin(models.Model):
    pin = models.CharField(max_length=6, unique=True)
    multi_use = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    used_count = models.PositiveIntegerField(default=0)
    revoked = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)

    @classmethod
    def issue(cls, *, user, multi_use: bool, minutes: int) -> "RegistrationPin":
        for _ in range(20):
            pin = f"{secrets.randbelow(10**6):06d}"
            if not cls.objects.filter(pin=pin).exists():
                return cls.objects.create(
                    pin=pin,
                    multi_use=multi_use,
                    expires_at=timezone.now() + timedelta(minutes=minutes),
                    created_by=user,
                )
        raise RuntimeError("PIN을 만들지 못했습니다.")

    def is_usable(self, now: datetime | None = None) -> bool:
        now = now or timezone.now()
        if self.revoked or now >= self.expires_at:
            return False
        return self.multi_use or self.used_count == 0

    @classmethod
    def consume(cls, pin: str) -> bool:
        with transaction.atomic():
            obj = cls.objects.select_for_update().filter(pin=pin).first()
            if obj is None or not obj.is_usable():
                return False
            obj.used_count += 1
            obj.save(update_fields=["used_count"])
            return True
```

- [ ] **Step 4: 마이그레이션 생성**

Run: `uv run python manage.py makemigrations labs`
Expected: `labs/migrations/0001_initial.py` 생성 (Room, PC, RegistrationPin)

- [ ] **Step 5: 테스트 통과 확인**

Run: `uv run pytest tests/test_labs_models.py -v`
Expected: 10 passed

- [ ] **Step 6: Commit**

```bash
git add server/labs server/tests/test_labs_models.py
git commit -m "feat(server): room, PC and registration PIN models"
```

---

### Task 4: 클라이언트 등록 API + 프로토콜 문서

**Files:**
- Create: `server/clientapi/views.py`, `server/clientapi/urls.py`
- Modify: `server/wcms/urls.py`
- Create: `docs/protocol.md`
- Test: `server/tests/test_client_register.py`

**Interfaces:**
- Consumes: `RegistrationPin.consume`, `PC.register`, `settings.WCMS_CLIENT_IP_HEADER`
- Produces:
  - `POST /client/register` JSON `{pin, hostname, machine_guid, specs?, version?}` → `201 {"pc_id": int, "token": str}`
  - 오류: `400 {"error": "bad_json" | "bad_fields" | "specs_too_large"}`, `403 {"error": "invalid_pin"}`, `429 {"error": "too_many_attempts"}` (같은 IP에서 PIN 실패 10회면 10분 차단)
  - `clientapi.views.client_ip(request) -> str`

- [ ] **Step 1: 실패하는 테스트 작성**

`server/tests/test_client_register.py`:

```python
import json

import pytest

from labs.models import PC, RegistrationPin

pytestmark = pytest.mark.django_db


def payload(pin: str, **override) -> dict:
    data = {
        "pin": pin,
        "hostname": "LAB-01",
        "machine_guid": "guid-1",
        "specs": {"cpu": "Intel Core i5-12400"},
        "version": "2026.1",
    }
    data.update(override)
    return data


def post(client, body):
    data = body if isinstance(body, str) else json.dumps(body)
    return client.post("/client/register", data=data, content_type="application/json")


def new_pin() -> str:
    return RegistrationPin.issue(user=None, multi_use=False, minutes=10).pin


def test_register_success(client):
    response = post(client, payload(new_pin()))
    assert response.status_code == 201
    body = response.json()
    pc = PC.from_token(body["token"])
    assert pc.id == body["pc_id"]
    assert pc.specs == {"cpu": "Intel Core i5-12400"}
    assert pc.client_version == "2026.1"


def test_invalid_pin(client):
    response = post(client, payload("999999"))
    assert response.status_code == 403
    assert response.json() == {"error": "invalid_pin"}


def test_bad_json(client):
    response = post(client, "{not json")
    assert response.status_code == 400
    assert response.json() == {"error": "bad_json"}


def test_non_object_json(client):
    response = post(client, "[1, 2]")
    assert response.status_code == 400
    assert response.json() == {"error": "bad_json"}


def test_missing_hostname(client):
    response = post(client, payload(new_pin(), hostname=None))
    assert response.status_code == 400
    assert response.json() == {"error": "bad_fields"}


def test_too_long_hostname(client):
    response = post(client, payload(new_pin(), hostname="x" * 65))
    assert response.status_code == 400


def test_specs_too_large(client):
    response = post(client, payload(new_pin(), specs={"x": "a" * 20000}))
    assert response.status_code == 400
    assert response.json() == {"error": "specs_too_large"}


def test_lockout_after_ten_failures(client):
    for _ in range(10):
        post(client, payload("000000"))
    response = post(client, payload(new_pin()))
    assert response.status_code == 429
    assert response.json() == {"error": "too_many_attempts"}


def test_get_not_allowed(client):
    assert client.get("/client/register").status_code == 405
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `uv run pytest tests/test_client_register.py -v`
Expected: FAIL, 404 (URL 없음)

- [ ] **Step 3: 등록 뷰 구현**

`server/clientapi/views.py`:

```python
import json

from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from labs.models import PC, RegistrationPin

MAX_PIN_FAILURES = 10
PIN_LOCK_SECONDS = 600
MAX_SPECS_BYTES = 16384


def client_ip(request: HttpRequest) -> str:
    header = settings.WCMS_CLIENT_IP_HEADER
    if header and request.META.get(header):
        return request.META[header].split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def _error(error: str, status: int = 400) -> JsonResponse:
    return JsonResponse({"error": error}, status=status)


@csrf_exempt
@require_POST
def register(request: HttpRequest) -> JsonResponse:
    fail_key = f"register-fail:{client_ip(request)}"
    if cache.get(fail_key, 0) >= MAX_PIN_FAILURES:
        return _error("too_many_attempts", 429)

    try:
        data = json.loads(request.body)
    except ValueError:
        return _error("bad_json")
    if not isinstance(data, dict):
        return _error("bad_json")

    pin = data.get("pin")
    hostname = data.get("hostname")
    machine_guid = data.get("machine_guid")
    specs = data.get("specs", {})
    version = data.get("version", "")
    if not all(isinstance(v, str) for v in (pin, hostname, machine_guid, version)):
        return _error("bad_fields")
    if not isinstance(specs, dict):
        return _error("bad_fields")
    if not (0 < len(hostname) <= 64 and 0 < len(machine_guid) <= 64 and len(version) <= 20):
        return _error("bad_fields")
    if len(json.dumps(specs)) > MAX_SPECS_BYTES:
        return _error("specs_too_large")

    if not RegistrationPin.consume(pin):
        cache.set(fail_key, cache.get(fail_key, 0) + 1, PIN_LOCK_SECONDS)
        return _error("invalid_pin", 403)

    pc, token = PC.register(
        hostname=hostname, machine_guid=machine_guid, specs=specs, version=version
    )
    return JsonResponse({"pc_id": pc.id, "token": token}, status=201)
```

`server/clientapi/urls.py`:

```python
from django.urls import path

from clientapi import views

app_name = "clientapi"

urlpatterns = [
    path("register", views.register, name="register"),
]
```

`server/wcms/urls.py` 전체:

```python
from django.urls import include, path

from wcms.views import healthz

urlpatterns = [
    path("healthz", healthz),
    path("client/", include("clientapi.urls")),
]
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `uv run pytest tests/test_client_register.py -v`
Expected: 9 passed

- [ ] **Step 5: 프로토콜 문서 작성**

`docs/protocol.md`:

````markdown
# 클라이언트-서버 프로토콜 v1

클라이언트는 학내망에서 서버 내부 주소로 직접 접속한다. 이 문서의 경로는 그 주소 기준이다.

## 1. 등록

`POST /client/register` (Content-Type: application/json)

```json
{"pin": "123456", "hostname": "LAB-01", "machine_guid": "<HKLM\\SOFTWARE\\Microsoft\\Cryptography\\MachineGuid>", "specs": {}, "version": "2026.1"}
```

| 필드 | 제한 |
|---|---|
| pin | 6자리 문자열 |
| hostname | 1~64자 |
| machine_guid | 1~64자. 같은 값으로 다시 등록하면 같은 PC로 취급하고 자리를 유지한다 |
| specs | 객체, JSON으로 16KB 이하. 키는 자유 (cpu, ram_gb, os, ip, mac 등) |
| version | 20자 이하 |

응답:

| 상태 | 본문 |
|---|---|
| 201 | `{"pc_id": 1, "token": "..."}`. 토큰은 다시 볼 수 없으므로 클라이언트가 저장한다 |
| 400 | `{"error": "bad_json" \| "bad_fields" \| "specs_too_large"}` |
| 403 | `{"error": "invalid_pin"}` |
| 429 | `{"error": "too_many_attempts"}`. 같은 IP에서 PIN 실패 10회면 10분 차단 |

## 2. WebSocket 연결

`GET /client/ws`, 헤더 `Authorization: Bearer <token>`

- 토큰이 없거나 틀리면 핸드셰이크가 403으로 거절된다. 다시 등록해야 한다.
- 같은 PC로 새 연결이 들어오면 이전 연결은 서버가 close code `4409`로 닫는다.
- 모든 메시지는 JSON 텍스트 프레임이다. 형식: `{"type": "...", ...}`
- 연결이 끊기면 재접속한다. 대기 시간은 1초에서 시작해 두 배씩 늘리고 최대 60초, 매번 0~1초 무작위 지연을 더한다.

## 3. 클라이언트 → 서버

### hello

연결 직후 한 번.

```json
{"type": "hello", "version": "2026.1"}
```

### status

10초마다. 서버는 30초 동안 status가 없으면 오프라인으로 본다.

```json
{
  "type": "status",
  "cpu": 12.5,
  "mem_used": 8123456789, "mem_total": 17179869184,
  "disk_used": 246000000000, "disk_total": 512000000000,
  "user": "Student",
  "session": "active",
  "foreground": {"process": "chrome.exe", "title": "YouTube - Chrome"}
}
```

| 필드 | 규칙 |
|---|---|
| cpu | 0 이상 숫자 (%) |
| mem_*, disk_* | 0 이상 숫자 (바이트) |
| user | 로그인한 사용자 이름, 최대 64자 |
| session | `active`(로그인, 잠금 아님) / `locked` / `none`(로그인 없음). 그 밖의 값은 `none` |
| foreground | 앞에 떠 있는 창. process 최대 128자, title 최대 256자 |

목록에 없는 필드는 버린다.

### ping

```json
{"type": "ping"}
```

서버 응답: `{"type": "pong"}`

## 4. 서버 → 클라이언트

| 메시지 | 의미 |
|---|---|
| `{"type": "pong"}` | ping 응답 |
| `{"type": "error", "error": "unknown_type"}` | 모르는 type을 받음 |

명령 메시지는 계획 2에서 추가한다.
````

- [ ] **Step 6: Commit**

```bash
git add server/clientapi server/wcms/urls.py server/tests/test_client_register.py docs/protocol.md
git commit -m "feat(server): PIN-based client registration API and protocol doc"
```

---

### Task 5: 클라이언트 WebSocket

**Files:**
- Create: `server/clientapi/protocol.py`, `server/clientapi/consumers.py`, `server/labs/live.py`
- Modify: `server/wcms/routing.py`
- Test: `server/tests/test_client_ws.py`, `server/tests/test_live_payload.py`

**Interfaces:**
- Consumes: `PC.from_token`, `PC.is_online`, `PC.label`
- Produces:
  - `clientapi.protocol.bearer_token(scope: dict) -> str | None`
  - `clientapi.protocol.clean_status(message: dict) -> dict`
  - `clientapi.protocol.pc_group(pc_id: int) -> str` (`"pc-<id>"`, 계획 2에서 명령 전달에 쓴다)
  - `labs.live.LIVE_GROUP = "live"`
  - `labs.live.pc_payload(pc: PC, *, admin: bool) -> dict`
    - 공통 키: `id, label, room_id, row, col, state, state_label`
    - 비로그인 `state`: `offline` / `in_use` / `available`
    - 관리자 `state`: `offline` / `active` / `locked` / `no_user`, 추가 키: `hostname, version, user, session, foreground, cpu, mem_used, mem_total, disk_used, disk_total`
  - `labs.live.broadcast_pc(pc_id: int) -> Awaitable[None]` → 채널 그룹 `LIVE_GROUP`에 `{"type": "pc.update", "public": dict, "admin": dict}` 전송
  - WebSocket 경로 `/client/ws` (`ClientConsumer`)

- [ ] **Step 1: payload 테스트 작성**

`server/tests/test_live_payload.py`:

```python
import pytest
from django.utils import timezone

from labs.live import pc_payload
from labs.models import PC, Room

pytestmark = pytest.mark.django_db

ADMIN_ONLY = {"hostname", "user", "session", "foreground", "cpu", "version"}


def online_pc(session: str) -> PC:
    room = Room.objects.create(name="301", rows=5, cols=8)
    pc, _ = PC.register(hostname="LAB-01", machine_guid="g1", specs={}, version="2026.1")
    pc.room, pc.row, pc.col = room, 0, 0
    pc.online = True
    pc.last_seen = timezone.now()
    pc.status = {"user": "Student", "session": session, "cpu": 10}
    pc.save()
    return pc


def test_public_payload_hides_details():
    data = pc_payload(online_pc("active"), admin=False)
    assert data["label"] == "301-01"
    assert data["state"] == "in_use"
    assert data["state_label"] == "사용 중"
    assert not ADMIN_ONLY & data.keys()


def test_public_locked_counts_as_available():
    assert pc_payload(online_pc("locked"), admin=False)["state"] == "available"


def test_admin_payload_has_details_and_session_state():
    data = pc_payload(online_pc("locked"), admin=True)
    assert data["state"] == "locked"
    assert data["user"] == "Student"
    assert ADMIN_ONLY <= data.keys()


def test_offline_state():
    pc = online_pc("active")
    pc.online = False
    assert pc_payload(pc, admin=True)["state"] == "offline"
    assert pc_payload(pc, admin=False)["state_label"] == "오프라인"
```

- [ ] **Step 2: WebSocket 테스트 작성**

`server/tests/test_client_ws.py`:

```python
import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator

from labs.models import PC
from wcms.asgi import application

pytestmark = pytest.mark.django_db(transaction=True)


@database_sync_to_async
def make_pc() -> tuple[PC, str]:
    return PC.register(hostname="LAB-01", machine_guid="g1", specs={}, version="2026.1")


@database_sync_to_async
def reload(pc_id: int) -> PC:
    return PC.objects.get(pk=pc_id)


def communicator(token: str | None) -> WebsocketCommunicator:
    headers = [(b"authorization", f"Bearer {token}".encode())] if token else []
    return WebsocketCommunicator(application, "/client/ws", headers=headers)


async def test_rejects_missing_token():
    connected, _ = await communicator(None).connect()
    assert not connected


async def test_rejects_wrong_token():
    await make_pc()
    connected, _ = await communicator("wrong").connect()
    assert not connected


async def test_connect_and_disconnect_toggle_online():
    pc, token = await make_pc()
    ws = communicator(token)
    connected, _ = await ws.connect()
    assert connected
    assert (await reload(pc.id)).online is True
    await ws.disconnect()
    assert (await reload(pc.id)).online is False


async def test_status_is_cleaned_and_stored():
    pc, token = await make_pc()
    ws = communicator(token)
    await ws.connect()
    await ws.send_json_to(
        {
            "type": "status",
            "cpu": 12.5,
            "mem_used": -1,
            "user": "Student",
            "session": "weird",
            "foreground": {"process": "chrome.exe", "title": "x" * 500},
            "evil": True,
        }
    )
    await ws.send_json_to({"type": "ping"})
    assert await ws.receive_json_from() == {"type": "pong"}

    stored = (await reload(pc.id)).status
    assert stored["cpu"] == 12.5
    assert "mem_used" not in stored
    assert stored["session"] == "none"
    assert len(stored["foreground"]["title"]) == 256
    assert "evil" not in stored
    await ws.disconnect()


async def test_hello_stores_version():
    pc, token = await make_pc()
    ws = communicator(token)
    await ws.connect()
    await ws.send_json_to({"type": "hello", "version": "2026.2"})
    await ws.send_json_to({"type": "ping"})
    await ws.receive_json_from()
    assert (await reload(pc.id)).client_version == "2026.2"
    await ws.disconnect()


async def test_unknown_type_returns_error():
    _, token = await make_pc()
    ws = communicator(token)
    await ws.connect()
    await ws.send_json_to({"type": "nope"})
    assert await ws.receive_json_from() == {"type": "error", "error": "unknown_type"}
    await ws.disconnect()


async def test_new_connection_supersedes_old():
    pc, token = await make_pc()
    first = communicator(token)
    await first.connect()
    second = communicator(token)
    await second.connect()

    closed = await first.receive_output(timeout=1)
    assert closed["type"] == "websocket.close"
    assert closed["code"] == 4409
    await first.disconnect()

    assert (await reload(pc.id)).online is True
    await second.disconnect()
    assert (await reload(pc.id)).online is False
```

- [ ] **Step 3: 테스트가 실패하는지 확인**

Run: `uv run pytest tests/test_live_payload.py tests/test_client_ws.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'labs.live'` 및 WebSocket 연결 실패

- [ ] **Step 4: labs/live.py 구현**

`server/labs/live.py`:

```python
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer

from labs.models import PC

LIVE_GROUP = "live"

STATE_LABELS = {
    "offline": "오프라인",
    "in_use": "사용 중",
    "available": "비어 있음",
    "active": "사용 중",
    "locked": "잠금",
    "no_user": "로그인 없음",
}


def _state(pc: PC, admin: bool) -> str:
    if not pc.is_online:
        return "offline"
    session = pc.status.get("session", "none")
    if admin:
        return {"active": "active", "locked": "locked"}.get(session, "no_user")
    return "in_use" if session == "active" else "available"


def pc_payload(pc: PC, *, admin: bool) -> dict:
    state = _state(pc, admin)
    data = {
        "id": pc.id,
        "label": pc.label,
        "room_id": pc.room_id,
        "row": pc.row,
        "col": pc.col,
        "state": state,
        "state_label": STATE_LABELS[state],
    }
    if admin:
        status = pc.status
        data.update(
            {
                "hostname": pc.hostname,
                "version": pc.client_version,
                "user": status.get("user", ""),
                "session": status.get("session", "none"),
                "foreground": status.get("foreground"),
                "cpu": status.get("cpu"),
                "mem_used": status.get("mem_used"),
                "mem_total": status.get("mem_total"),
                "disk_used": status.get("disk_used"),
                "disk_total": status.get("disk_total"),
            }
        )
    return data


@database_sync_to_async
def _load(pc_id: int) -> PC:
    return PC.objects.select_related("room").get(pk=pc_id)


async def broadcast_pc(pc_id: int) -> None:
    pc = await _load(pc_id)
    await get_channel_layer().group_send(
        LIVE_GROUP,
        {
            "type": "pc.update",
            "public": pc_payload(pc, admin=False),
            "admin": pc_payload(pc, admin=True),
        },
    )
```

- [ ] **Step 5: clientapi/protocol.py 구현**

`server/clientapi/protocol.py`:

```python
NUMBER_FIELDS = ("cpu", "mem_used", "mem_total", "disk_used", "disk_total")
SESSIONS = ("active", "locked", "none")


def pc_group(pc_id: int) -> str:
    return f"pc-{pc_id}"


def bearer_token(scope: dict) -> str | None:
    for name, value in scope.get("headers", []):
        if name == b"authorization":
            text = value.decode("latin-1")
            if text.startswith("Bearer "):
                return text[len("Bearer "):].strip() or None
    return None


def clean_status(message: dict) -> dict:
    status: dict = {}
    for key in NUMBER_FIELDS:
        value = message.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0:
            status[key] = value
    user = message.get("user")
    if isinstance(user, str):
        status["user"] = user[:64]
    session = message.get("session")
    status["session"] = session if session in SESSIONS else "none"
    foreground = message.get("foreground")
    if isinstance(foreground, dict):
        status["foreground"] = {
            "process": str(foreground.get("process", ""))[:128],
            "title": str(foreground.get("title", ""))[:256],
        }
    return status
```

- [ ] **Step 6: ClientConsumer 구현**

`server/clientapi/consumers.py`:

```python
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.utils import timezone

from clientapi.protocol import bearer_token, clean_status, pc_group
from labs.live import broadcast_pc
from labs.models import PC

CLOSE_SUPERSEDED = 4409


@database_sync_to_async
def _pc_id_for_token(token: str) -> int | None:
    pc = PC.from_token(token)
    return pc.id if pc else None


@database_sync_to_async
def _mark_connected(pc_id: int, channel: str) -> None:
    PC.objects.filter(pk=pc_id).update(online=True, connection=channel, last_seen=timezone.now())


@database_sync_to_async
def _mark_disconnected(pc_id: int, channel: str) -> bool:
    return PC.objects.filter(pk=pc_id, connection=channel).update(online=False, connection="") > 0


@database_sync_to_async
def _save_hello(pc_id: int, version: str) -> None:
    PC.objects.filter(pk=pc_id).update(client_version=version[:20], last_seen=timezone.now())


@database_sync_to_async
def _save_status(pc_id: int, status: dict) -> None:
    PC.objects.filter(pk=pc_id).update(status=status, last_seen=timezone.now())


class ClientConsumer(AsyncJsonWebsocketConsumer):
    pc_id: int | None = None

    async def connect(self) -> None:
        token = bearer_token(self.scope)
        pc_id = await _pc_id_for_token(token) if token else None
        if pc_id is None:
            await self.close()
            return
        self.pc_id = pc_id
        group = pc_group(pc_id)
        await self.channel_layer.group_send(group, {"type": "pc.superseded"})
        await self.channel_layer.group_add(group, self.channel_name)
        await _mark_connected(pc_id, self.channel_name)
        await self.accept()
        await broadcast_pc(pc_id)

    async def disconnect(self, code: int) -> None:
        if self.pc_id is None:
            return
        await self.channel_layer.group_discard(pc_group(self.pc_id), self.channel_name)
        if await _mark_disconnected(self.pc_id, self.channel_name):
            await broadcast_pc(self.pc_id)

    async def receive_json(self, content, **kwargs) -> None:
        kind = content.get("type") if isinstance(content, dict) else None
        if kind == "status":
            await _save_status(self.pc_id, clean_status(content))
            await broadcast_pc(self.pc_id)
        elif kind == "hello":
            version = content.get("version")
            if isinstance(version, str):
                await _save_hello(self.pc_id, version)
        elif kind == "ping":
            await self.send_json({"type": "pong"})
        else:
            await self.send_json({"type": "error", "error": "unknown_type"})

    async def pc_superseded(self, event: dict) -> None:
        await self.close(code=CLOSE_SUPERSEDED)
```

- [ ] **Step 7: 라우팅 추가**

`server/wcms/routing.py` 전체:

```python
from django.urls import path

from clientapi.consumers import ClientConsumer

websocket_urlpatterns = [
    path("client/ws", ClientConsumer.as_asgi()),
]
```

- [ ] **Step 8: 테스트 통과 확인**

Run: `uv run pytest tests/test_live_payload.py tests/test_client_ws.py -v`
Expected: 11 passed

- [ ] **Step 9: 전체 테스트**

Run: `uv run pytest`
Expected: 모두 통과

- [ ] **Step 10: Commit**

```bash
git add server/clientapi server/labs/live.py server/wcms/routing.py server/tests/test_client_ws.py server/tests/test_live_payload.py
git commit -m "feat(server): client WebSocket with status reporting and live broadcast"
```

---

### Task 6: 관리자 로그인 (비밀번호 + TOTP)

**Files:**
- Create: `server/accounts/models.py`, `server/accounts/views.py`, `server/accounts/urls.py`, `server/accounts/permissions.py`
- Create: `server/accounts/templates/accounts/login.html`, `otp.html`, `otp_setup.html`
- Create: `server/web/templates/base.html`, `server/web/static/web/app.css`
- Create: `server/accounts/migrations/0001_initial.py` (makemigrations로 생성)
- Modify: `server/wcms/urls.py`
- Test: `server/tests/test_accounts.py`

**Interfaces:**
- Consumes: Django `User` (`is_staff`가 관리자)
- Produces:
  - `TOTPDevice(user OneToOne related_name="totp", secret: str, confirmed: bool, last_used_step: int)`, `TOTPDevice.verify(code: str) -> bool` (앞뒤 30초 허용, 같은 코드 재사용 불가)
  - `accounts.permissions.is_admin(user) -> bool`, `accounts.permissions.admin_required` (뷰 데코레이터, 아니면 로그인 화면으로)
  - URL: `accounts:login` `/login/`, `accounts:otp` `/login/otp/`, `accounts:otp_setup` `/login/otp/setup/`, `accounts:logout` `/logout/` (POST만)
  - 템플릿 `base.html`: 블록 `title`, `content`, `scripts`. 사이드바 `<div class="nav-links">` 안에 메뉴 링크를 둔다. 컨텍스트 변수 `nav`가 현재 메뉴 이름
  - CSS 클래스: `shell, side, brand, nav-links, nav, on, side-foot, content, page-head, meta, card, narrow, stack, btn, pri, dng, sm, error, notice, table, tabs, tab, sr, mono, linklike, plain`

- [ ] **Step 1: 실패하는 테스트 작성**

`server/tests/test_accounts.py`:

```python
import pyotp
import pytest
from django.contrib.auth import get_user_model

from accounts.models import TOTPDevice

pytestmark = pytest.mark.django_db

PASSWORD = "pw-123456"


@pytest.fixture
def staff():
    return get_user_model().objects.create_user("admin", password=PASSWORD, is_staff=True)


@pytest.fixture
def device(staff):
    return TOTPDevice.objects.create(user=staff, secret=pyotp.random_base32(), confirmed=True)


def password_step(client, username="admin", password=PASSWORD, next_url=""):
    return client.post("/login/", {"username": username, "password": password, "next": next_url})


def logged_in(client) -> bool:
    return "_auth_user_id" in client.session


def test_login_page_renders(client):
    response = client.get("/login/")
    assert response.status_code == 200
    assert "관리자 로그인" in response.content.decode()


def test_wrong_password(client, staff):
    response = password_step(client, password="wrong")
    assert response.status_code == 200
    assert "올바르지 않습니다" in response.content.decode()
    assert not logged_in(client)


def test_non_staff_rejected(client):
    get_user_model().objects.create_user("student", password=PASSWORD)
    response = password_step(client, username="student")
    assert response.status_code == 200
    assert not logged_in(client)


def test_first_login_requires_totp_setup(client, staff):
    response = password_step(client)
    assert response.url == "/login/otp/setup/"
    assert not logged_in(client)

    page = client.get("/login/otp/setup/")
    assert page.status_code == 200
    assert "<svg" in page.content.decode()

    secret = TOTPDevice.objects.get(user=staff).secret
    response = client.post("/login/otp/setup/", {"code": pyotp.TOTP(secret).now()})
    assert response.status_code == 302
    assert TOTPDevice.objects.get(user=staff).confirmed is True
    assert logged_in(client)


def test_password_alone_does_not_log_in(client, device):
    response = password_step(client)
    assert response.url == "/login/otp/"
    assert not logged_in(client)


def test_otp_login(client, device):
    password_step(client)
    response = client.post("/login/otp/", {"code": pyotp.TOTP(device.secret).now()})
    assert response.status_code == 302
    assert response.url == "/"
    assert logged_in(client)


def test_otp_lockout_after_five_wrong_codes(client, device):
    password_step(client)
    for _ in range(4):
        response = client.post("/login/otp/", {"code": "abcdef"})
        assert response.status_code == 200
    response = client.post("/login/otp/", {"code": "abcdef"})
    assert response.url == "/login/"
    assert client.get("/login/otp/").url == "/login/"
    assert not logged_in(client)


def test_otp_page_without_password_step_redirects(client, device):
    assert client.get("/login/otp/").url == "/login/"


def test_code_cannot_be_reused(device):
    code = pyotp.TOTP(device.secret).now()
    assert device.verify(code) is True
    assert device.verify(code) is False


def test_open_redirect_blocked(client, device):
    password_step(client, next_url="https://evil.example/")
    response = client.post("/login/otp/", {"code": pyotp.TOTP(device.secret).now()})
    assert response.url == "/"


def test_local_next_kept(client, device):
    password_step(client, next_url="/pins/")
    response = client.post("/login/otp/", {"code": pyotp.TOTP(device.secret).now()})
    assert response.url == "/pins/"


def test_logout_requires_post(client, staff):
    client.force_login(staff)
    assert client.get("/logout/").status_code == 405
    client.post("/logout/")
    assert not logged_in(client)
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `uv run pytest tests/test_accounts.py -v`
Expected: FAIL, `ImportError: cannot import name 'TOTPDevice'`

- [ ] **Step 3: 모델과 권한 헬퍼 구현**

`server/accounts/models.py`:

```python
import hmac
import time

import pyotp
from django.conf import settings
from django.db import models

STEP_SECONDS = 30


class TOTPDevice(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="totp"
    )
    secret = models.CharField(max_length=64)
    confirmed = models.BooleanField(default=False)
    last_used_step = models.BigIntegerField(default=0)

    def verify(self, code: str) -> bool:
        code = code.replace(" ", "").strip()
        if not code.isdigit():
            return False
        totp = pyotp.TOTP(self.secret)
        current = int(time.time() // STEP_SECONDS)
        for step in (current - 1, current, current + 1):
            if step <= self.last_used_step:
                continue
            if hmac.compare_digest(totp.at(step * STEP_SECONDS), code):
                self.last_used_step = step
                self.save(update_fields=["last_used_step"])
                return True
        return False
```

`server/accounts/permissions.py`:

```python
from django.contrib.auth.decorators import user_passes_test


def is_admin(user) -> bool:
    return bool(user is not None and user.is_authenticated and user.is_active and user.is_staff)


admin_required = user_passes_test(is_admin, login_url="accounts:login")
```

- [ ] **Step 4: 마이그레이션 생성**

Run: `uv run python manage.py makemigrations accounts`
Expected: `accounts/migrations/0001_initial.py` 생성 (TOTPDevice)

- [ ] **Step 5: 뷰와 URL 구현**

`server/accounts/views.py`:

```python
import pyotp
import segno
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from accounts.models import TOTPDevice

PENDING_KEY = "pending_user_id"
NEXT_KEY = "pending_next"
ATTEMPTS_KEY = "otp_attempts"
MAX_ATTEMPTS = 5
BACKEND = "django.contrib.auth.backends.ModelBackend"
WRONG_CODE = "인증 코드가 올바르지 않습니다."


def _safe_next(request: HttpRequest, url: str | None) -> str:
    if url and url_has_allowed_host_and_scheme(
        url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return url
    return "/"


def _clear_pending(request: HttpRequest) -> None:
    for key in (PENDING_KEY, NEXT_KEY, ATTEMPTS_KEY):
        request.session.pop(key, None)


def _pending_user(request: HttpRequest):
    user_id = request.session.get(PENDING_KEY)
    if user_id is None:
        return None
    return get_user_model().objects.filter(pk=user_id, is_active=True, is_staff=True).first()


def _finish_login(request: HttpRequest, user) -> HttpResponse:
    next_url = request.session.get(NEXT_KEY, "/")
    _clear_pending(request)
    login(request, user, backend=BACKEND)
    return redirect(next_url)


def _count_failure(request: HttpRequest) -> bool:
    """실패 횟수를 올리고, 한도에 닿으면 대기 중인 로그인을 버린다."""
    request.session[ATTEMPTS_KEY] = request.session.get(ATTEMPTS_KEY, 0) + 1
    if request.session[ATTEMPTS_KEY] >= MAX_ATTEMPTS:
        _clear_pending(request)
        return True
    return False


def login_view(request: HttpRequest) -> HttpResponse:
    error = ""
    if request.method == "POST":
        user = authenticate(
            request,
            username=request.POST.get("username", ""),
            password=request.POST.get("password", ""),
        )
        if user is not None and user.is_staff:
            request.session[PENDING_KEY] = user.pk
            request.session[NEXT_KEY] = _safe_next(request, request.POST.get("next"))
            request.session[ATTEMPTS_KEY] = 0
            if TOTPDevice.objects.filter(user=user, confirmed=True).exists():
                return redirect("accounts:otp")
            return redirect("accounts:otp_setup")
        error = "아이디 또는 비밀번호가 올바르지 않습니다."
    return render(
        request, "accounts/login.html", {"error": error, "next": request.GET.get("next", "")}
    )


def otp_view(request: HttpRequest) -> HttpResponse:
    user = _pending_user(request)
    if user is None:
        return redirect("accounts:login")
    device = TOTPDevice.objects.filter(user=user, confirmed=True).first()
    if device is None:
        return redirect("accounts:otp_setup")
    error = ""
    if request.method == "POST":
        if device.verify(request.POST.get("code", "")):
            return _finish_login(request, user)
        if _count_failure(request):
            return redirect("accounts:login")
        error = WRONG_CODE
    return render(request, "accounts/otp.html", {"error": error})


def otp_setup_view(request: HttpRequest) -> HttpResponse:
    user = _pending_user(request)
    if user is None:
        return redirect("accounts:login")
    if TOTPDevice.objects.filter(user=user, confirmed=True).exists():
        return redirect("accounts:otp")
    device, _ = TOTPDevice.objects.get_or_create(
        user=user, defaults={"secret": pyotp.random_base32()}
    )
    error = ""
    if request.method == "POST":
        if device.verify(request.POST.get("code", "")):
            device.confirmed = True
            device.save(update_fields=["confirmed"])
            return _finish_login(request, user)
        if _count_failure(request):
            return redirect("accounts:login")
        error = WRONG_CODE
    uri = pyotp.TOTP(device.secret).provisioning_uri(name=user.get_username(), issuer_name="WCMS")
    context = {
        "error": error,
        "qr_svg": segno.make(uri, error="m").svg_inline(scale=5),
        "secret": device.secret,
    }
    return render(request, "accounts/otp_setup.html", context)


@require_POST
def logout_view(request: HttpRequest) -> HttpResponse:
    logout(request)
    return redirect("/")
```

`server/accounts/urls.py`:

```python
from django.urls import path

from accounts import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("login/otp/", views.otp_view, name="otp"),
    path("login/otp/setup/", views.otp_setup_view, name="otp_setup"),
    path("logout/", views.logout_view, name="logout"),
]
```

`server/wcms/urls.py` 전체:

```python
from django.urls import include, path

from wcms.views import healthz

urlpatterns = [
    path("healthz", healthz),
    path("client/", include("clientapi.urls")),
    path("", include("accounts.urls")),
]
```

- [ ] **Step 6: base.html과 CSS 작성**

`server/web/templates/base.html`:

```html
{% load static %}<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{% block title %}WCMS{% endblock %}</title>
<link rel="stylesheet" href="{% static 'web/app.css' %}">
</head>
<body>
<div class="shell">
<nav class="side" aria-label="주 메뉴">
<div class="brand"><span class="brand-name">WCMS</span><span class="brand-ver">{{ wcms_version }}</span></div>
<div class="nav-links"></div>
<div class="side-foot">
{% if user.is_authenticated and user.is_staff %}
<span>{{ user.get_username }}</span>
<form method="post" action="{% url 'accounts:logout' %}">{% csrf_token %}<button type="submit" class="linklike">로그아웃</button></form>
{% else %}
<a href="{% url 'accounts:login' %}">관리자 로그인</a>
{% endif %}
</div>
</nav>
<main class="content">
{% block content %}{% endblock %}
</main>
</div>
{% block scripts %}{% endblock %}
</body>
</html>
```

`server/web/static/web/app.css`:

```css
:root {
  --ground: #F4F5F7;
  --surface: #FFFFFF;
  --ink: #15171C;
  --muted: #5B616E;
  --line: #E1E4EA;
  --line-soft: #EEF0F3;
  --side: #111318;
  --side-ink: #C9CDD6;
  --side-muted: #8B919E;
  --accent: #2449D8;
  --accent-dark: #1A36A8;
  --ok: #13804A;
  --danger: #B42318;
  --warn-bg: #FFF4E5;
  --warn-ink: #8A3A00;
}

* { box-sizing: border-box; }
body { margin: 0; background: var(--ground); color: var(--ink); font-family: "IBM Plex Sans KR", system-ui, sans-serif; font-size: 14px; }
a { color: var(--accent); }
a:hover { color: var(--accent-dark); }
h1 { margin: 0; font-size: 26px; }
h2 { margin: 0 0 12px; font-size: 16px; }

.shell { min-height: 100vh; display: flex; flex-wrap: wrap; }
.side { flex: 1 1 220px; background: var(--side); padding: 20px 14px; display: flex; flex-direction: column; gap: 4px; }
.brand { display: flex; align-items: baseline; gap: 8px; padding: 4px 12px 20px; }
.brand-name { font-weight: 700; font-size: 18px; color: #FFFFFF; letter-spacing: 0.04em; }
.brand-ver { font-size: 12px; color: var(--side-muted); }
.nav-links { display: flex; flex-direction: column; gap: 4px; flex: 1; }
.nav { display: flex; align-items: center; min-height: 44px; padding: 0 12px; border-radius: 8px; color: var(--side-ink); text-decoration: none; }
.nav:hover { background: #1C1F26; color: #FFFFFF; }
.nav.on { background: #262A36; color: #FFFFFF; font-weight: 600; }
.side-foot { display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 12px; border-top: 1px solid #262A36; color: var(--side-ink); font-size: 13px; }
.side-foot a, .side-foot .linklike { color: var(--side-muted); }
.content { flex: 999 1 560px; min-width: 0; padding: 28px 32px 40px; display: flex; flex-direction: column; gap: 20px; }

.page-head { display: flex; flex-wrap: wrap; align-items: flex-end; justify-content: space-between; gap: 16px; }
.meta { color: var(--muted); margin: 4px 0 0; }
.card { background: var(--surface); border: 1px solid var(--line); border-radius: 14px; padding: 20px; }
.narrow { max-width: 420px; width: 100%; }
.stack { display: flex; flex-direction: column; gap: 10px; }
.stack label { font-size: 13px; font-weight: 600; color: #3D424D; }
input, select, textarea { min-height: 44px; padding: 0 12px; border: 1px solid #D5D9E0; border-radius: 8px; font: inherit; background: #FFFFFF; color: var(--ink); }
textarea { padding: 12px; }

.btn { display: inline-flex; align-items: center; justify-content: center; gap: 6px; min-height: 44px; padding: 0 16px; border-radius: 8px; border: 1px solid #D5D9E0; background: #FFFFFF; color: var(--ink); font: inherit; font-weight: 500; cursor: pointer; text-decoration: none; }
.btn:hover { background: #F1F3F6; color: var(--ink); }
.btn.pri { background: var(--accent); border-color: var(--accent); color: #FFFFFF; }
.btn.pri:hover { background: var(--accent-dark); color: #FFFFFF; }
.btn.dng { color: var(--danger); border-color: #EBC3BF; }
.btn.sm { min-height: 36px; padding: 0 12px; font-size: 13px; }
.linklike { background: none; border: 0; padding: 0; font: inherit; cursor: pointer; text-decoration: underline; }

.error { margin: 0; padding: 10px 12px; border-radius: 8px; background: #FCE9E7; color: #A3211A; }
.notice { margin: 0; padding: 10px 12px; border-radius: 8px; background: #E6ECFB; color: var(--accent-dark); }

.table { width: 100%; border-collapse: collapse; }
.table th { text-align: left; font-size: 12px; font-weight: 600; color: var(--muted); padding: 10px 12px; border-bottom: 1px solid var(--line-soft); }
.table td { padding: 10px 12px; border-bottom: 1px solid var(--line-soft); }

.tabs { display: flex; flex-wrap: wrap; gap: 6px; padding: 4px; background: #E9ECF1; border-radius: 10px; align-self: flex-start; }
.tab { display: inline-flex; align-items: center; min-height: 40px; padding: 0 16px; border-radius: 8px; color: #3D424D; text-decoration: none; font-weight: 500; border: 1px solid transparent; }
.tab:hover { background: #DDE1E8; color: var(--ink); }
.tab.on { background: #FFFFFF; border-color: #D5D9E0; color: var(--ink); font-weight: 600; }

.sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
.mono { font-family: "JetBrains Mono", ui-monospace, monospace; }
.plain { margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 6px; }
```

- [ ] **Step 7: 로그인 템플릿 작성**

`server/accounts/templates/accounts/login.html`:

```html
{% extends "base.html" %}
{% block title %}로그인 · WCMS{% endblock %}
{% block content %}
<section class="card narrow">
<h1>관리자 로그인</h1>
<form method="post" class="stack">
{% csrf_token %}
{% if error %}<p class="error" role="alert">{{ error }}</p>{% endif %}
<input type="hidden" name="next" value="{{ next }}">
<label for="id_username">아이디</label>
<input id="id_username" name="username" autocomplete="username" required autofocus>
<label for="id_password">비밀번호</label>
<input id="id_password" name="password" type="password" autocomplete="current-password" required>
<button type="submit" class="btn pri">다음</button>
</form>
</section>
{% endblock %}
```

`server/accounts/templates/accounts/otp.html`:

```html
{% extends "base.html" %}
{% block title %}인증 코드 · WCMS{% endblock %}
{% block content %}
<section class="card narrow">
<h1>인증 코드</h1>
<form method="post" class="stack">
{% csrf_token %}
{% if error %}<p class="error" role="alert">{{ error }}</p>{% endif %}
<label for="id_code">인증 앱의 6자리 코드</label>
<input id="id_code" name="code" inputmode="numeric" autocomplete="one-time-code" maxlength="7" required autofocus>
<button type="submit" class="btn pri">로그인</button>
</form>
</section>
{% endblock %}
```

`server/accounts/templates/accounts/otp_setup.html`:

```html
{% extends "base.html" %}
{% block title %}인증 앱 등록 · WCMS{% endblock %}
{% block content %}
<section class="card narrow">
<h1>인증 앱 등록</h1>
<p class="meta">인증 앱(Google Authenticator 등)으로 QR 코드를 찍고, 앱에 나온 6자리 코드를 입력하세요.</p>
{# qr_svg는 서버가 만든 QR 이미지라 사용자 입력이 들어가지 않는다 #}
<div>{{ qr_svg|safe }}</div>
<p class="meta">직접 입력: <span class="mono">{{ secret }}</span></p>
<form method="post" class="stack">
{% csrf_token %}
{% if error %}<p class="error" role="alert">{{ error }}</p>{% endif %}
<label for="id_code">6자리 코드</label>
<input id="id_code" name="code" inputmode="numeric" autocomplete="one-time-code" maxlength="7" required autofocus>
<button type="submit" class="btn pri">등록하고 로그인</button>
</form>
</section>
{% endblock %}
```

- [ ] **Step 8: 테스트 통과 확인**

Run: `uv run pytest tests/test_accounts.py -v`
Expected: 12 passed

- [ ] **Step 9: Commit**

```bash
git add server/accounts server/web/templates server/web/static server/wcms/urls.py server/tests/test_accounts.py
git commit -m "feat(server): admin login with password and TOTP"
```

---

### Task 7: 실시간 실습실 그리드

**Files:**
- Create: `server/web/views.py`, `server/web/urls.py`, `server/web/consumers.py`
- Create: `server/web/templates/web/room.html`, `server/web/templates/web/tile.html`, `server/web/templates/web/empty.html`
- Create: `server/web/static/web/grid.js`
- Modify: `server/web/static/web/app.css` (그리드 스타일 추가), `server/web/templates/base.html` (메뉴), `server/wcms/urls.py`, `server/wcms/routing.py`
- Test: `server/tests/test_web.py`, `server/tests/test_live_ws.py`

**Interfaces:**
- Consumes: `pc_payload`, `broadcast_pc`, `LIVE_GROUP`, `is_admin`, `Room`, `PC`
- Produces:
  - URL `web:home` `/` (첫 실습실로 이동, 없으면 안내), `web:room` `/rooms/<room_id>/`
  - WebSocket `/ws/live` (`LiveConsumer`, Origin 검사). 서버 → 브라우저 `{"type": "pc", "pc": <pc_payload>}`
  - 타일 DOM: `<article class="tile st-<state>" data-pc-id="<id>">` 안에 `data-field="screen" | "state" | "user" | "foreground"` 요소. 계획 4에서 `.screen` 안에 썸네일을 넣는다

- [ ] **Step 1: 화면 테스트 작성**

`server/tests/test_web.py`:

```python
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from labs.models import PC, Room

pytestmark = pytest.mark.django_db


@pytest.fixture
def room_with_pc():
    room = Room.objects.create(name="301", rows=2, cols=4, aisle_after=2)
    pc, _ = PC.register(hostname="LAB-HOST-01", machine_guid="g1", specs={}, version="2026.1")
    pc.room, pc.row, pc.col = room, 0, 1
    pc.online = True
    pc.last_seen = timezone.now()
    pc.status = {
        "user": "StudentName",
        "session": "active",
        "foreground": {"process": "chrome.exe", "title": "<script>alert(1)</script>"},
    }
    pc.save()
    return room, pc


@pytest.fixture
def admin_client(client):
    user = get_user_model().objects.create_user("admin", password="pw-123456", is_staff=True)
    client.force_login(user)
    return client


def test_home_redirects_to_first_room(client, room_with_pc):
    room, _ = room_with_pc
    assert client.get("/").url == f"/rooms/{room.id}/"


def test_home_without_rooms(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "등록된 실습실이 없습니다" in response.content.decode()


def test_anonymous_sees_state_only(client, room_with_pc):
    room, _ = room_with_pc
    html = client.get(f"/rooms/{room.id}/").content.decode()
    assert "301-02" in html
    assert "사용 중" in html
    assert "StudentName" not in html
    assert "chrome.exe" not in html
    assert "LAB-HOST-01" not in html


def test_admin_sees_details_escaped(admin_client, room_with_pc):
    room, _ = room_with_pc
    html = admin_client.get(f"/rooms/{room.id}/").content.decode()
    assert "StudentName" in html
    assert "chrome.exe" in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<script>alert(1)</script>" not in html


def test_aisle_and_empty_seats_rendered(client, room_with_pc):
    room, _ = room_with_pc
    html = client.get(f"/rooms/{room.id}/").content.decode()
    assert html.count('class="aisle"') == 2
    assert html.count("st-empty") == 7


def test_unknown_room_404(client):
    assert client.get("/rooms/999/").status_code == 404
```

- [ ] **Step 2: 브라우저 WebSocket 테스트 작성**

`server/tests/test_live_ws.py`:

```python
import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone

from labs.live import broadcast_pc
from labs.models import PC
from wcms.asgi import application
from web.consumers import LiveConsumer

pytestmark = pytest.mark.django_db(transaction=True)


@database_sync_to_async
def make_pc() -> PC:
    pc, _ = PC.register(hostname="LAB-01", machine_guid="g1", specs={}, version="2026.1")
    pc.online = True
    pc.last_seen = timezone.now()
    pc.status = {"user": "Student", "session": "active"}
    pc.save()
    return pc


@database_sync_to_async
def make_staff():
    return get_user_model().objects.create_user("admin", password="pw-123456", is_staff=True)


async def connect_as(user) -> WebsocketCommunicator:
    ws = WebsocketCommunicator(LiveConsumer.as_asgi(), "/ws/live")
    ws.scope["user"] = user
    connected, _ = await ws.connect()
    assert connected
    return ws


async def test_anonymous_receives_public_payload():
    pc = await make_pc()
    ws = await connect_as(AnonymousUser())
    await broadcast_pc(pc.id)
    message = await ws.receive_json_from()
    assert message["type"] == "pc"
    assert message["pc"]["state"] == "in_use"
    assert "user" not in message["pc"]
    await ws.disconnect()


async def test_admin_receives_details():
    pc = await make_pc()
    ws = await connect_as(await make_staff())
    await broadcast_pc(pc.id)
    message = await ws.receive_json_from()
    assert message["pc"]["user"] == "Student"
    assert message["pc"]["state"] == "active"
    await ws.disconnect()


async def test_foreign_origin_rejected():
    ws = WebsocketCommunicator(
        application,
        "/ws/live",
        headers=[(b"origin", b"http://evil.example"), (b"host", b"localhost")],
    )
    connected, _ = await ws.connect()
    assert not connected


async def test_same_origin_accepted():
    ws = WebsocketCommunicator(
        application,
        "/ws/live",
        headers=[(b"origin", b"http://localhost"), (b"host", b"localhost")],
    )
    connected, _ = await ws.connect()
    assert connected
    await ws.disconnect()
```

- [ ] **Step 3: 테스트가 실패하는지 확인**

Run: `uv run pytest tests/test_web.py tests/test_live_ws.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'web.consumers'` 및 404

- [ ] **Step 4: LiveConsumer 구현**

`server/web/consumers.py`:

```python
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from accounts.permissions import is_admin
from labs.live import LIVE_GROUP


class LiveConsumer(AsyncJsonWebsocketConsumer):
    admin = False

    async def connect(self) -> None:
        self.admin = is_admin(self.scope.get("user"))
        await self.channel_layer.group_add(LIVE_GROUP, self.channel_name)
        await self.accept()

    async def disconnect(self, code: int) -> None:
        await self.channel_layer.group_discard(LIVE_GROUP, self.channel_name)

    async def pc_update(self, event: dict) -> None:
        await self.send_json({"type": "pc", "pc": event["admin"] if self.admin else event["public"]})
```

`server/wcms/routing.py` 전체:

```python
from channels.security.websocket import AllowedHostsOriginValidator
from django.urls import path

from clientapi.consumers import ClientConsumer
from web.consumers import LiveConsumer

websocket_urlpatterns = [
    path("client/ws", ClientConsumer.as_asgi()),
    path("ws/live", AllowedHostsOriginValidator(LiveConsumer.as_asgi())),
]
```

클라이언트 경로에는 Origin 검사를 붙이지 않는다. C++ 클라이언트는 Origin 헤더를 보내지 않고, 토큰으로 인증한다.

- [ ] **Step 5: 뷰와 URL 구현**

`server/web/views.py`:

```python
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from accounts.permissions import is_admin
from labs.live import pc_payload
from labs.models import PC, Room


def _grid_columns(room: Room) -> str:
    if room.aisle_after:
        left = room.aisle_after
        right = room.cols - room.aisle_after
        return f"repeat({left}, minmax(0, 1fr)) 24px repeat({right}, minmax(0, 1fr))"
    return f"repeat({room.cols}, minmax(0, 1fr))"


def _cells(room: Room, by_seat: dict[tuple[int, int], dict]) -> list[dict]:
    cells: list[dict] = []
    for row in range(room.rows):
        for col in range(room.cols):
            cells.append(
                {"kind": "seat", "pc": by_seat.get((row, col)), "number": row * room.cols + col + 1}
            )
            if room.aisle_after and col + 1 == room.aisle_after:
                cells.append({"kind": "aisle"})
    return cells


def home(request: HttpRequest) -> HttpResponse:
    room = Room.objects.first()
    if room is None:
        return render(request, "web/empty.html", {"nav": "rooms"})
    return redirect("web:room", room_id=room.id)


def room_view(request: HttpRequest, room_id: int) -> HttpResponse:
    room = get_object_or_404(Room, pk=room_id)
    admin = is_admin(request.user)
    payloads = [pc_payload(pc, admin=admin) for pc in room.pcs.select_related("room")]
    by_seat = {(p["row"], p["col"]): p for p in payloads}
    context = {
        "nav": "rooms",
        "room": room,
        "rooms": Room.objects.all(),
        "cells": _cells(room, by_seat),
        "grid_columns": _grid_columns(room),
        "is_admin": admin,
        "online_count": sum(1 for p in payloads if p["state"] != "offline"),
        "total": len(payloads),
        "unassigned": PC.objects.filter(room__isnull=True) if admin else [],
    }
    return render(request, "web/room.html", context)
```

`server/web/urls.py`:

```python
from django.urls import path

from web import views

app_name = "web"

urlpatterns = [
    path("", views.home, name="home"),
    path("rooms/<int:room_id>/", views.room_view, name="room"),
]
```

`server/wcms/urls.py` 전체:

```python
from django.urls import include, path

from wcms.views import healthz

urlpatterns = [
    path("healthz", healthz),
    path("client/", include("clientapi.urls")),
    path("", include("accounts.urls")),
    path("", include("web.urls")),
]
```

- [ ] **Step 6: 템플릿 작성**

`server/web/templates/web/tile.html`:

```html
<article class="tile st-{{ pc.state }}" data-pc-id="{{ pc.id }}">
<div class="screen"><span data-field="screen">{{ pc.state_label }}</span></div>
<div class="tile-foot"><span class="tile-name">{{ pc.label }}</span><span class="tile-state" data-field="state">{{ pc.state_label }}</span></div>
{% if is_admin %}
<div class="tile-detail"><span data-field="user">{{ pc.user }}</span><span data-field="foreground">{% if pc.foreground %}{{ pc.foreground.process }}{% if pc.foreground.title %} · {{ pc.foreground.title }}{% endif %}{% endif %}</span></div>
{% endif %}
</article>
```

`server/web/templates/web/room.html`:

```html
{% extends "base.html" %}
{% load static %}
{% block title %}{{ room.name }} · WCMS{% endblock %}
{% block content %}
<header class="page-head">
<div>
<h1>실습실 {{ room.name }}</h1>
<p class="meta">온라인 {{ online_count }} / {{ total }}</p>
</div>
</header>
<nav class="tabs" aria-label="실습실">
{% for r in rooms %}<a class="tab{% if r.id == room.id %} on{% endif %}" href="{% url 'web:room' r.id %}"{% if r.id == room.id %} aria-current="page"{% endif %}>{{ r.name }}</a>{% endfor %}
</nav>
<section class="card" aria-label="좌석 배치">
<div class="front"><span>교탁</span></div>
<div class="seat-scroll">
<div class="seat-grid" data-live-grid style="grid-template-columns: {{ grid_columns }}">
{% for cell in cells %}
{% if cell.kind == "aisle" %}<div class="aisle" aria-hidden="true"></div>
{% elif cell.pc %}{% include "web/tile.html" with pc=cell.pc %}
{% else %}<div class="tile st-empty"><span class="tile-name">{{ cell.number }}</span></div>
{% endif %}
{% endfor %}
</div>
</div>
</section>
{% if is_admin and unassigned %}
<section class="card">
<h2>자리 미배정 PC</h2>
<ul class="plain">{% for pc in unassigned %}<li>{{ pc.hostname }}</li>{% endfor %}</ul>
</section>
{% endif %}
{% endblock %}
{% block scripts %}<script src="{% static 'web/grid.js' %}" defer></script>{% endblock %}
```

`server/web/templates/web/empty.html`:

```html
{% extends "base.html" %}
{% block content %}
<section class="card narrow">
<h1>실습실</h1>
<p class="meta">등록된 실습실이 없습니다. 관리자가 실습실 관리에서 추가해야 합니다.</p>
</section>
{% endblock %}
```

- [ ] **Step 7: 사이드바 메뉴 추가**

`server/web/templates/base.html`에서

```html
<div class="nav-links"></div>
```

를 아래로 바꾼다.

```html
<div class="nav-links">
<a class="nav{% if nav == 'rooms' %} on{% endif %}" href="{% url 'web:home' %}">실습실</a>
</div>
```

- [ ] **Step 8: grid.js 작성**

`server/web/static/web/grid.js`:

```javascript
(function () {
  "use strict";
  const grid = document.querySelector("[data-live-grid]");
  if (!grid) return;

  const scheme = location.protocol === "https:" ? "wss" : "ws";
  let delay = 1000;

  function setText(tile, field, text) {
    const el = tile.querySelector('[data-field="' + field + '"]');
    if (el) el.textContent = text;
  }

  function render(pc) {
    const tile = grid.querySelector('[data-pc-id="' + pc.id + '"]');
    if (!tile) return;
    tile.className = "tile st-" + pc.state;
    setText(tile, "screen", pc.state_label);
    setText(tile, "state", pc.state_label);
    if ("user" in pc) setText(tile, "user", pc.user || "");
    if ("foreground" in pc) {
      const fg = pc.foreground;
      setText(tile, "foreground", fg ? [fg.process, fg.title].filter(Boolean).join(" · ") : "");
    }
  }

  function connect() {
    const ws = new WebSocket(scheme + "://" + location.host + "/ws/live");
    ws.onopen = function () { delay = 1000; };
    ws.onmessage = function (event) {
      const message = JSON.parse(event.data);
      if (message.type === "pc") render(message.pc);
    };
    ws.onclose = function () {
      setTimeout(connect, delay + Math.random() * 1000);
      delay = Math.min(delay * 2, 30000);
    };
  }

  connect();
})();
```

- [ ] **Step 9: 그리드 CSS 추가**

`server/web/static/web/app.css` 끝에 추가:

```css
.front { display: flex; justify-content: center; margin-bottom: 16px; }
.front span { font-size: 12px; color: var(--muted); padding: 4px 40px; border: 1px dashed #C4C9D2; border-radius: 6px; }
.seat-scroll { overflow-x: auto; }
.seat-grid { display: grid; gap: 12px; min-width: 960px; }
.tile { display: flex; flex-direction: column; background: var(--surface); border: 1px solid var(--line); border-radius: 10px; overflow: hidden; min-height: 120px; }
.screen { aspect-ratio: 16 / 10; display: flex; align-items: center; justify-content: center; background: #2F5C7A; color: #FFFFFF; font-size: 12px; }
.tile-foot { display: flex; align-items: center; justify-content: space-between; gap: 6px; padding: 8px 10px; }
.tile-name { font-size: 13px; font-weight: 600; }
.tile-state { font-size: 12px; color: var(--muted); }
.tile-detail { display: flex; flex-direction: column; gap: 2px; padding: 0 10px 8px; font-size: 12px; color: var(--muted); overflow: hidden; }
.tile-detail span { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.st-offline .screen { background: #2A2D34; color: #A9AFBB; }
.st-no_user .screen, .st-available .screen { background: #3B4A5A; }
.st-locked .screen { background: #4A3F2A; }
.st-active .tile-state, .st-in_use .tile-state { color: var(--ok); font-weight: 600; }
.st-empty { align-items: center; justify-content: center; background: transparent; border-style: dashed; color: var(--muted); }
.aisle { min-height: 1px; }
```

- [ ] **Step 10: 테스트 통과 확인**

Run: `uv run pytest tests/test_web.py tests/test_live_ws.py -v`
Expected: 10 passed

- [ ] **Step 11: 전체 테스트**

Run: `uv run pytest`
Expected: 모두 통과

- [ ] **Step 12: Commit**

```bash
git add server/web server/wcms server/tests/test_web.py server/tests/test_live_ws.py
git commit -m "feat(server): live room seat grid for admins and anonymous viewers"
```

---

### Task 8: 실습실 관리 + 등록 PIN 화면

**Files:**
- Create: `server/labs/forms.py`, `server/labs/views.py`, `server/labs/urls.py`
- Create: `server/labs/templates/labs/rooms_manage.html`, `room_edit.html`, `pins.html`
- Modify: `server/wcms/urls.py`, `server/web/templates/base.html`, `server/web/static/web/app.css`
- Test: `server/tests/test_labs_views.py`

**Interfaces:**
- Consumes: `Room`, `PC`, `RegistrationPin.issue`, `RegistrationPin.is_usable`, `admin_required`
- Produces:
  - URL `labs:rooms_manage` `/rooms/manage/`, `labs:room_edit` `/rooms/<room_id>/edit/`, `labs:room_delete` `/rooms/<room_id>/delete/` (POST), `labs:pins` `/pins/`, `labs:pin_revoke` `/pins/<pin_id>/revoke/` (POST)
  - 자리 배치 폼 필드 이름: `seat-<row>-<col>` (0부터), 값은 PC id 또는 빈 문자열
  - `labs.forms.RoomForm`, `labs.forms.PinForm(multi_use: bool, minutes: 10 | 60 | 180)`

- [ ] **Step 1: 실패하는 테스트 작성**

`server/tests/test_labs_views.py`:

```python
import pytest
from django.contrib.auth import get_user_model

from labs.models import PC, RegistrationPin, Room

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client(client):
    user = get_user_model().objects.create_user("admin", password="pw-123456", is_staff=True)
    client.force_login(user)
    return client


def make_pc(n: int) -> PC:
    pc, _ = PC.register(hostname=f"LAB-{n:02d}", machine_guid=f"g{n}", specs={}, version="2026.1")
    return pc


def room_fields(**override) -> dict:
    data = {"name": "301", "rows": "5", "cols": "8", "aisle_after": "4", "sort_order": "0"}
    data.update(override)
    return data


@pytest.mark.parametrize("url", ["/rooms/manage/", "/pins/"])
def test_anonymous_redirected_to_login(client, url):
    response = client.get(url)
    assert response.status_code == 302
    assert response.url.startswith("/login/")


def test_create_room(admin_client):
    response = admin_client.post("/rooms/manage/", room_fields())
    room = Room.objects.get(name="301")
    assert response.url == f"/rooms/{room.id}/edit/"
    assert (room.rows, room.cols, room.aisle_after) == (5, 8, 4)


def test_aisle_must_be_inside_room(admin_client):
    response = admin_client.post("/rooms/manage/", room_fields(aisle_after="8"))
    assert response.status_code == 200
    assert not Room.objects.exists()


def test_assign_seats(admin_client):
    room = Room.objects.create(name="301", rows=2, cols=4)
    a, b = make_pc(1), make_pc(2)
    data = room_fields(rows="2", cols="4", aisle_after="")
    data.update({"seat-0-0": str(a.id), "seat-1-3": str(b.id)})
    response = admin_client.post(f"/rooms/{room.id}/edit/", data)
    assert response.status_code == 302
    a.refresh_from_db()
    b.refresh_from_db()
    assert (a.room, a.row, a.col) == (room, 0, 0)
    assert (b.room, b.row, b.col) == (room, 1, 3)


def test_same_pc_twice_rejected(admin_client):
    room = Room.objects.create(name="301", rows=2, cols=4)
    a = make_pc(1)
    data = room_fields(rows="2", cols="4", aisle_after="")
    data.update({"seat-0-0": str(a.id), "seat-0-1": str(a.id)})
    response = admin_client.post(f"/rooms/{room.id}/edit/", data)
    assert response.status_code == 200
    assert "두 자리" in response.content.decode()
    a.refresh_from_db()
    assert a.room is None


def test_shrinking_room_unassigns_out_of_range_pc(admin_client):
    room = Room.objects.create(name="301", rows=2, cols=4)
    a = make_pc(1)
    a.room, a.row, a.col = room, 0, 3
    a.save()
    data = room_fields(rows="2", cols="3", aisle_after="")
    data["seat-0-3"] = str(a.id)
    admin_client.post(f"/rooms/{room.id}/edit/", data)
    a.refresh_from_db()
    assert a.room is None


def test_delete_room_unassigns_pcs(admin_client):
    room = Room.objects.create(name="301", rows=2, cols=4)
    a = make_pc(1)
    a.room, a.row, a.col = room, 0, 0
    a.save()
    response = admin_client.post(f"/rooms/{room.id}/delete/")
    assert response.url == "/rooms/manage/"
    a.refresh_from_db()
    assert (a.room, a.row, a.col) == (None, None, None)
    assert not Room.objects.exists()


def test_issue_pin(admin_client):
    response = admin_client.post("/pins/", {"minutes": "60", "multi_use": "on"})
    pin = RegistrationPin.objects.get()
    assert pin.multi_use is True
    assert pin.pin in response.content.decode()


def test_revoke_pin(admin_client):
    pin = RegistrationPin.issue(user=None, multi_use=True, minutes=10)
    admin_client.post(f"/pins/{pin.id}/revoke/")
    pin.refresh_from_db()
    assert pin.revoked is True
    assert pin.pin not in admin_client.get("/pins/").content.decode()
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `uv run pytest tests/test_labs_views.py -v`
Expected: FAIL, 404

- [ ] **Step 3: 폼 구현**

`server/labs/forms.py`:

```python
from django import forms

from labs.models import Room

MAX_SIDE = 20


class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = ["name", "rows", "cols", "aisle_after", "sort_order"]
        labels = {
            "name": "이름",
            "rows": "줄 수",
            "cols": "열 수",
            "aisle_after": "통로 위치 (N번째 열 뒤, 비우면 없음)",
            "sort_order": "정렬 순서",
        }

    def clean(self) -> dict:
        data = super().clean()
        rows, cols, aisle = data.get("rows"), data.get("cols"), data.get("aisle_after")
        if rows is not None and not 1 <= rows <= MAX_SIDE:
            self.add_error("rows", f"1~{MAX_SIDE} 사이로 입력하세요.")
        if cols is not None and not 1 <= cols <= MAX_SIDE:
            self.add_error("cols", f"1~{MAX_SIDE} 사이로 입력하세요.")
        if aisle is not None and cols is not None and not 1 <= aisle < cols:
            self.add_error("aisle_after", "1 이상, 열 수보다 작게 입력하세요.")
        return data


class PinForm(forms.Form):
    multi_use = forms.BooleanField(required=False, label="여러 대에 사용")
    minutes = forms.TypedChoiceField(
        choices=[(10, "10분"), (60, "1시간"), (180, "3시간")],
        coerce=int,
        initial=10,
        label="유효 시간",
    )
```

- [ ] **Step 4: 뷰와 URL 구현**

`server/labs/views.py`:

```python
from django.db import transaction
from django.http import HttpRequest, HttpResponse, QueryDict
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.permissions import admin_required
from labs.forms import PinForm, RoomForm
from labs.models import PC, RegistrationPin, Room

Seat = tuple[int, int]


def _parse_seats(post: QueryDict, rows: int, cols: int) -> tuple[dict[Seat, int], str]:
    assignments: dict[Seat, int] = {}
    seen: set[int] = set()
    for row in range(rows):
        for col in range(cols):
            raw = post.get(f"seat-{row}-{col}", "")
            if not raw:
                continue
            if not raw.isdigit():
                return {}, "잘못된 PC 선택입니다."
            pc_id = int(raw)
            if pc_id in seen:
                return {}, "같은 PC를 두 자리에 배치할 수 없습니다."
            seen.add(pc_id)
            assignments[(row, col)] = pc_id
    if seen and PC.objects.filter(pk__in=seen).count() != len(seen):
        return {}, "존재하지 않는 PC입니다."
    return assignments, ""


def _seat_rows(rows: int, cols: int, current: dict[Seat, int]) -> list[list[dict]]:
    return [
        [
            {
                "name": f"seat-{row}-{col}",
                "number": row * cols + col + 1,
                "current": current.get((row, col)),
            }
            for col in range(cols)
        ]
        for row in range(rows)
    ]


@admin_required
def rooms_manage(request: HttpRequest) -> HttpResponse:
    form = RoomForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        room = form.save()
        return redirect("labs:room_edit", room_id=room.id)
    return render(
        request, "labs/rooms_manage.html", {"nav": "manage", "rooms": Room.objects.all(), "form": form}
    )


@admin_required
def room_edit(request: HttpRequest, room_id: int) -> HttpResponse:
    room = get_object_or_404(Room, pk=room_id)
    form = RoomForm(request.POST or None, instance=room)
    seat_error = ""
    current = {(pc.row, pc.col): pc.id for pc in room.pcs.all()}
    rows, cols = room.rows, room.cols

    if request.method == "POST" and form.is_valid():
        rows, cols = form.cleaned_data["rows"], form.cleaned_data["cols"]
        assignments, seat_error = _parse_seats(request.POST, rows, cols)
        if not seat_error:
            with transaction.atomic():
                room = form.save()
                PC.objects.filter(room=room).update(room=None, row=None, col=None)
                for (row, col), pc_id in assignments.items():
                    PC.objects.filter(pk=pc_id).update(room=room, row=row, col=col)
            return redirect("labs:room_edit", room_id=room.id)
        current = {}
        for row in range(rows):
            for col in range(cols):
                value = request.POST.get(f"seat-{row}-{col}", "")
                if value.isdigit():
                    current[(row, col)] = int(value)

    pcs = PC.objects.select_related("room").order_by("hostname")
    context = {
        "nav": "manage",
        "room": room,
        "form": form,
        "seat_error": seat_error,
        "seat_rows": _seat_rows(rows, cols, current),
        "pc_choices": [{"id": pc.id, "text": f"{pc.hostname} ({pc.label})"} for pc in pcs],
    }
    return render(request, "labs/room_edit.html", context)


@admin_required
@require_POST
def room_delete(request: HttpRequest, room_id: int) -> HttpResponse:
    room = get_object_or_404(Room, pk=room_id)
    with transaction.atomic():
        PC.objects.filter(room=room).update(room=None, row=None, col=None)
        room.delete()
    return redirect("labs:rooms_manage")


@admin_required
def pins(request: HttpRequest) -> HttpResponse:
    form = PinForm(request.POST or None)
    new_pin = None
    if request.method == "POST" and form.is_valid():
        new_pin = RegistrationPin.issue(
            user=request.user,
            multi_use=form.cleaned_data["multi_use"],
            minutes=form.cleaned_data["minutes"],
        )
        form = PinForm()
    now = timezone.now()
    active = [
        pin
        for pin in RegistrationPin.objects.filter(revoked=False, expires_at__gt=now).order_by("-created_at")
        if pin.is_usable(now)
    ]
    return render(
        request, "labs/pins.html", {"nav": "pins", "form": form, "new_pin": new_pin, "pins": active}
    )


@admin_required
@require_POST
def pin_revoke(request: HttpRequest, pin_id: int) -> HttpResponse:
    RegistrationPin.objects.filter(pk=pin_id).update(revoked=True)
    return redirect("labs:pins")
```

`server/labs/urls.py`:

```python
from django.urls import path

from labs import views

app_name = "labs"

urlpatterns = [
    path("rooms/manage/", views.rooms_manage, name="rooms_manage"),
    path("rooms/<int:room_id>/edit/", views.room_edit, name="room_edit"),
    path("rooms/<int:room_id>/delete/", views.room_delete, name="room_delete"),
    path("pins/", views.pins, name="pins"),
    path("pins/<int:pin_id>/revoke/", views.pin_revoke, name="pin_revoke"),
]
```

`server/wcms/urls.py` 전체:

```python
from django.urls import include, path

from wcms.views import healthz

urlpatterns = [
    path("healthz", healthz),
    path("client/", include("clientapi.urls")),
    path("", include("accounts.urls")),
    path("", include("labs.urls")),
    path("", include("web.urls")),
]
```

`labs.urls`를 `web.urls`보다 앞에 둔다. `/rooms/manage/`가 `/rooms/<int:room_id>/`와 겹치지는 않지만 관리 경로를 먼저 찾게 한다.

- [ ] **Step 5: 템플릿 작성**

`server/labs/templates/labs/rooms_manage.html`:

```html
{% extends "base.html" %}
{% block title %}실습실 관리 · WCMS{% endblock %}
{% block content %}
<header class="page-head"><h1>실습실 관리</h1></header>
<section class="card">
<h2>실습실</h2>
{% if rooms %}
<table class="table">
<thead><tr><th scope="col">이름</th><th scope="col">크기</th><th scope="col">PC</th><th scope="col"><span class="sr">편집</span></th></tr></thead>
<tbody>
{% for room in rooms %}
<tr><td>{{ room.name }}</td><td>{{ room.rows }} × {{ room.cols }}</td><td>{{ room.pcs.count }}</td><td><a href="{% url 'labs:room_edit' room.id %}">자리 배치</a></td></tr>
{% endfor %}
</tbody>
</table>
{% else %}
<p class="meta">아직 없습니다.</p>
{% endif %}
</section>
<section class="card narrow">
<h2>실습실 추가</h2>
<form method="post" class="stack">
{% csrf_token %}
{{ form.non_field_errors }}
{% for field in form %}
<label for="{{ field.id_for_label }}">{{ field.label }}</label>
{{ field }}
{% for error in field.errors %}<p class="error">{{ error }}</p>{% endfor %}
{% endfor %}
<button type="submit" class="btn pri">추가</button>
</form>
</section>
{% endblock %}
```

`server/labs/templates/labs/room_edit.html`:

```html
{% extends "base.html" %}
{% block title %}{{ room.name }} 자리 배치 · WCMS{% endblock %}
{% block content %}
<header class="page-head">
<div><h1>{{ room.name }} 자리 배치</h1><p class="meta"><a href="{% url 'labs:rooms_manage' %}">실습실 관리</a></p></div>
<form method="post" action="{% url 'labs:room_delete' room.id %}">{% csrf_token %}<button type="submit" class="btn dng">실습실 삭제</button></form>
</header>
<form method="post" class="stack">
{% csrf_token %}
<section class="card">
<h2>크기</h2>
<div class="form-row">
{% for field in form %}
<div class="stack">
<label for="{{ field.id_for_label }}">{{ field.label }}</label>
{{ field }}
{% for error in field.errors %}<p class="error">{{ error }}</p>{% endfor %}
</div>
{% endfor %}
</div>
</section>
<section class="card">
<h2>자리</h2>
{% if seat_error %}<p class="error" role="alert">{{ seat_error }}</p>{% endif %}
<div class="seat-scroll">
{% for row in seat_rows %}
<div class="seat-edit-row">
{% for seat in row %}
<div class="seat-edit">
<label for="{{ seat.name }}">{{ seat.number }}</label>
<select id="{{ seat.name }}" name="{{ seat.name }}">
<option value="">비움</option>
{% for pc in pc_choices %}<option value="{{ pc.id }}"{% if pc.id == seat.current %} selected{% endif %}>{{ pc.text }}</option>{% endfor %}
</select>
</div>
{% endfor %}
</div>
{% endfor %}
</div>
</section>
<div><button type="submit" class="btn pri">저장</button></div>
</form>
{% endblock %}
```

`server/labs/templates/labs/pins.html`:

```html
{% extends "base.html" %}
{% block title %}등록 PIN · WCMS{% endblock %}
{% block content %}
<header class="page-head"><h1>등록 PIN</h1></header>
{% if new_pin %}
<p class="notice" role="status">새 PIN: <strong class="mono">{{ new_pin.pin }}</strong> ({{ new_pin.expires_at|date:"H:i" }}까지{% if new_pin.multi_use %}, 여러 대 사용 가능{% endif %})</p>
{% endif %}
<section class="card narrow">
<h2>PIN 만들기</h2>
<form method="post" class="stack">
{% csrf_token %}
<label for="{{ form.minutes.id_for_label }}">{{ form.minutes.label }}</label>
{{ form.minutes }}
<label>{{ form.multi_use }} {{ form.multi_use.label }}</label>
<button type="submit" class="btn pri">만들기</button>
</form>
</section>
<section class="card">
<h2>사용 가능한 PIN</h2>
{% if pins %}
<table class="table">
<thead><tr><th scope="col">PIN</th><th scope="col">만료</th><th scope="col">방식</th><th scope="col">사용</th><th scope="col"><span class="sr">폐기</span></th></tr></thead>
<tbody>
{% for pin in pins %}
<tr>
<td class="mono">{{ pin.pin }}</td>
<td>{{ pin.expires_at|date:"H:i" }}</td>
<td>{% if pin.multi_use %}여러 대{% else %}1회{% endif %}</td>
<td>{{ pin.used_count }}</td>
<td><form method="post" action="{% url 'labs:pin_revoke' pin.id %}">{% csrf_token %}<button type="submit" class="btn sm dng">폐기</button></form></td>
</tr>
{% endfor %}
</tbody>
</table>
{% else %}
<p class="meta">없습니다.</p>
{% endif %}
</section>
{% endblock %}
```

- [ ] **Step 6: 메뉴와 CSS 추가**

`server/web/templates/base.html`에서

```html
<a class="nav{% if nav == 'rooms' %} on{% endif %}" href="{% url 'web:home' %}">실습실</a>
</div>
```

를 아래로 바꾼다.

```html
<a class="nav{% if nav == 'rooms' %} on{% endif %}" href="{% url 'web:home' %}">실습실</a>
{% if user.is_authenticated and user.is_staff %}
<a class="nav{% if nav == 'manage' %} on{% endif %}" href="{% url 'labs:rooms_manage' %}">실습실 관리</a>
<a class="nav{% if nav == 'pins' %} on{% endif %}" href="{% url 'labs:pins' %}">등록 PIN</a>
{% endif %}
</div>
```

`server/web/static/web/app.css` 끝에 추가:

```css
.form-row { display: flex; flex-wrap: wrap; gap: 16px; }
.form-row > .stack { flex: 1 1 160px; }
.seat-edit-row { display: flex; gap: 8px; margin-bottom: 8px; min-width: 960px; }
.seat-edit { flex: 1 1 0; display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.seat-edit label { font-size: 12px; color: var(--muted); }
.seat-edit select { width: 100%; }
```

- [ ] **Step 7: 테스트 통과 확인**

Run: `uv run pytest tests/test_labs_views.py -v`
Expected: 10 passed

- [ ] **Step 8: 전체 테스트**

Run: `uv run pytest`
Expected: 모두 통과

- [ ] **Step 9: Commit**

```bash
git add server/labs server/web server/wcms/urls.py server/tests/test_labs_views.py
git commit -m "feat(server): room seat management and registration PIN pages"
```

---

### Task 9: 개발용 가짜 클라이언트 + 실행 확인

C++ 클라이언트(계획 3)가 나오기 전에 서버 화면을 실제로 돌려 보기 위한 도구다.

**Files:**
- Create: `server/tools/fake_client.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: `POST /client/register`, `/client/ws` 프로토콜 (`docs/protocol.md`)
- Produces: `uv run python tools/fake_client.py --server <url> [--pin <PIN>] [--count N]`. 발급받은 토큰은 `server/tools/.fake_clients.json`에 저장해서 다음 실행에 재사용한다

- [ ] **Step 1: 가짜 클라이언트 작성**

`server/tools/fake_client.py`:

```python
"""개발용 가짜 클라이언트. C++ 클라이언트 없이 서버 화면을 확인할 때 쓴다.

uv run python tools/fake_client.py --server http://localhost:8000 --pin 123456 --count 8
"""

import argparse
import asyncio
import json
import random
import urllib.request
from pathlib import Path

import websockets

STATE_FILE = Path(__file__).with_name(".fake_clients.json")
APPS = [
    ("chrome.exe", "자료구조 3주차 - Google Docs - Chrome"),
    ("chrome.exe", "YouTube - Chrome"),
    ("Code.exe", "main.cpp - Visual Studio Code"),
    ("explorer.exe", "파일 탐색기"),
]


def register(server: str, pin: str, index: int) -> str:
    body = json.dumps(
        {
            "pin": pin,
            "hostname": f"FAKE-{index:02d}",
            "machine_guid": f"fake-{index}",
            "specs": {"cpu": "Fake CPU", "ram_gb": 16},
            "version": "2026.1",
        }
    ).encode()
    request = urllib.request.Request(
        f"{server}/client/register",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request) as response:
        return json.load(response)["token"]


def fake_status() -> dict:
    session = random.choices(["active", "locked", "none"], weights=[8, 1, 1])[0]
    process, title = random.choice(APPS)
    return {
        "type": "status",
        "cpu": round(random.uniform(1, 60), 1),
        "mem_used": random.randint(4, 12) * 1024**3,
        "mem_total": 16 * 1024**3,
        "disk_used": 246 * 1000**3,
        "disk_total": 512 * 1000**3,
        "user": "Student" if session != "none" else "",
        "session": session,
        "foreground": {"process": process, "title": title} if session == "active" else None,
    }


async def run_one(ws_url: str, token: str) -> None:
    headers = {"Authorization": f"Bearer {token}"}
    async for ws in websockets.connect(ws_url, additional_headers=headers):
        try:
            await ws.send(json.dumps({"type": "hello", "version": "2026.1"}))
            while True:
                await ws.send(json.dumps(fake_status()))
                await asyncio.sleep(10)
        except websockets.ConnectionClosed:
            continue


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", default="http://localhost:8000")
    parser.add_argument("--pin")
    parser.add_argument("--count", type=int, default=8)
    args = parser.parse_args()

    tokens: dict[str, str] = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}
    for index in range(1, args.count + 1):
        if str(index) not in tokens:
            if not args.pin:
                parser.error(f"FAKE-{index:02d}의 토큰이 없습니다. --pin을 주세요.")
            tokens[str(index)] = register(args.server, args.pin, index)
    STATE_FILE.write_text(json.dumps(tokens))

    ws_url = args.server.replace("http", "ws", 1) + "/client/ws"
    await asyncio.gather(*(run_one(ws_url, tokens[str(i)]) for i in range(1, args.count + 1)))


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: 서버를 띄우고 관리자 만들기**

```bash
cd server
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

Expected: `Starting ASGI/Daphne ... development server at http://127.0.0.1:8000/`

- [ ] **Step 3: 화면에서 확인 (수동)**

1. `http://localhost:8000/login/` 로그인 → QR을 인증 앱으로 찍고 코드 입력 → 로그인됨
2. 실습실 관리에서 `301`(5줄 × 8열, 통로 4) 추가
3. 등록 PIN에서 "여러 대에 사용", 10분으로 PIN 생성

- [ ] **Step 4: 가짜 클라이언트 실행 (다른 터미널)**

```bash
cd server
uv run python tools/fake_client.py --pin <3번에서 만든 PIN> --count 8
```

확인할 것:
1. 실습실 `301` 화면 아래 "자리 미배정 PC"에 `FAKE-01`~`FAKE-08`이 보인다
2. 자리 배치에서 8대를 배치하고 저장 → 실습실 화면에 타일이 나온다
3. 10초마다 타일의 사용자, 앞 창, 상태 글자가 새로고침 없이 바뀐다
4. 가짜 클라이언트를 Ctrl+C로 끄면 타일이 바로 "오프라인"이 된다
5. 시크릿 창(비로그인)으로 같은 화면을 열면 상태만 보이고 사용자, 앞 창, 호스트 이름은 안 보인다

- [ ] **Step 5: README에 실행법 추가**

`README.md` 끝에 추가:

````markdown

## 서버 실행 (개발)

```bash
cd server
uv sync
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

가짜 클라이언트: `uv run python tools/fake_client.py --pin <PIN> --count 8`

## 테스트

```bash
cd server
uv run pytest
```
````

- [ ] **Step 6: Commit**

```bash
git add server/tools/fake_client.py README.md
git commit -m "feat(server): fake client for local development"
```
