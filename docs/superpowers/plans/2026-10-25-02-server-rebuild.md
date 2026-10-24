# WCMS 2026.1 계획 02: 서버 새로 만들기 (DRF + Channels) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 계획 1의 서버 코드를 버리고, 설계 문서의 웹 구조(DRF JSON API + Channels, 단일 ASGI 프로세스, Redis 상태)대로 서버를 새로 만든다. 범위: 관리자 인증(비밀번호 + TOTP, 1회용 등록 링크), 관리자 계정 관리, 실습실·좌석·PC·등록 PIN, 클라이언트 등록과 WebSocket, 브라우저 실시간 구독, 감사 로그, OpenAPI 스키마, 클라이언트 프로토콜 문서.

**Architecture:** `server/`에 Django 5.2 프로젝트 `wcms`와 앱 `audit`, `accounts`, `labs`, `agent`, `live`. 화면은 없고 JSON API(`/api/*`)와 WebSocket(`/ws/live`, `/client/ws`)만 제공한다. 실시간 PC 상태와 세션, 실패 카운터는 Django 캐시(운영은 Redis)에 두고 SQLite에는 설정과 기록만 쓴다. 프론트엔드(계획 03)는 이 서버가 만든 `server/openapi.yaml`에서 타입을 생성한다.

**Tech Stack:** Python 3.13, uv, Django 5.2, djangorestframework, drf-spectacular, channels 4, channels-redis, uvicorn[standard], redis, pyotp, segno, pytest + pytest-django + pytest-asyncio, websockets(개발용 가짜 클라이언트)

**설계 문서:** `docs/superpowers/specs/2026-10-24-wcms-2026-1-design.md` (2장 "웹 구조", 3장, 4장, 6장)

**작업 브랜치:** `dev`에서 `feat/server-base`를 만들어 작업하고, 끝나면 `dev`로 합친다.

## 전체 계획 순서 (갱신)

| 순서 | 계획 | 결과물 |
|---|---|---|
| 01 | 저장소 정리 + 서버 기반 | 완료. 구조가 바뀌어 서버 코드는 02에서 새로 만든다 |
| 02 | 서버 새로 만들기 (이 문서) | DRF API, 인증, 실습실 관리, 클라이언트 등록·연결, 실시간 구독 |
| 03 | 프론트엔드 기반 | SvelteKit SPA: 로그인, 등록 링크, 실습실 그리드, 설정 화면 |
| 04 | 원격 명령 | 서버 + 화면 |
| 05 | C++ 클라이언트 기반 | |
| 06 | 화면 (썸네일, 크게 보기, 스크린샷) | |
| 07 | 정책 | |
| 08 | 프로그램 | |
| 09 | 예약 작업 + 배포 | |

## Global Constraints

- 계획 1의 `server/` 코드는 재사용하지 않는다. Task 1에서 전부 지우고 새로 만든다.
- Python 3.13, 패키지 관리는 uv만 (`uv add`, `uv sync`, `uv run`). `pip` 직접 사용 금지. 명령은 모두 `server/`에서 실행한다.
- URL은 끝 슬래시 없음 (`/api/rooms`, `/api/rooms/3`). `APPEND_SLASH = False`.
- 오류 응답 형식은 하나: `{"error": "<code>", "detail": "<사람이 읽을 문장>", "fields": {...}}` (`fields`는 입력 오류일 때만). 클라이언트 등록 API도 같은 형식.
- 미인증 API 요청은 401, 권한 없음은 403.
- 시각은 UTC (`TIME_ZONE = "UTC"`), ISO 8601로 주고받는다.
- 비로그인 사용자에게는 좌석 라벨과 켜짐/꺼짐만 준다. 호스트 이름, 사용자, 프로세스, 창 제목, IP, 사양은 비로그인 응답과 비로그인 WebSocket 메시지 어디에도 나오면 안 된다.
- 학생이 조작할 수 있는 값(호스트 이름, 사용자 이름, 창 제목, 프로세스 이름, specs)은 길이·타입을 검증하고 그대로 신뢰하지 않는다.
- 실시간 PC 상태(10초마다 오는 status)는 DB에 쓰지 않는다. `agent.state`(Django 캐시)에만 둔다.
- 채널 그룹 이름은 `wcms/groups.py` 함수로만 만든다.
- 커밋 메시지에 작성자 표기(Co-Authored-By 등)를 넣지 않는다.

---

## 파일 구조

```
protocol/
  README.md                     클라이언트-서버 프로토콜 v1 (C++ 클라이언트 기준 문서)
  examples/*.json               메시지 예시. 서버 테스트와 C++ 테스트가 같이 읽는다
server/
  pyproject.toml, uv.lock, .python-version, manage.py, openapi.yaml
  wcms/
    settings.py, urls.py, api_urls.py, asgi.py, routing.py, views.py(healthz)
    api.py        SessionAuth, IsAdmin, is_admin, ApiError, 오류 형식, SafeJSONParser, csrf_failure, api_not_found, ErrorSerializer
    net.py        client_ip, scope_client_ip, header, is_internal_request, is_internal_scope
    limits.py     FailureLimiter
    groups.py     채널 그룹 이름
    middleware.py InternalOnlyMiddleware
  audit/      models.py(AuditLog), services.py(record), serializers.py, views.py, urls.py
  accounts/   totp.py, models.py(TOTPDevice, EnrollmentToken), serializers.py, views.py, urls.py,
              management/commands/createadmin.py
  labs/       models.py(Room, PC, RegistrationPin), serializers.py, views.py, urls.py
  agent/      protocol.py, state.py, views.py(register), consumers.py(AgentConsumer), urls.py
  live/       serializers.py, snapshots.py, publish.py, views.py, consumers.py(LiveConsumer), urls.py
  tests/      conftest.py, test_*.py
  tools/fake_client.py
```

---

### Task 1: 새 프로젝트 골격

**Files:**
- Delete: `server/` 전체 (계획 1 코드)
- Create: `server/pyproject.toml`, `server/manage.py`, `server/wcms/__init__.py`, `server/wcms/settings.py`, `server/wcms/urls.py`, `server/wcms/api_urls.py`, `server/wcms/asgi.py`, `server/wcms/routing.py`, `server/wcms/views.py`, `server/wcms/api.py`
- Create: 앱 골격 `server/{audit,accounts,labs,agent,live}/__init__.py`, `apps.py`, `urls.py`, `migrations/__init__.py`
- Test: `server/tests/__init__.py`, `server/tests/conftest.py`, `server/tests/test_project.py`

**Interfaces:**
- Produces:
  - `wcms.api.SessionAuth`, `wcms.api.IsAdmin`, `wcms.api.is_admin(user) -> bool`
  - `wcms.api.ApiError(code: str, detail: str, status_code: int = 400)`
  - `wcms.api.error_body(code: str, detail: str, fields: dict | None = None) -> dict`
  - `wcms.api.ErrorSerializer`, `wcms.api.error_responses(*statuses: int) -> dict` (drf-spectacular `responses`에 펼쳐 넣는 용도)
  - `wcms.api.SafeJSONParser`, `wcms.api.csrf_failure`, `wcms.api.api_not_found`
  - 설정: `WCMS_VERSION`, `WCMS_TRUST_X_REAL_IP: bool`, `WCMS_REQUIRE_INTERNAL: bool`, `WCMS_ENROLL_HOURS = 24`, `WCMS_PENDING_LOGIN_SECONDS = 300`
  - 각 앱 `urls.py`는 `urlpatterns = []`로 시작하고, 이후 Task가 채운다. `wcms/api_urls.py`가 `audit`, `accounts`, `labs`, `live`의 urls를 `/api/` 아래에 모은다. `agent.urls`는 `/client/` 아래.
  - 테스트 픽스처(`tests/conftest.py`): `api`(미인증 `APIClient`), `admin_user`, `admin_api`(admin_user로 `force_login`한 `APIClient`), 캐시 자동 초기화

- [ ] **Step 1: 계획 1 서버 삭제**

```bash
git rm -r -q server
rm -rf server
```

- [ ] **Step 2: pyproject.toml 작성과 의존성 설치**

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

```bash
cd server
uv python pin 3.13
uv add "django>=5.2,<5.3" "djangorestframework>=3.16" "drf-spectacular>=0.28" "channels>=4.2" "channels-redis>=4.2" "uvicorn[standard]>=0.34" "redis>=5" "pyotp>=2.9" "segno>=1.6"
uv add --dev "pytest>=8" "pytest-django>=4.9" "pytest-asyncio>=0.24" "websockets>=14"
```

- [ ] **Step 3: manage.py와 앱 골격**

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

다섯 앱(`audit`, `accounts`, `labs`, `agent`, `live`) 각각에 빈 `__init__.py`, 빈 `migrations/__init__.py`, 아래 형태의 `apps.py`와 `urls.py`를 만든다. 클래스 이름은 `AuditConfig`, `AccountsConfig`, `LabsConfig`, `AgentConfig`, `LiveConfig`.

`server/audit/apps.py`:

```python
from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "audit"
```

`server/audit/urls.py` (다섯 앱 모두 같은 내용으로 시작):

```python
urlpatterns: list = []
```

`server/wcms/__init__.py`, `server/tests/__init__.py`는 빈 파일.

- [ ] **Step 4: settings.py**

`server/wcms/settings.py`:

```python
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BASE_DIR.parent
DEV_SECRET_KEY = "dev-only-insecure-key"


def env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


def env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    return default if value is None else value == "1"


def read_version() -> str:
    path = REPO_DIR / "VERSION"
    return path.read_text(encoding="utf-8").strip() if path.exists() else "dev"


DEBUG = env_bool("WCMS_DEBUG", True)
SECRET_KEY = os.environ.get("WCMS_SECRET_KEY", DEV_SECRET_KEY)
if not DEBUG and SECRET_KEY == DEV_SECRET_KEY:
    raise ImproperlyConfigured("WCMS_DEBUG=0이면 WCMS_SECRET_KEY를 반드시 설정해야 합니다.")

ALLOWED_HOSTS = env_list("WCMS_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("WCMS_CSRF_TRUSTED_ORIGINS", "http://localhost:5173")

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "rest_framework",
    "drf_spectacular",
    "channels",
    "audit",
    "accounts",
    "labs",
    "agent",
    "live",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "wcms.urls"
APPEND_SLASH = False
ASGI_APPLICATION = "wcms.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": []},
    }
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("WCMS_DB_PATH", str(BASE_DIR / "db.sqlite3")),
        "OPTIONS": {
            "init_command": "PRAGMA journal_mode=WAL;",
            "transaction_mode": "IMMEDIATE",
            "timeout": 20,
        },
    }
}

REDIS_URL = os.environ.get("WCMS_REDIS_URL", "")
if REDIS_URL:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.redis.RedisCache", "LOCATION": REDIS_URL}}
    CHANNEL_LAYERS = {
        "default": {"BACKEND": "channels_redis.core.RedisChannelLayer", "CONFIG": {"hosts": [REDIS_URL]}}
    }
else:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
    CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}

SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_COOKIE_AGE = 12 * 3600
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
CSRF_FAILURE_VIEW = "wcms.api.csrf_failure"
if env_bool("WCMS_BEHIND_TLS_PROXY", False):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["wcms.api.SessionAuth"],
    "DEFAULT_PERMISSION_CLASSES": ["wcms.api.IsAdmin"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["wcms.api.SafeJSONParser"],
    "EXCEPTION_HANDLER": "wcms.api.exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

LANGUAGE_CODE = "ko-kr"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

WCMS_VERSION = read_version()
WCMS_TRUST_X_REAL_IP = env_bool("WCMS_TRUST_X_REAL_IP", False)
WCMS_REQUIRE_INTERNAL = env_bool("WCMS_REQUIRE_INTERNAL", False)
WCMS_ENROLL_HOURS = 24
WCMS_PENDING_LOGIN_SECONDS = 300

SPECTACULAR_SETTINGS = {
    "TITLE": "WCMS API",
    "VERSION": WCMS_VERSION,
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
}
```

- [ ] **Step 5: wcms/api.py**

`server/wcms/api.py`:

```python
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404, HttpRequest, JsonResponse
from rest_framework import exceptions, permissions, serializers
from rest_framework.authentication import SessionAuthentication
from rest_framework.parsers import JSONParser
from rest_framework.views import exception_handler as drf_exception_handler


class SessionAuth(SessionAuthentication):
    """세션 인증. 미인증 요청이 403이 아니라 401을 받도록 인증 헤더 값을 돌려준다."""

    def authenticate_header(self, request) -> str:
        return "Session"


def is_admin(user) -> bool:
    return bool(user is not None and user.is_authenticated and user.is_active and user.is_staff)


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view) -> bool:
        return is_admin(request.user)


class ApiError(exceptions.APIException):
    """오류 코드와 상태를 직접 지정하는 API 오류."""

    def __init__(self, code: str, detail: str, status_code: int = 400):
        self.status_code = status_code
        super().__init__(detail=detail, code=code)


class SafeJSONParser(JSONParser):
    """너무 깊게 중첩된 JSON이 500이 아니라 400이 되게 한다."""

    def parse(self, stream, media_type=None, parser_context=None):
        try:
            return super().parse(stream, media_type, parser_context)
        except RecursionError:
            raise exceptions.ParseError("JSON이 너무 깊게 중첩되어 있습니다.")


class ErrorSerializer(serializers.Serializer):
    error = serializers.CharField()
    detail = serializers.CharField()
    fields = serializers.DictField(required=False)


def error_responses(*statuses: int) -> dict:
    return {status: ErrorSerializer for status in statuses}


def error_body(code: str, detail: str, fields: dict | None = None) -> dict:
    body: dict = {"error": code, "detail": detail}
    if fields:
        body["fields"] = fields
    return body


def exception_handler(exc, context):
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, DjangoPermissionDenied):
        exc = exceptions.PermissionDenied()
    response = drf_exception_handler(exc, context)
    if response is None:
        return None
    if isinstance(exc, exceptions.ValidationError):
        data = response.data
        fields = data if isinstance(data, dict) else {"non_field_errors": data}
        response.data = error_body("invalid", "입력값을 확인하세요.", fields)
        return response
    codes = exc.get_codes() if hasattr(exc, "get_codes") else "error"
    code = codes if isinstance(codes, str) else "error"
    detail = response.data.get("detail", "") if isinstance(response.data, dict) else ""
    response.data = error_body(code, str(detail))
    return response


def csrf_failure(request: HttpRequest, reason: str = "") -> JsonResponse:
    return JsonResponse(error_body("csrf_failed", "보안 토큰이 없거나 맞지 않습니다. 새로고침 후 다시 시도하세요."), status=403)


def api_not_found(request: HttpRequest, *args, **kwargs) -> JsonResponse:
    return JsonResponse(error_body("not_found", "없는 API입니다."), status=404)
```

- [ ] **Step 6: urls, views, routing, asgi**

`server/wcms/views.py`:

```python
from django.http import HttpRequest, HttpResponse


def healthz(request: HttpRequest) -> HttpResponse:
    return HttpResponse("ok", content_type="text/plain")
```

`server/wcms/api_urls.py`:

```python
from django.urls import include, path

urlpatterns = [
    path("", include("accounts.urls")),
    path("", include("labs.urls")),
    path("", include("live.urls")),
    path("", include("audit.urls")),
]
```

`server/wcms/urls.py`:

```python
from django.urls import include, path, re_path

from wcms.api import api_not_found
from wcms.views import healthz

urlpatterns = [
    path("healthz", healthz),
    path("api/", include("wcms.api_urls")),
    re_path(r"^api/", api_not_found),
    path("client/", include("agent.urls")),
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

- [ ] **Step 7: 테스트 작성**

`server/tests/conftest.py`:

```python
import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

PASSWORD = "correct-horse-battery-9"


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api() -> APIClient:
    return APIClient()


@pytest.fixture
def admin_user(db):
    return get_user_model().objects.create_user("admin", password=PASSWORD, is_staff=True)


@pytest.fixture
def admin_api(admin_user) -> APIClient:
    client = APIClient()
    client.force_login(admin_user)
    return client
```

`server/tests/test_project.py`:

```python
import io
import os
import subprocess
import sys

import pytest
from django.conf import settings
from django.test import RequestFactory
from rest_framework.exceptions import ParseError

from wcms.api import SafeJSONParser, csrf_failure


def test_version_comes_from_version_file():
    assert settings.WCMS_VERSION == "2026.1"


def test_time_zone_is_utc():
    assert settings.TIME_ZONE == "UTC"


def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.content == b"ok"


def test_unknown_api_path_is_json_404(api):
    response = api.get("/api/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"] == "not_found"


def test_csrf_failure_is_json():
    response = csrf_failure(RequestFactory().post("/api/x"), reason="no token")
    assert response.status_code == 403
    assert b'"csrf_failed"' in response.content


def test_safe_json_parser_rejects_deep_nesting():
    stream = io.BytesIO(b"[" * 100_000 + b"]" * 100_000)
    with pytest.raises(ParseError):
        SafeJSONParser().parse(stream)


def test_production_requires_secret_key():
    env = {**os.environ, "WCMS_DEBUG": "0", "DJANGO_SETTINGS_MODULE": "wcms.settings"}
    env.pop("WCMS_SECRET_KEY", None)
    result = subprocess.run(
        [sys.executable, "-c", "import django; django.setup()"],
        env=env,
        cwd=settings.BASE_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "WCMS_SECRET_KEY" in result.stderr
```

- [ ] **Step 8: 테스트와 check 실행**

Run: `uv run pytest -v && uv run python manage.py check`
Expected: 7 passed, `System check identified no issues`

- [ ] **Step 9: Commit**

```bash
git add -A server
git commit -m "feat(server): new DRF + Channels project skeleton"
```

---

### Task 2: 공통 모듈 (접속 IP, 내부 경로 확인, 실패 카운터, 그룹 이름)

**Files:**
- Create: `server/wcms/net.py`, `server/wcms/limits.py`, `server/wcms/groups.py`, `server/wcms/middleware.py`
- Modify: `server/wcms/settings.py` (MIDDLEWARE에 한 줄 추가)
- Test: `server/tests/test_common.py`

**Interfaces:**
- Consumes: `settings.WCMS_TRUST_X_REAL_IP`, `settings.WCMS_REQUIRE_INTERNAL`, `wcms.api.error_body`
- Produces:
  - `wcms.net.client_ip(request) -> str` (`WCMS_TRUST_X_REAL_IP`이면 `X-Real-IP`, 아니면 `REMOTE_ADDR`)
  - `wcms.net.scope_client_ip(scope) -> str`, `wcms.net.header(scope, name: bytes) -> str | None`
  - `wcms.net.is_internal_request(request) -> bool`, `wcms.net.is_internal_scope(scope) -> bool` (`WCMS_REQUIRE_INTERNAL`이 꺼져 있으면 항상 True, 켜져 있으면 `X-WCMS-Via: internal` 헤더 필요)
  - `wcms.limits.FailureLimiter(name: str, limit: int, window: int)` 메서드 `blocked(ident) -> bool`, `record(ident) -> None`, `reset(ident) -> None`
  - `wcms.groups`: `user_group(user_id)`, `pc_group(pc_id)`(클라이언트 연결), `pc_watch_group(pc_id)`(브라우저 구독), `room_group(room_id)`, `room_public_group(room_id)` → `str`
  - `wcms.middleware.InternalOnlyMiddleware`: `/client/`로 시작하는 HTTP 요청이 내부 경로가 아니면 JSON 404

- [ ] **Step 1: 실패하는 테스트 작성**

`server/tests/test_common.py`:

```python
from django.http import HttpResponse
from django.test import RequestFactory, override_settings

from wcms import groups
from wcms.limits import FailureLimiter
from wcms.middleware import InternalOnlyMiddleware
from wcms.net import client_ip, is_internal_scope, scope_client_ip

rf = RequestFactory()


def test_client_ip_ignores_header_unless_trusted():
    request = rf.get("/", REMOTE_ADDR="10.0.0.1", HTTP_X_REAL_IP="1.2.3.4")
    assert client_ip(request) == "10.0.0.1"
    with override_settings(WCMS_TRUST_X_REAL_IP=True):
        assert client_ip(request) == "1.2.3.4"


def test_scope_client_ip():
    scope = {"client": ("10.0.0.9", 5000), "headers": [(b"x-real-ip", b"5.6.7.8")]}
    assert scope_client_ip(scope) == "10.0.0.9"
    with override_settings(WCMS_TRUST_X_REAL_IP=True):
        assert scope_client_ip(scope) == "5.6.7.8"


def test_internal_scope_check():
    plain = {"headers": []}
    marked = {"headers": [(b"x-wcms-via", b"internal")]}
    assert is_internal_scope(plain) is True
    with override_settings(WCMS_REQUIRE_INTERNAL=True):
        assert is_internal_scope(plain) is False
        assert is_internal_scope(marked) is True


def test_internal_only_middleware():
    middleware = InternalOnlyMiddleware(lambda request: HttpResponse("passed"))
    with override_settings(WCMS_REQUIRE_INTERNAL=True):
        blocked = middleware(rf.post("/client/register"))
        assert blocked.status_code == 404
        assert b'"not_found"' in blocked.content
        allowed = middleware(rf.post("/client/register", HTTP_X_WCMS_VIA="internal"))
        assert allowed.content == b"passed"
        other = middleware(rf.get("/api/auth/me"))
        assert other.content == b"passed"


def test_failure_limiter():
    limiter = FailureLimiter("test", limit=3, window=60)
    for _ in range(2):
        limiter.record("a")
    assert limiter.blocked("a") is False
    limiter.record("a")
    assert limiter.blocked("a") is True
    assert limiter.blocked("b") is False
    limiter.reset("a")
    assert limiter.blocked("a") is False


def test_group_names():
    assert groups.user_group(1) == "user-1"
    assert groups.pc_group(2) == "pc-2"
    assert groups.pc_watch_group(2) == "pcwatch-2"
    assert groups.room_group(3) == "room-3"
    assert groups.room_public_group(3) == "room-3-public"
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `uv run pytest tests/test_common.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'wcms.limits'` 등

- [ ] **Step 3: 구현**

`server/wcms/net.py`:

```python
from django.conf import settings
from django.http import HttpRequest

INTERNAL_VALUE = "internal"


def header(scope: dict, name: bytes) -> str | None:
    for key, value in scope.get("headers", []):
        if key == name:
            return value.decode("latin-1")
    return None


def client_ip(request: HttpRequest) -> str:
    if settings.WCMS_TRUST_X_REAL_IP and request.META.get("HTTP_X_REAL_IP"):
        return request.META["HTTP_X_REAL_IP"].strip()
    return request.META.get("REMOTE_ADDR", "")


def scope_client_ip(scope: dict) -> str:
    if settings.WCMS_TRUST_X_REAL_IP:
        value = header(scope, b"x-real-ip")
        if value:
            return value.strip()
    client = scope.get("client")
    return client[0] if client else ""


def is_internal_request(request: HttpRequest) -> bool:
    if not settings.WCMS_REQUIRE_INTERNAL:
        return True
    return request.META.get("HTTP_X_WCMS_VIA") == INTERNAL_VALUE


def is_internal_scope(scope: dict) -> bool:
    if not settings.WCMS_REQUIRE_INTERNAL:
        return True
    return header(scope, b"x-wcms-via") == INTERNAL_VALUE
```

`server/wcms/limits.py`:

```python
from django.core.cache import cache


class FailureLimiter:
    """키별 실패 횟수를 센다. 창은 첫 실패 시점부터 고정되고 실패가 이어져도 늘어나지 않는다."""

    def __init__(self, name: str, limit: int, window: int):
        self.name = name
        self.limit = limit
        self.window = window

    def _key(self, ident: str) -> str:
        return f"fail:{self.name}:{ident}"

    def blocked(self, ident: str) -> bool:
        return cache.get(self._key(ident), 0) >= self.limit

    def record(self, ident: str) -> None:
        key = self._key(ident)
        cache.add(key, 0, self.window)
        try:
            cache.incr(key)
        except ValueError:
            cache.set(key, 1, self.window)

    def reset(self, ident: str) -> None:
        cache.delete(self._key(ident))
```

`server/wcms/groups.py`:

```python
def user_group(user_id: int) -> str:
    return f"user-{user_id}"


def pc_group(pc_id: int) -> str:
    """클라이언트 연결이 들어가는 그룹."""
    return f"pc-{pc_id}"


def pc_watch_group(pc_id: int) -> str:
    """PC 하나를 보는 브라우저가 들어가는 그룹."""
    return f"pcwatch-{pc_id}"


def room_group(room_id: int) -> str:
    return f"room-{room_id}"


def room_public_group(room_id: int) -> str:
    return f"room-{room_id}-public"
```

`server/wcms/middleware.py`:

```python
from django.http import JsonResponse

from wcms.api import error_body
from wcms.net import is_internal_request


class InternalOnlyMiddleware:
    """클라이언트 경로(/client/)는 내부용 nginx 블록을 거친 요청만 받는다."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/client/") and not is_internal_request(request):
            return JsonResponse(error_body("not_found", "없는 경로입니다."), status=404)
        return self.get_response(request)
```

`server/wcms/settings.py`의 MIDDLEWARE에서 `"django.middleware.security.SecurityMiddleware",` 바로 다음 줄에 추가:

```python
    "wcms.middleware.InternalOnlyMiddleware",
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `uv run pytest -v`
Expected: 13 passed

- [ ] **Step 5: Commit**

```bash
git add server/wcms server/tests/test_common.py
git commit -m "feat(server): client IP, internal-path check, failure limiter, group names"
```

---

### Task 3: 감사 로그

**Files:**
- Create: `server/audit/models.py`, `server/audit/services.py`, `server/audit/serializers.py`, `server/audit/views.py`
- Modify: `server/audit/urls.py`
- Create: `server/audit/migrations/0001_initial.py` (makemigrations)
- Test: `server/tests/test_audit.py`

**Interfaces:**
- Produces:
  - `AuditLog(actor: User | None, action: str, target: str, detail: dict, created_at)`
  - `audit.services.record(actor, action: str, target: str = "", **detail) -> AuditLog` (`actor`가 미인증이면 None으로 저장)
  - `GET /api/audit` (관리자) → cursor 페이지네이션 `{"next": str | null, "previous": str | null, "results": [{"id", "actor", "action", "target", "detail", "created_at"}]}`, 한 페이지 50개, 최신순. `actor`는 사용자 이름 또는 null

- [ ] **Step 1: 실패하는 테스트 작성**

`server/tests/test_audit.py`:

```python
import pytest
from django.contrib.auth.models import AnonymousUser

from audit.models import AuditLog
from audit.services import record

pytestmark = pytest.mark.django_db


def test_record_stores_actor_and_detail(admin_user):
    entry = record(admin_user, "room.create", "room:1", name="301")
    assert entry.actor == admin_user
    assert entry.detail == {"name": "301"}


def test_record_anonymous_actor_is_none():
    entry = record(AnonymousUser(), "admin.enrolled", "user:1")
    assert entry.actor is None


def test_list_requires_admin(api):
    assert api.get("/api/audit").status_code == 401


def test_list_is_newest_first_and_paginated(admin_api, admin_user):
    for n in range(55):
        record(admin_user, "test.action", f"t:{n}")
    first = admin_api.get("/api/audit").json()
    assert len(first["results"]) == 50
    assert first["results"][0]["target"] == "t:54"
    assert first["results"][0]["actor"] == "admin"
    assert first["next"]
    second = admin_api.get(first["next"]).json()
    assert len(second["results"]) == 5
    assert AuditLog.objects.count() == 55
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `uv run pytest tests/test_audit.py -v`
Expected: FAIL, `ImportError`

- [ ] **Step 3: 구현**

`server/audit/models.py`:

```python
from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    action = models.CharField(max_length=64)
    target = models.CharField(max_length=128, blank=True)
    detail = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-id"]
```

`server/audit/services.py`:

```python
from audit.models import AuditLog


def record(actor, action: str, target: str = "", **detail) -> AuditLog:
    user = actor if actor is not None and actor.is_authenticated else None
    return AuditLog.objects.create(actor=user, action=action, target=target, detail=detail)
```

`server/audit/serializers.py`:

```python
from rest_framework import serializers

from audit.models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    actor = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = ["id", "actor", "action", "target", "detail", "created_at"]

    def get_actor(self, obj: AuditLog) -> str | None:
        return obj.actor.get_username() if obj.actor else None
```

`server/audit/views.py`:

```python
from rest_framework.generics import ListAPIView
from rest_framework.pagination import CursorPagination

from audit.models import AuditLog
from audit.serializers import AuditLogSerializer


class NewestFirst(CursorPagination):
    page_size = 50
    ordering = "-id"


class AuditLogList(ListAPIView):
    queryset = AuditLog.objects.select_related("actor")
    serializer_class = AuditLogSerializer
    pagination_class = NewestFirst
```

`server/audit/urls.py`:

```python
from django.urls import path

from audit.views import AuditLogList

urlpatterns = [
    path("audit", AuditLogList.as_view()),
]
```

Run: `uv run python manage.py makemigrations audit`

- [ ] **Step 4: 테스트 통과 확인**

Run: `uv run pytest -v`
Expected: 17 passed

- [ ] **Step 5: Commit**

```bash
git add server/audit server/tests/test_audit.py
git commit -m "feat(server): audit log with admin listing"
```

---

### Task 4: 관리자 계정 모델 (TOTP, 1회용 등록 링크, createadmin)

**Files:**
- Create: `server/accounts/totp.py`, `server/accounts/models.py`, `server/accounts/management/__init__.py`, `server/accounts/management/commands/__init__.py`, `server/accounts/management/commands/createadmin.py`
- Create: `server/accounts/migrations/0001_initial.py` (makemigrations)
- Test: `server/tests/test_accounts_models.py`

**Interfaces:**
- Consumes: `settings.WCMS_ENROLL_HOURS`
- Produces:
  - `accounts.totp.matching_step(secret: str, code: str) -> int | None` (6자리 ASCII 숫자만, 앞뒤 30초 허용)
  - `TOTPDevice(user OneToOne related_name="totp", secret, last_used_step)`, `TOTPDevice.verify(code) -> bool` (같은 step 재사용 불가, 조건부 update로 원자적)
  - `EnrollmentToken(user, token_hash, purpose: "new"|"reset", totp_secret, expires_at, used_at, created_by, created_at)`
    - `EnrollmentToken.issue(*, user, purpose: str, created_by) -> tuple[EnrollmentToken, str]` (같은 사용자의 미사용 토큰은 즉시 만료)
    - `EnrollmentToken.find_usable(token: str) -> EnrollmentToken | None`
    - `EnrollmentToken.needs_password -> bool` (purpose가 "new")
    - `EnrollmentToken.complete(*, password: str | None, code: str) -> bool` (코드가 맞으면 비밀번호 설정(new일 때), TOTPDevice 생성 또는 교체, 사용 처리. 등록에 쓴 코드는 로그인에 재사용 불가)
  - `uv run python manage.py createadmin <username>` → 관리자(is_staff, 비밀번호 없음) 생성 후 `/enroll/<token>` 한 줄 출력

- [ ] **Step 1: 실패하는 테스트 작성**

`server/tests/test_accounts_models.py`:

```python
import time
from datetime import timedelta
from io import StringIO

import pyotp
import pytest
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.utils import timezone

from accounts.models import EnrollmentToken, TOTPDevice
from accounts.totp import matching_step

pytestmark = pytest.mark.django_db
User = get_user_model()


def test_matching_step_accepts_current_code():
    secret = pyotp.random_base32()
    assert matching_step(secret, pyotp.TOTP(secret).now()) is not None


@pytest.mark.parametrize("code", ["", "12345", "1234567", "abcdef", "²²²²²²", "１２３４５６"])
def test_matching_step_rejects_malformed(code):
    assert matching_step(pyotp.random_base32(), code) is None


def test_device_code_cannot_be_reused(admin_user):
    device = TOTPDevice.objects.create(user=admin_user, secret=pyotp.random_base32())
    code = pyotp.TOTP(device.secret).now()
    assert device.verify(code) is True
    assert device.verify(code) is False


def test_issue_invalidates_previous_token(admin_user):
    _, first = EnrollmentToken.issue(user=admin_user, purpose="reset", created_by=None)
    _, second = EnrollmentToken.issue(user=admin_user, purpose="reset", created_by=None)
    assert EnrollmentToken.find_usable(first) is None
    assert EnrollmentToken.find_usable(second) is not None


def test_expired_and_used_tokens_unusable(admin_user):
    entry, token = EnrollmentToken.issue(user=admin_user, purpose="reset", created_by=None)
    entry.expires_at = timezone.now() - timedelta(seconds=1)
    entry.save()
    assert EnrollmentToken.find_usable(token) is None
    entry, token = EnrollmentToken.issue(user=admin_user, purpose="reset", created_by=None)
    assert entry.complete(password=None, code=pyotp.TOTP(entry.totp_secret).now()) is True
    assert EnrollmentToken.find_usable(token) is None


def test_complete_new_sets_password_and_device():
    user = User.objects.create_user("newbie", is_staff=True)
    entry, _ = EnrollmentToken.issue(user=user, purpose="new", created_by=None)
    assert entry.needs_password is True
    code = pyotp.TOTP(entry.totp_secret).now()
    assert entry.complete(password="a-long-new-password-7", code=code) is True
    user.refresh_from_db()
    assert user.check_password("a-long-new-password-7")
    assert user.totp.verify(code) is False


def test_complete_wrong_code_changes_nothing():
    user = User.objects.create_user("newbie", is_staff=True)
    entry, _ = EnrollmentToken.issue(user=user, purpose="new", created_by=None)
    assert entry.complete(password="a-long-new-password-7", code="000000") is False
    user.refresh_from_db()
    assert not user.has_usable_password()
    assert not TOTPDevice.objects.filter(user=user).exists()


def test_reset_replaces_device_keeps_password(admin_user):
    TOTPDevice.objects.create(user=admin_user, secret="OLDSECRETOLDSECRET")
    entry, _ = EnrollmentToken.issue(user=admin_user, purpose="reset", created_by=None)
    assert entry.needs_password is False
    assert entry.complete(password=None, code=pyotp.TOTP(entry.totp_secret).at(time.time())) is True
    admin_user.refresh_from_db()
    assert admin_user.totp.secret == entry.totp_secret
    assert admin_user.check_password("correct-horse-battery-9")


def test_createadmin_prints_enroll_link():
    out = StringIO()
    call_command("createadmin", "boss", stdout=out)
    user = User.objects.get(username="boss")
    assert user.is_staff and not user.has_usable_password()
    line = out.getvalue().strip()
    assert line.startswith("/enroll/")
    assert EnrollmentToken.find_usable(line.removeprefix("/enroll/")).user == user


def test_createadmin_rejects_existing_username(admin_user):
    with pytest.raises(CommandError):
        call_command("createadmin", "admin", stdout=StringIO())
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `uv run pytest tests/test_accounts_models.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'accounts.totp'`

- [ ] **Step 3: 구현**

`server/accounts/totp.py`:

```python
import hmac
import time

import pyotp

STEP_SECONDS = 30


def matching_step(secret: str, code: str) -> int | None:
    """코드가 맞는 30초 구간 번호를 돌려준다. 앞뒤 한 구간까지 허용한다."""
    code = code.replace(" ", "").strip()
    if not (len(code) == 6 and code.isascii() and code.isdigit()):
        return None
    totp = pyotp.TOTP(secret)
    current = int(time.time() // STEP_SECONDS)
    for step in (current - 1, current, current + 1):
        if hmac.compare_digest(totp.at(step * STEP_SECONDS), code):
            return step
    return None
```

`server/accounts/models.py`:

```python
import hashlib
import secrets
from datetime import timedelta

import pyotp
from django.conf import settings
from django.db import models, transaction
from django.utils import timezone

from accounts.totp import matching_step


class TOTPDevice(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="totp")
    secret = models.CharField(max_length=64)
    last_used_step = models.BigIntegerField(default=0)

    def verify(self, code: str) -> bool:
        step = matching_step(self.secret, code)
        if step is None:
            return False
        updated = TOTPDevice.objects.filter(pk=self.pk, last_used_step__lt=step).update(last_used_step=step)
        if updated:
            self.last_used_step = step
        return updated == 1


class EnrollmentToken(models.Model):
    NEW = "new"
    RESET = "reset"
    PURPOSES = [(NEW, "새 계정"), (RESET, "인증 앱 재설정")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="enrollments")
    token_hash = models.CharField(max_length=64, unique=True)
    purpose = models.CharField(max_length=8, choices=PURPOSES)
    totp_secret = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    @staticmethod
    def hash_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    @classmethod
    def issue(cls, *, user, purpose: str, created_by) -> tuple["EnrollmentToken", str]:
        now = timezone.now()
        cls.objects.filter(user=user, used_at__isnull=True, expires_at__gt=now).update(expires_at=now)
        token = secrets.token_urlsafe(32)
        entry = cls.objects.create(
            user=user,
            token_hash=cls.hash_token(token),
            purpose=purpose,
            totp_secret=pyotp.random_base32(),
            expires_at=now + timedelta(hours=settings.WCMS_ENROLL_HOURS),
            created_by=created_by if created_by is not None and created_by.is_authenticated else None,
        )
        return entry, token

    @classmethod
    def find_usable(cls, token: str) -> "EnrollmentToken | None":
        return (
            cls.objects.select_related("user")
            .filter(token_hash=cls.hash_token(token), used_at__isnull=True, expires_at__gt=timezone.now())
            .first()
        )

    @property
    def needs_password(self) -> bool:
        return self.purpose == self.NEW

    def complete(self, *, password: str | None, code: str) -> bool:
        step = matching_step(self.totp_secret, code)
        if step is None:
            return False
        with transaction.atomic():
            if self.needs_password:
                self.user.set_password(password)
                self.user.save(update_fields=["password"])
            TOTPDevice.objects.update_or_create(
                user=self.user, defaults={"secret": self.totp_secret, "last_used_step": step}
            )
            self.used_at = timezone.now()
            self.save(update_fields=["used_at"])
        return True
```

`server/accounts/management/__init__.py`, `server/accounts/management/commands/__init__.py`: 빈 파일.

`server/accounts/management/commands/createadmin.py`:

```python
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from accounts.models import EnrollmentToken


class Command(BaseCommand):
    help = "관리자 계정을 만들고 비밀번호·인증 앱 등록 링크를 출력한다. 첫 관리자를 만들 때 쓴다."

    def add_arguments(self, parser) -> None:
        parser.add_argument("username")

    def handle(self, *args, username: str, **options) -> None:
        User = get_user_model()
        if User.objects.filter(username=username).exists():
            raise CommandError("이미 있는 아이디입니다.")
        user = User.objects.create_user(username=username, is_staff=True)
        _, token = EnrollmentToken.issue(user=user, purpose=EnrollmentToken.NEW, created_by=None)
        self.stdout.write(f"/enroll/{token}")
```

Run: `uv run python manage.py makemigrations accounts`

- [ ] **Step 4: 테스트 통과 확인**

Run: `uv run pytest -v`
Expected: 모두 통과 (이 파일 15개)

- [ ] **Step 5: Commit**

```bash
git add server/accounts server/tests/test_accounts_models.py
git commit -m "feat(server): TOTP device, one-time enrollment tokens, createadmin command"
```

---

### Task 5: 로그인 API (비밀번호 → 인증 코드)

**Files:**
- Create: `server/accounts/serializers.py`, `server/accounts/views.py`
- Modify: `server/accounts/urls.py`
- Test: `server/tests/test_auth_api.py`

**Interfaces:**
- Consumes: `TOTPDevice`, `FailureLimiter`, `client_ip`, `ApiError`, `is_admin`, `error_responses`, `wcms.groups.user_group`
- Produces:
  - `GET /api/auth/me` (누구나) → `{"authenticated": bool, "user": {"id": int, "username": str} | null}`. 응답에 `csrftoken` 쿠키를 심는다
  - `POST /api/auth/login` `{username, password}` (CSRF 검사) → `200 {"next": "otp"}`. 오류: `400 invalid_credentials`, `403 totp_not_enrolled`, `429 too_many_attempts`
  - `POST /api/auth/otp` `{code}` (CSRF 검사) → `200` me와 같은 형식, 세션 생성. 오류: `401 no_pending_login`(대기 중 로그인 없음/5분 만료), `400 invalid_code`, `429 too_many_attempts`
  - `POST /api/auth/logout` → `204`. 그 사용자의 열린 `/ws/live` 연결에 `{"type": "session.end"}`를 `user_group`으로 보낸다
  - 시도 제한: 비밀번호 실패는 (IP+아이디) 5회, IP 20회, 아이디 50회 / 15분. 인증 코드 실패는 사용자별 5회 / 15분
  - `accounts.serializers.UserSerializer`, `MeSerializer` (다른 Task의 스키마에서 재사용)

- [ ] **Step 1: 실패하는 테스트 작성**

`server/tests/test_auth_api.py`:

```python
import time

import pyotp
import pytest
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APIClient

from accounts.models import TOTPDevice
from tests.conftest import PASSWORD
from wcms.groups import user_group

pytestmark = pytest.mark.django_db


@pytest.fixture
def device(admin_user):
    return TOTPDevice.objects.create(user=admin_user, secret=pyotp.random_base32())


def password_step(client, username="admin", password=PASSWORD, ip="10.0.0.1"):
    return client.post("/api/auth/login", {"username": username, "password": password}, format="json", REMOTE_ADDR=ip)


def code_now(device, offset=0):
    return pyotp.TOTP(device.secret).at(time.time() + offset)


def test_me_anonymous_sets_csrf_cookie(api):
    response = api.get("/api/auth/me")
    assert response.json() == {"authenticated": False, "user": None}
    assert "csrftoken" in response.cookies


def test_wrong_password(api, device):
    response = password_step(api, password="wrong")
    assert response.status_code == 400
    assert response.json()["error"] == "invalid_credentials"


def test_non_staff_rejected(api):
    get_user_model().objects.create_user("student", password=PASSWORD)
    assert password_step(api, username="student").json()["error"] == "invalid_credentials"


def test_not_enrolled(api, admin_user):
    response = password_step(api)
    assert response.status_code == 403
    assert response.json()["error"] == "totp_not_enrolled"


def test_password_alone_does_not_log_in(api, device):
    assert password_step(api).json() == {"next": "otp"}
    assert api.get("/api/auth/me").json()["authenticated"] is False


def test_full_login(api, device, admin_user):
    password_step(api)
    response = api.post("/api/auth/otp", {"code": code_now(device)}, format="json")
    assert response.status_code == 200
    assert response.json() == {"authenticated": True, "user": {"id": admin_user.id, "username": "admin"}}
    assert api.get("/api/auth/me").json()["authenticated"] is True


def test_otp_without_password_step(api, device):
    response = api.post("/api/auth/otp", {"code": code_now(device)}, format="json")
    assert response.status_code == 401
    assert response.json()["error"] == "no_pending_login"


def test_pending_login_expires(api, device):
    with override_settings(WCMS_PENDING_LOGIN_SECONDS=-1):
        password_step(api)
    response = api.post("/api/auth/otp", {"code": code_now(device)}, format="json")
    assert response.json()["error"] == "no_pending_login"


def test_otp_lock_applies_across_sessions(api, device):
    password_step(api)
    for _ in range(5):
        api.post("/api/auth/otp", {"code": "000000"}, format="json")
    fresh = APIClient()
    response = password_step(fresh)
    assert response.status_code == 429
    assert response.json()["error"] == "too_many_attempts"


def test_password_lock_is_per_ip_and_username(api, device):
    for _ in range(5):
        password_step(api, password="wrong", ip="10.0.0.1")
    assert password_step(api, ip="10.0.0.1").status_code == 429
    assert password_step(APIClient(), ip="10.0.0.2").json() == {"next": "otp"}


def test_login_requires_csrf_token(device):
    client = APIClient(enforce_csrf_checks=True)
    response = password_step(client)
    assert response.status_code == 403
    assert response.json()["error"] == "csrf_failed"
    token = client.get("/api/auth/me").cookies["csrftoken"].value
    response = client.post(
        "/api/auth/login", {"username": "admin", "password": PASSWORD}, format="json", HTTP_X_CSRFTOKEN=token
    )
    assert response.json() == {"next": "otp"}


def test_logout_ends_live_sessions(admin_api, admin_user):
    layer = get_channel_layer()
    channel = async_to_sync(layer.new_channel)()
    async_to_sync(layer.group_add)(user_group(admin_user.id), channel)
    assert admin_api.post("/api/auth/logout").status_code == 204
    assert admin_api.get("/api/auth/me").json()["authenticated"] is False
    assert async_to_sync(layer.receive)(channel) == {"type": "session.end"}


def test_admin_api_requires_login(api):
    response = api.get("/api/audit")
    assert response.status_code == 401
    assert response.json()["error"] == "not_authenticated"
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `uv run pytest tests/test_auth_api.py -v`
Expected: FAIL (404)

- [ ] **Step 3: 구현**

`server/accounts/serializers.py`:

```python
from rest_framework import serializers


class UserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()


class MeSerializer(serializers.Serializer):
    authenticated = serializers.BooleanField()
    user = UserSerializer(allow_null=True)


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=128, trim_whitespace=False)


class LoginResultSerializer(serializers.Serializer):
    next = serializers.ChoiceField(choices=["otp"])


class CodeSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=10)


def me_payload(user) -> dict:
    if user is None:
        return {"authenticated": False, "user": None}
    return {"authenticated": True, "user": {"id": user.id, "username": user.get_username()}}
```

`server/accounts/views.py`:

```python
import time

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import TOTPDevice
from accounts.serializers import CodeSerializer, LoginResultSerializer, LoginSerializer, MeSerializer, me_payload
from wcms.api import ApiError, error_responses, is_admin
from wcms.groups import user_group
from wcms.limits import FailureLimiter
from wcms.net import client_ip

PENDING_KEY = "auth_pending"
BACKEND = "django.contrib.auth.backends.ModelBackend"
TOO_MANY = "잠시 후 다시 시도하세요."

login_pair = FailureLimiter("login-pair", limit=5, window=900)
login_ip = FailureLimiter("login-ip", limit=20, window=900)
login_user = FailureLimiter("login-user", limit=50, window=900)
otp_user = FailureLimiter("otp-user", limit=5, window=900)


def end_live_sessions(user_id: int) -> None:
    async_to_sync(get_channel_layer().group_send)(user_group(user_id), {"type": "session.end"})


@method_decorator(ensure_csrf_cookie, name="dispatch")
class MeView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses={200: MeSerializer})
    def get(self, request):
        return Response(me_payload(request.user if is_admin(request.user) else None))


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=LoginSerializer, responses={200: LoginResultSerializer, **error_responses(400, 403, 429)})
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        username = serializer.validated_data["username"]
        name_key = username.lower()
        ip = client_ip(request)
        pair_key = f"{ip}|{name_key}"
        if login_pair.blocked(pair_key) or login_ip.blocked(ip) or login_user.blocked(name_key):
            raise ApiError("too_many_attempts", TOO_MANY, 429)

        user = authenticate(request._request, username=username, password=serializer.validated_data["password"])
        if user is None or not user.is_staff:
            login_pair.record(pair_key)
            login_ip.record(ip)
            login_user.record(name_key)
            raise ApiError("invalid_credentials", "아이디 또는 비밀번호가 올바르지 않습니다.")
        if not TOTPDevice.objects.filter(user=user).exists():
            raise ApiError("totp_not_enrolled", "인증 앱 등록이 필요합니다. 관리자에게 등록 링크를 받으세요.", 403)
        if otp_user.blocked(str(user.pk)):
            raise ApiError("too_many_attempts", TOO_MANY, 429)

        login_pair.reset(pair_key)
        request.session[PENDING_KEY] = {"user": user.pk, "until": time.time() + settings.WCMS_PENDING_LOGIN_SECONDS}
        return Response({"next": "otp"})


@method_decorator(csrf_protect, name="dispatch")
class OtpView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=CodeSerializer, responses={200: MeSerializer, **error_responses(400, 401, 429)})
    def post(self, request):
        serializer = CodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pending = request.session.get(PENDING_KEY) or {}
        user = None
        if pending.get("until", 0) > time.time():
            user = get_user_model().objects.filter(pk=pending.get("user"), is_active=True, is_staff=True).first()
        if user is None:
            request.session.pop(PENDING_KEY, None)
            raise ApiError("no_pending_login", "처음부터 다시 로그인하세요.", 401)

        ident = str(user.pk)
        if otp_user.blocked(ident):
            request.session.pop(PENDING_KEY, None)
            raise ApiError("too_many_attempts", TOO_MANY, 429)
        device = TOTPDevice.objects.filter(user=user).first()
        if device is None or not device.verify(serializer.validated_data["code"]):
            otp_user.record(ident)
            if otp_user.blocked(ident):
                request.session.pop(PENDING_KEY, None)
            raise ApiError("invalid_code", "인증 코드가 올바르지 않습니다.")

        request.session.pop(PENDING_KEY, None)
        otp_user.reset(ident)
        login(request._request, user, backend=BACKEND)
        return Response(me_payload(user))


class LogoutView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=None, responses={204: None})
    def post(self, request):
        user_id = request.user.pk if request.user.is_authenticated else None
        logout(request._request)
        if user_id is not None:
            end_live_sessions(user_id)
        return Response(status=204)
```

`server/accounts/urls.py`:

```python
from django.urls import path

from accounts import views

urlpatterns = [
    path("auth/me", views.MeView.as_view()),
    path("auth/login", views.LoginView.as_view()),
    path("auth/otp", views.OtpView.as_view()),
    path("auth/logout", views.LogoutView.as_view()),
]
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `uv run pytest -v`
Expected: 모두 통과

- [ ] **Step 5: Commit**

```bash
git add server/accounts server/tests/test_auth_api.py
git commit -m "feat(server): password + TOTP login API with failure limits"
```

---

### Task 6: 등록 링크 API와 관리자 계정 관리 API

**Files:**
- Modify: `server/accounts/serializers.py` (추가), `server/accounts/views.py` (추가), `server/accounts/urls.py`
- Test: `server/tests/test_admins_api.py`

**Interfaces:**
- Consumes: `EnrollmentToken`, `TOTPDevice`, `audit.services.record`, `end_live_sessions`, `FailureLimiter`
- Produces:
  - `GET /api/auth/enroll/<token>` (누구나, 캐시 금지) → `{"username", "needs_password": bool, "secret": str, "otp_uri": str, "qr_svg": str}`. 잘못되거나 만료·사용된 토큰은 `404 invalid_token`
  - `POST /api/auth/enroll/<token>` `{password?, code}` (CSRF 검사) → `204`. 오류: `400 invalid`(fields.password, 비밀번호 규칙), `400 invalid_code`, `404 invalid_token`, `429 too_many_attempts`(토큰별 10회 / 15분). 로그인은 시키지 않는다
  - `GET /api/admins` → `[{"id", "username", "totp_enrolled": bool, "is_self": bool}]`
  - `POST /api/admins` `{username}` → `201 {"admin": {...}, "enroll_url": "/enroll/<token>", "expires_at"}`
  - `POST /api/admins/<id>/reset` → `200 {"enroll_url", "expires_at"}` (인증 앱 재설정 링크)
  - `DELETE /api/admins/<id>` → `204`. 자기 자신은 `400 cannot_delete_self`. 삭제된 관리자의 `/ws/live`는 닫힌다
  - 감사 로그 action: `admin.create`, `admin.reset`, `admin.delete`, `admin.enrolled`

- [ ] **Step 1: 실패하는 테스트 작성**

`server/tests/test_admins_api.py`:

```python
import time

import pyotp
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from accounts.models import EnrollmentToken, TOTPDevice
from audit.models import AuditLog

pytestmark = pytest.mark.django_db
User = get_user_model()


def token_of(url: str) -> str:
    return url.removeprefix("/enroll/")


def create_admin(admin_api, username="kim"):
    return admin_api.post("/api/admins", {"username": username}, format="json")


def test_admin_endpoints_require_login(api):
    assert api.get("/api/admins").status_code == 401


def test_create_admin_returns_enroll_link(admin_api):
    response = create_admin(admin_api)
    assert response.status_code == 201
    body = response.json()
    assert body["admin"]["username"] == "kim"
    assert body["admin"]["totp_enrolled"] is False
    assert body["enroll_url"].startswith("/enroll/")
    assert AuditLog.objects.filter(action="admin.create").exists()


def test_create_duplicate_username(admin_api):
    response = create_admin(admin_api, "admin")
    assert response.status_code == 400
    assert "username" in response.json()["fields"]


def test_enroll_info_and_complete_then_login(admin_api):
    url = create_admin(admin_api).json()["enroll_url"]
    anon = APIClient()
    info = anon.get(f"/api/auth{url}")
    assert info.status_code == 200
    data = info.json()
    assert data["username"] == "kim"
    assert data["needs_password"] is True
    assert data["qr_svg"].startswith("<svg")
    assert "no-store" in info["Cache-Control"] or "max-age=0" in info["Cache-Control"]

    weak = anon.post(f"/api/auth{url}", {"password": "short", "code": "000000"}, format="json")
    assert weak.status_code == 400
    assert "password" in weak.json()["fields"]

    code = pyotp.TOTP(data["secret"]).now()
    done = anon.post(f"/api/auth{url}", {"password": "kim-long-password-42", "code": code}, format="json")
    assert done.status_code == 204
    assert anon.get(f"/api/auth{url}").status_code == 404

    login = APIClient()
    login.post("/api/auth/login", {"username": "kim", "password": "kim-long-password-42"}, format="json")
    later = pyotp.TOTP(data["secret"]).at(time.time() + 30)
    assert login.post("/api/auth/otp", {"code": later}, format="json").json()["authenticated"] is True


def test_enroll_wrong_code(admin_api):
    url = create_admin(admin_api).json()["enroll_url"]
    response = APIClient().post(f"/api/auth{url}", {"password": "kim-long-password-42", "code": "000000"}, format="json")
    assert response.json()["error"] == "invalid_code"


def test_enroll_invalid_token(api):
    assert api.get("/api/auth/enroll/not-a-token").json()["error"] == "invalid_token"


def test_reset_link_keeps_password(admin_api):
    target = User.objects.create_user("lee", password="lee-long-password-42", is_staff=True)
    TOTPDevice.objects.create(user=target, secret=pyotp.random_base32())
    url = admin_api.post(f"/api/admins/{target.id}/reset").json()["enroll_url"]
    anon = APIClient()
    data = anon.get(f"/api/auth{url}").json()
    assert data["needs_password"] is False
    assert anon.post(f"/api/auth{url}", {"code": pyotp.TOTP(data["secret"]).now()}, format="json").status_code == 204
    target.refresh_from_db()
    assert target.totp.secret == data["secret"]
    assert target.check_password("lee-long-password-42")


def test_list_marks_self(admin_api, admin_user):
    create_admin(admin_api)
    rows = admin_api.get("/api/admins").json()
    me = next(row for row in rows if row["id"] == admin_user.id)
    assert me["is_self"] is True
    assert len(rows) == 2


def test_cannot_delete_self(admin_api, admin_user):
    response = admin_api.delete(f"/api/admins/{admin_user.id}")
    assert response.status_code == 400
    assert response.json()["error"] == "cannot_delete_self"


def test_delete_other_admin(admin_api):
    target_id = create_admin(admin_api).json()["admin"]["id"]
    assert admin_api.delete(f"/api/admins/{target_id}").status_code == 204
    assert not User.objects.filter(id=target_id).exists()


def test_reissue_invalidates_old_link(admin_api):
    created = create_admin(admin_api).json()
    old = token_of(created["enroll_url"])
    admin_api.post(f"/api/admins/{created['admin']['id']}/reset")
    assert EnrollmentToken.find_usable(old) is None
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `uv run pytest tests/test_admins_api.py -v`
Expected: FAIL (404)

- [ ] **Step 3: 구현**

`server/accounts/serializers.py` 맨 위 import에 `from django.contrib.auth import get_user_model`을 추가하고, 파일 끝에 추가:

```python
class EnrollInfoSerializer(serializers.Serializer):
    username = serializers.CharField()
    needs_password = serializers.BooleanField()
    secret = serializers.CharField()
    otp_uri = serializers.CharField()
    qr_svg = serializers.CharField()


class EnrollCompleteSerializer(serializers.Serializer):
    password = serializers.CharField(max_length=128, required=False, trim_whitespace=False)
    code = serializers.CharField(max_length=10)


class AdminSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    totp_enrolled = serializers.BooleanField()
    is_self = serializers.BooleanField()


class AdminCreateSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, validators=[get_user_model().username_validator])

    def validate_username(self, value: str) -> str:
        if get_user_model().objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("이미 있는 아이디입니다.")
        return value


class EnrollLinkSerializer(serializers.Serializer):
    enroll_url = serializers.CharField()
    expires_at = serializers.DateTimeField()


class AdminCreatedSerializer(EnrollLinkSerializer):
    admin = AdminSerializer()


def admin_payload(user, current) -> dict:
    return {
        "id": user.id,
        "username": user.get_username(),
        "totp_enrolled": hasattr(user, "totp"),
        "is_self": user.id == current.id,
    }
```

`server/accounts/views.py` 맨 위 import에 추가:

```python
import pyotp
import segno
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import never_cache
from rest_framework import serializers as drf_serializers

from accounts.models import EnrollmentToken
from accounts.serializers import (
    AdminCreatedSerializer,
    AdminCreateSerializer,
    AdminSerializer,
    EnrollCompleteSerializer,
    EnrollInfoSerializer,
    EnrollLinkSerializer,
    admin_payload,
)
from audit.services import record
```

`server/accounts/views.py` 끝에 추가:

```python
enroll_attempts = FailureLimiter("enroll", limit=10, window=900)
INVALID_TOKEN = "링크가 만료됐거나 이미 사용됐습니다. 관리자에게 새 링크를 받으세요."


def usable_token(token: str) -> EnrollmentToken:
    entry = EnrollmentToken.find_usable(token)
    if entry is None:
        raise ApiError("invalid_token", INVALID_TOKEN, 404)
    return entry


@method_decorator([never_cache, csrf_protect], name="dispatch")
class EnrollView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses={200: EnrollInfoSerializer, **error_responses(404)})
    def get(self, request, token: str):
        entry = usable_token(token)
        uri = pyotp.TOTP(entry.totp_secret).provisioning_uri(name=entry.user.get_username(), issuer_name="WCMS")
        return Response(
            {
                "username": entry.user.get_username(),
                "needs_password": entry.needs_password,
                "secret": entry.totp_secret,
                "otp_uri": uri,
                "qr_svg": segno.make(uri, error="m").svg_inline(scale=5),
            }
        )

    @extend_schema(request=EnrollCompleteSerializer, responses={204: None, **error_responses(400, 404, 429)})
    def post(self, request, token: str):
        entry = usable_token(token)
        if enroll_attempts.blocked(entry.token_hash):
            raise ApiError("too_many_attempts", TOO_MANY, 429)
        serializer = EnrollCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        password = serializer.validated_data.get("password")
        if entry.needs_password:
            if not password:
                raise drf_serializers.ValidationError({"password": ["비밀번호를 입력하세요."]})
            try:
                validate_password(password, entry.user)
            except DjangoValidationError as exc:
                raise drf_serializers.ValidationError({"password": list(exc.messages)})
        if not entry.complete(password=password, code=serializer.validated_data["code"]):
            enroll_attempts.record(entry.token_hash)
            raise ApiError("invalid_code", "인증 코드가 올바르지 않습니다.")
        record(entry.user, "admin.enrolled", f"user:{entry.user.id}", purpose=entry.purpose)
        return Response(status=204)


def staff_users():
    return get_user_model().objects.filter(is_staff=True).select_related("totp")


def enroll_link(entry: EnrollmentToken, token: str) -> dict:
    return {"enroll_url": f"/enroll/{token}", "expires_at": entry.expires_at}


class AdminListView(APIView):
    @extend_schema(responses={200: AdminSerializer(many=True)})
    def get(self, request):
        return Response([admin_payload(user, request.user) for user in staff_users().order_by("username")])

    @extend_schema(request=AdminCreateSerializer, responses={201: AdminCreatedSerializer, **error_responses(400)})
    def post(self, request):
        serializer = AdminCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = get_user_model().objects.create_user(username=serializer.validated_data["username"], is_staff=True)
        entry, token = EnrollmentToken.issue(user=user, purpose=EnrollmentToken.NEW, created_by=request.user)
        record(request.user, "admin.create", f"user:{user.id}", username=user.get_username())
        return Response({"admin": admin_payload(user, request.user), **enroll_link(entry, token)}, status=201)


class AdminResetView(APIView):
    @extend_schema(request=None, responses={200: EnrollLinkSerializer, **error_responses(404)})
    def post(self, request, pk: int):
        user = get_object_or_404(staff_users(), pk=pk)
        entry, token = EnrollmentToken.issue(user=user, purpose=EnrollmentToken.RESET, created_by=request.user)
        record(request.user, "admin.reset", f"user:{user.id}")
        return Response(enroll_link(entry, token))


class AdminDetailView(APIView):
    @extend_schema(responses={204: None, **error_responses(400, 404)})
    def delete(self, request, pk: int):
        user = get_object_or_404(staff_users(), pk=pk)
        if user.id == request.user.id:
            raise ApiError("cannot_delete_self", "자기 계정은 삭제할 수 없습니다.")
        record(request.user, "admin.delete", f"user:{user.id}", username=user.get_username())
        user.delete()
        end_live_sessions(pk)
        return Response(status=204)
```

`server/accounts/urls.py` 전체:

```python
from django.urls import path

from accounts import views

urlpatterns = [
    path("auth/me", views.MeView.as_view()),
    path("auth/login", views.LoginView.as_view()),
    path("auth/otp", views.OtpView.as_view()),
    path("auth/logout", views.LogoutView.as_view()),
    path("auth/enroll/<str:token>", views.EnrollView.as_view()),
    path("admins", views.AdminListView.as_view()),
    path("admins/<int:pk>", views.AdminDetailView.as_view()),
    path("admins/<int:pk>/reset", views.AdminResetView.as_view()),
]
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `uv run pytest -v`
Expected: 모두 통과

- [ ] **Step 5: Commit**

```bash
git add server/accounts server/tests/test_admins_api.py
git commit -m "feat(server): enrollment link and admin account management API"
```

---

### Task 7: 실습실, PC, 등록 PIN 모델

**Files:**
- Create: `server/labs/models.py`
- Create: `server/labs/migrations/0001_initial.py` (makemigrations)
- Test: `server/tests/test_labs_models.py`

**Interfaces:**
- Produces:
  - `Room(name unique, rows, cols, aisle_after: int | None (1부터 센 열 번호, 그 열 뒤에 통로), sort_order)`, 정렬 `sort_order, name`
  - `PC(hostname, machine_guid unique, token_hash unique, client_version, specs: dict, room FK(SET_NULL, related_name="pcs") | None, row | None, col | None, registered_at)`, 제약 `unique_seat(room, row, col)`
    - `PC.hash_token(token) -> str`, `PC.register(*, hostname, machine_guid, specs, version) -> tuple[PC, str]` (같은 machine_guid면 갱신·토큰 교체·자리 유지), `PC.from_token(token) -> PC | None`
    - `PC.seated -> bool`, `PC.label -> str` (자리 있으면 `"{room.name}-{번호:02d}"`, 번호 = `row * room.cols + col + 1`, 없으면 hostname)
  - `RegistrationPin(pin unique, multi_use, expires_at, used_count, revoked, created_by, created_at)`
    - `RegistrationPin.issue(*, user, multi_use: bool, minutes: int)` (중복 시 재시도, IntegrityError 처리), `is_usable(now=None) -> bool`, `RegistrationPin.consume(pin) -> bool` (트랜잭션)
    - 쿼리셋 헬퍼 `RegistrationPin.usable()` → 지금 쓸 수 있는 PIN만

- [ ] **Step 1: 실패하는 테스트 작성**

`server/tests/test_labs_models.py`:

```python
from datetime import timedelta

import pytest
from django.db import IntegrityError
from django.utils import timezone

from labs.models import PC, RegistrationPin, Room

pytestmark = pytest.mark.django_db


def make_pc(guid="guid-1", hostname="LAB-01") -> tuple[PC, str]:
    return PC.register(hostname=hostname, machine_guid=guid, specs={"cpu": "i5"}, version="2026.1")


def test_pin_format_and_single_use():
    pin = RegistrationPin.issue(user=None, multi_use=False, minutes=10)
    assert len(pin.pin) == 6 and pin.pin.isdigit()
    assert RegistrationPin.consume(pin.pin) is True
    assert RegistrationPin.consume(pin.pin) is False


def test_multi_use_pin():
    pin = RegistrationPin.issue(user=None, multi_use=True, minutes=10)
    assert all(RegistrationPin.consume(pin.pin) for _ in range(3))


def test_expired_revoked_unknown_pins():
    expired = RegistrationPin.issue(user=None, multi_use=True, minutes=10)
    expired.expires_at = timezone.now() - timedelta(seconds=1)
    expired.save()
    revoked = RegistrationPin.issue(user=None, multi_use=True, minutes=10)
    revoked.revoked = True
    revoked.save()
    assert RegistrationPin.consume(expired.pin) is False
    assert RegistrationPin.consume(revoked.pin) is False
    assert RegistrationPin.consume("999999") is False


def test_usable_queryset_excludes_spent_single_use():
    spent = RegistrationPin.issue(user=None, multi_use=False, minutes=10)
    RegistrationPin.consume(spent.pin)
    live = RegistrationPin.issue(user=None, multi_use=False, minutes=10)
    assert list(RegistrationPin.usable()) == [live]


def test_token_is_hashed_and_resolves():
    pc, token = make_pc()
    assert pc.token_hash == PC.hash_token(token) != token
    assert PC.from_token(token) == pc
    assert PC.from_token("wrong") is None


def test_reregister_keeps_seat_and_rotates_token():
    room = Room.objects.create(name="301", rows=5, cols=8)
    pc, old = make_pc()
    pc.room, pc.row, pc.col = room, 1, 4
    pc.save()
    again, new = make_pc(hostname="LAB-01-NEW")
    assert again.pk == pc.pk and again.room == room and again.hostname == "LAB-01-NEW"
    assert PC.from_token(old) is None and PC.from_token(new) == pc


def test_label_and_seated():
    room = Room.objects.create(name="301", rows=5, cols=8)
    pc, _ = make_pc()
    assert pc.seated is False and pc.label == "LAB-01"
    pc.room, pc.row, pc.col = room, 1, 4
    pc.save()
    assert pc.seated is True and pc.label == "301-13"


def test_seat_is_unique():
    room = Room.objects.create(name="301", rows=5, cols=8)
    a, _ = make_pc("g1", "A")
    b, _ = make_pc("g2", "B")
    a.room, a.row, a.col = room, 0, 0
    a.save()
    b.room, b.row, b.col = room, 0, 0
    with pytest.raises(IntegrityError):
        b.save()
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `uv run pytest tests/test_labs_models.py -v`
Expected: FAIL, `ImportError`

- [ ] **Step 3: 구현**

`server/labs/models.py`:

```python
import hashlib
import secrets
from datetime import datetime, timedelta

from django.conf import settings
from django.db import IntegrityError, models, transaction
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
    room = models.ForeignKey(Room, null=True, blank=True, on_delete=models.SET_NULL, related_name="pcs")
    row = models.PositiveSmallIntegerField(null=True, blank=True)
    col = models.PositiveSmallIntegerField(null=True, blank=True)
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["hostname"]
        constraints = [models.UniqueConstraint(fields=["room", "row", "col"], name="unique_seat")]

    def __str__(self) -> str:
        return self.label

    @staticmethod
    def hash_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    @classmethod
    def register(cls, *, hostname: str, machine_guid: str, specs: dict, version: str) -> tuple["PC", str]:
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
    def seated(self) -> bool:
        return self.room_id is not None and self.row is not None and self.col is not None

    @property
    def label(self) -> str:
        if self.seated:
            return f"{self.room.name}-{self.row * self.room.cols + self.col + 1:02d}"
        return self.hostname


class RegistrationPin(models.Model):
    pin = models.CharField(max_length=6, unique=True)
    multi_use = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    used_count = models.PositiveIntegerField(default=0)
    revoked = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    @classmethod
    def issue(cls, *, user, multi_use: bool, minutes: int) -> "RegistrationPin":
        creator = user if user is not None and user.is_authenticated else None
        for _ in range(20):
            try:
                with transaction.atomic():
                    return cls.objects.create(
                        pin=f"{secrets.randbelow(10**6):06d}",
                        multi_use=multi_use,
                        expires_at=timezone.now() + timedelta(minutes=minutes),
                        created_by=creator,
                    )
            except IntegrityError:
                continue
        raise RuntimeError("PIN을 만들지 못했습니다.")

    @classmethod
    def usable(cls) -> models.QuerySet:
        return cls.objects.filter(revoked=False, expires_at__gt=timezone.now()).filter(
            models.Q(multi_use=True) | models.Q(used_count=0)
        )

    def is_usable(self, now: datetime | None = None) -> bool:
        now = now or timezone.now()
        if self.revoked or now >= self.expires_at:
            return False
        return self.multi_use or self.used_count == 0

    @classmethod
    def consume(cls, pin: str) -> bool:
        with transaction.atomic():
            entry = cls.objects.select_for_update().filter(pin=pin).first()
            if entry is None or not entry.is_usable():
                return False
            entry.used_count += 1
            entry.save(update_fields=["used_count"])
            return True
```

Run: `uv run python manage.py makemigrations labs`

- [ ] **Step 4: 테스트 통과 확인**

Run: `uv run pytest -v`
Expected: 모두 통과

- [ ] **Step 5: Commit**

```bash
git add server/labs server/tests/test_labs_models.py
git commit -m "feat(server): room, PC and registration PIN models"
```

---

### Task 8: 실습실·좌석·PC·PIN 관리 API

**Files:**
- Create: `server/labs/serializers.py`, `server/labs/views.py`
- Modify: `server/labs/urls.py`
- Test: `server/tests/test_labs_api.py`

**Interfaces:**
- Consumes: `Room`, `PC`, `RegistrationPin`, `audit.services.record`, `wcms.groups.pc_group`
- Produces (모두 관리자 전용):
  - `GET/POST /api/rooms`, `GET/PATCH/DELETE /api/rooms/<id>`: `{"id", "name", "rows", "cols", "aisle_after", "sort_order"}`. rows·cols 1~20, aisle_after는 null 또는 1 ≤ aisle_after < cols. 크기를 줄이면 범위 밖 자리의 PC는 자리 해제. 삭제하면 그 실습실 PC 전부 자리 해제
  - `GET/PUT /api/rooms/<id>/seats`: `{"seats": [{"row", "col", "pc"}]}`. PUT은 전체 교체. 같은 PC 두 번, 같은 자리 두 번, 범위 밖, 없는 PC → 400 invalid
  - `GET /api/pcs`: `[{"id", "hostname", "label", "room", "row", "col", "client_version", "specs", "registered_at"}]`
  - `DELETE /api/pcs/<id>` → 204. 그 PC의 클라이언트 연결에 `{"type": "pc.revoked"}`를 `pc_group`으로 보낸다
  - `GET /api/pins` (지금 쓸 수 있는 것만), `POST /api/pins` `{multi_use: bool, minutes: 10 | 60 | 180}` → 201, `DELETE /api/pins/<id>` → 204 (폐기)
  - 좌석이나 실습실이 바뀐 뒤 부르는 훅: `labs.views.room_changed(room_id: int)` — 이 Task에서는 아무것도 하지 않는 함수로 두고, Task 11에서 실시간 알림을 연결한다
  - 감사 로그 action: `room.create`, `room.update`, `room.delete`, `room.seats`, `pc.delete`, `pin.issue`, `pin.revoke`

- [ ] **Step 1: 실패하는 테스트 작성**

`server/tests/test_labs_api.py`:

```python
import pytest
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from audit.models import AuditLog
from labs.models import PC, RegistrationPin, Room
from wcms.groups import pc_group

pytestmark = pytest.mark.django_db


def make_pc(n: int) -> PC:
    pc, _ = PC.register(hostname=f"LAB-{n:02d}", machine_guid=f"g{n}", specs={}, version="2026.1")
    return pc


def seat(pc: PC, room: Room, row: int, col: int) -> None:
    pc.room, pc.row, pc.col = room, row, col
    pc.save()


def test_requires_admin(api):
    for url in ["/api/rooms", "/api/pcs", "/api/pins"]:
        assert api.get(url).status_code == 401


def test_room_crud(admin_api):
    created = admin_api.post("/api/rooms", {"name": "301", "rows": 5, "cols": 8, "aisle_after": 4}, format="json")
    assert created.status_code == 201
    room_id = created.json()["id"]
    assert admin_api.get("/api/rooms").json()[0]["name"] == "301"
    patched = admin_api.patch(f"/api/rooms/{room_id}", {"name": "302"}, format="json")
    assert patched.json()["name"] == "302"
    assert admin_api.delete(f"/api/rooms/{room_id}").status_code == 204
    assert AuditLog.objects.filter(action__startswith="room.").count() == 3


@pytest.mark.parametrize(
    "body", [{"rows": 0}, {"cols": 21}, {"aisle_after": 8}, {"aisle_after": 0}]
)
def test_room_validation(admin_api, body):
    response = admin_api.post("/api/rooms", {"name": "301", "rows": 5, "cols": 8, **body}, format="json")
    assert response.status_code == 400
    assert response.json()["error"] == "invalid"


def test_shrinking_room_unseats_out_of_range(admin_api):
    room = Room.objects.create(name="301", rows=2, cols=4)
    inside, outside = make_pc(1), make_pc(2)
    seat(inside, room, 0, 0)
    seat(outside, room, 0, 3)
    admin_api.patch(f"/api/rooms/{room.id}", {"cols": 3}, format="json")
    outside.refresh_from_db()
    inside.refresh_from_db()
    assert outside.room is None and outside.row is None
    assert inside.room == room


def test_delete_room_unseats(admin_api):
    room = Room.objects.create(name="301", rows=2, cols=4)
    pc = make_pc(1)
    seat(pc, room, 1, 1)
    admin_api.delete(f"/api/rooms/{room.id}")
    pc.refresh_from_db()
    assert (pc.room, pc.row, pc.col) == (None, None, None)


def test_replace_seats(admin_api):
    room = Room.objects.create(name="301", rows=2, cols=4)
    a, b, c = make_pc(1), make_pc(2), make_pc(3)
    seat(c, room, 1, 3)
    response = admin_api.put(
        f"/api/rooms/{room.id}/seats",
        {"seats": [{"row": 0, "col": 0, "pc": a.id}, {"row": 1, "col": 3, "pc": b.id}]},
        format="json",
    )
    assert response.status_code == 200
    for pc in (a, b, c):
        pc.refresh_from_db()
    assert (a.row, a.col, b.row, b.col) == (0, 0, 1, 3)
    assert c.room is None
    assert sorted(s["pc"] for s in admin_api.get(f"/api/rooms/{room.id}/seats").json()["seats"]) == [a.id, b.id]


@pytest.mark.parametrize("problem", ["dup_pc", "dup_seat", "out_of_range", "missing_pc"])
def test_seat_validation(admin_api, problem):
    room = Room.objects.create(name="301", rows=2, cols=4)
    a, b = make_pc(1), make_pc(2)
    seats = {
        "dup_pc": [{"row": 0, "col": 0, "pc": a.id}, {"row": 0, "col": 1, "pc": a.id}],
        "dup_seat": [{"row": 0, "col": 0, "pc": a.id}, {"row": 0, "col": 0, "pc": b.id}],
        "out_of_range": [{"row": 2, "col": 0, "pc": a.id}],
        "missing_pc": [{"row": 0, "col": 0, "pc": 9999}],
    }[problem]
    response = admin_api.put(f"/api/rooms/{room.id}/seats", {"seats": seats}, format="json")
    assert response.status_code == 400
    a.refresh_from_db()
    assert a.room is None


def test_pc_list_and_delete(admin_api):
    pc = make_pc(1)
    rows = admin_api.get("/api/pcs").json()
    assert rows[0]["hostname"] == "LAB-01" and rows[0]["label"] == "LAB-01"
    layer = get_channel_layer()
    channel = async_to_sync(layer.new_channel)()
    async_to_sync(layer.group_add)(pc_group(pc.id), channel)
    assert admin_api.delete(f"/api/pcs/{pc.id}").status_code == 204
    assert async_to_sync(layer.receive)(channel) == {"type": "pc.revoked"}
    assert not PC.objects.exists()


def test_pins(admin_api):
    created = admin_api.post("/api/pins", {"multi_use": True, "minutes": 60}, format="json")
    assert created.status_code == 201
    pin = created.json()
    assert len(pin["pin"]) == 6 and pin["multi_use"] is True
    assert [p["id"] for p in admin_api.get("/api/pins").json()] == [pin["id"]]
    assert admin_api.delete(f"/api/pins/{pin['id']}").status_code == 204
    assert admin_api.get("/api/pins").json() == []
    assert RegistrationPin.objects.get(id=pin["id"]).revoked is True


def test_pin_minutes_must_be_allowed(admin_api):
    response = admin_api.post("/api/pins", {"multi_use": False, "minutes": 30}, format="json")
    assert response.status_code == 400
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `uv run pytest tests/test_labs_api.py -v`
Expected: FAIL (404)

- [ ] **Step 3: 구현**

`server/labs/serializers.py`:

```python
from rest_framework import serializers

from labs.models import PC, RegistrationPin, Room

MAX_SIDE = 20


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ["id", "name", "rows", "cols", "aisle_after", "sort_order"]

    def validate(self, attrs: dict) -> dict:
        current = self.instance
        rows = attrs.get("rows", current.rows if current else 5)
        cols = attrs.get("cols", current.cols if current else 8)
        aisle = attrs.get("aisle_after", current.aisle_after if current else None)
        errors = {}
        if not 1 <= rows <= MAX_SIDE:
            errors["rows"] = [f"1~{MAX_SIDE} 사이로 입력하세요."]
        if not 1 <= cols <= MAX_SIDE:
            errors["cols"] = [f"1~{MAX_SIDE} 사이로 입력하세요."]
        if aisle is not None and not 1 <= aisle < cols:
            errors["aisle_after"] = ["1 이상, 열 수보다 작게 입력하세요."]
        if errors:
            raise serializers.ValidationError(errors)
        return attrs


class SeatSerializer(serializers.Serializer):
    row = serializers.IntegerField(min_value=0)
    col = serializers.IntegerField(min_value=0)
    pc = serializers.PrimaryKeyRelatedField(queryset=PC.objects.all())


class SeatsSerializer(serializers.Serializer):
    seats = SeatSerializer(many=True)

    def validate_seats(self, seats: list[dict]) -> list[dict]:
        room: Room = self.context["room"]
        positions: set[tuple[int, int]] = set()
        pcs: set[int] = set()
        for entry in seats:
            position = (entry["row"], entry["col"])
            if entry["row"] >= room.rows or entry["col"] >= room.cols:
                raise serializers.ValidationError("실습실 크기를 벗어난 자리가 있습니다.")
            if position in positions:
                raise serializers.ValidationError("같은 자리에 두 PC를 배치할 수 없습니다.")
            if entry["pc"].id in pcs:
                raise serializers.ValidationError("같은 PC를 두 자리에 배치할 수 없습니다.")
            positions.add(position)
            pcs.add(entry["pc"].id)
        return seats


class PCSerializer(serializers.ModelSerializer):
    label = serializers.CharField(read_only=True)

    class Meta:
        model = PC
        fields = ["id", "hostname", "label", "room", "row", "col", "client_version", "specs", "registered_at"]


class PinSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegistrationPin
        fields = ["id", "pin", "multi_use", "expires_at", "used_count", "created_at"]


class PinCreateSerializer(serializers.Serializer):
    multi_use = serializers.BooleanField(default=False)
    minutes = serializers.ChoiceField(choices=[10, 60, 180])
```

`server/labs/views.py`:

```python
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import record
from labs.models import PC, RegistrationPin, Room
from labs.serializers import PCSerializer, PinCreateSerializer, PinSerializer, RoomSerializer, SeatsSerializer
from wcms.api import error_responses
from wcms.groups import pc_group


def room_changed(room_id: int) -> None:
    """좌석이나 실습실 정보가 바뀌었을 때 부른다. 실시간 알림은 live 앱이 연결한다."""


def unseat(queryset) -> None:
    queryset.update(room=None, row=None, col=None)


class RoomList(generics.ListCreateAPIView):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer

    def perform_create(self, serializer) -> None:
        room = serializer.save()
        record(self.request.user, "room.create", f"room:{room.id}", name=room.name)


class RoomDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer

    def perform_update(self, serializer) -> None:
        with transaction.atomic():
            room = serializer.save()
            unseat(PC.objects.filter(room=room, row__gte=room.rows) | PC.objects.filter(room=room, col__gte=room.cols))
        record(self.request.user, "room.update", f"room:{room.id}", **serializer.validated_data)
        room_changed(room.id)

    def perform_destroy(self, instance: Room) -> None:
        room_id = instance.id
        with transaction.atomic():
            unseat(PC.objects.filter(room=instance))
            instance.delete()
        record(self.request.user, "room.delete", f"room:{room_id}")
        room_changed(room_id)


def seats_payload(room: Room) -> dict:
    pcs = PC.objects.filter(room=room, row__isnull=False, col__isnull=False).order_by("row", "col")
    return {"seats": [{"row": pc.row, "col": pc.col, "pc": pc.id} for pc in pcs]}


class RoomSeats(APIView):
    @extend_schema(responses={200: SeatsSerializer})
    def get(self, request, pk: int):
        return Response(seats_payload(get_object_or_404(Room, pk=pk)))

    @extend_schema(request=SeatsSerializer, responses={200: SeatsSerializer, **error_responses(400)})
    def put(self, request, pk: int):
        room = get_object_or_404(Room, pk=pk)
        serializer = SeatsSerializer(data=request.data, context={"room": room})
        serializer.is_valid(raise_exception=True)
        seats = serializer.validated_data["seats"]
        moved_from = set(
            PC.objects.filter(id__in=[s["pc"].id for s in seats], room__isnull=False)
            .exclude(room=room)
            .values_list("room_id", flat=True)
        )
        with transaction.atomic():
            unseat(PC.objects.filter(room=room))
            unseat(PC.objects.filter(id__in=[s["pc"].id for s in seats]))
            for entry in seats:
                PC.objects.filter(pk=entry["pc"].id).update(room=room, row=entry["row"], col=entry["col"])
        record(request.user, "room.seats", f"room:{room.id}", count=len(seats))
        for room_id in {room.id, *moved_from}:
            room_changed(room_id)
        return Response(seats_payload(room))


class PCList(generics.ListAPIView):
    queryset = PC.objects.select_related("room")
    serializer_class = PCSerializer


class PCDetail(generics.DestroyAPIView):
    queryset = PC.objects.select_related("room")
    serializer_class = PCSerializer

    def perform_destroy(self, instance: PC) -> None:
        pc_id, room_id = instance.id, instance.room_id
        record(self.request.user, "pc.delete", f"pc:{pc_id}", hostname=instance.hostname)
        instance.delete()
        async_to_sync(get_channel_layer().group_send)(pc_group(pc_id), {"type": "pc.revoked"})
        if room_id is not None:
            room_changed(room_id)


class PinList(APIView):
    @extend_schema(responses={200: PinSerializer(many=True)})
    def get(self, request):
        return Response(PinSerializer(RegistrationPin.usable().order_by("-created_at"), many=True).data)

    @extend_schema(request=PinCreateSerializer, responses={201: PinSerializer, **error_responses(400)})
    def post(self, request):
        serializer = PinCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pin = RegistrationPin.issue(user=request.user, **serializer.validated_data)
        record(request.user, "pin.issue", f"pin:{pin.id}", multi_use=pin.multi_use)
        return Response(PinSerializer(pin).data, status=201)


class PinDetail(APIView):
    @extend_schema(responses={204: None, **error_responses(404)})
    def delete(self, request, pk: int):
        pin = get_object_or_404(RegistrationPin, pk=pk)
        pin.revoked = True
        pin.save(update_fields=["revoked"])
        record(request.user, "pin.revoke", f"pin:{pin.id}")
        return Response(status=204)
```

`server/labs/urls.py`:

```python
from django.urls import path

from labs import views

urlpatterns = [
    path("rooms", views.RoomList.as_view()),
    path("rooms/<int:pk>", views.RoomDetail.as_view()),
    path("rooms/<int:pk>/seats", views.RoomSeats.as_view()),
    path("pcs", views.PCList.as_view()),
    path("pcs/<int:pk>", views.PCDetail.as_view()),
    path("pins", views.PinList.as_view()),
    path("pins/<int:pk>", views.PinDetail.as_view()),
]
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `uv run pytest -v`
Expected: 모두 통과

- [ ] **Step 5: Commit**

```bash
git add server/labs server/tests/test_labs_api.py
git commit -m "feat(server): room, seat, PC and PIN management API"
```

---

### Task 9: 클라이언트 프로토콜 문서와 예시 (`protocol/`)

C++ 클라이언트(계획 05)와 서버가 같이 지키는 계약이다. 코드보다 먼저 만든다.

**Files:**
- Delete: `docs/protocol.md` (계획 1 문서)
- Create: `protocol/README.md`, `protocol/examples/register_request.json`, `register_response.json`, `hello.json`, `status.json`, `ping.json`, `pong.json`, `error_bad_json.json`, `error_unknown_type.json`, `error_binary_not_supported.json`
- Modify: `CLAUDE.md` (프로토콜 경로)

**Interfaces:**
- Produces: 프로토콜 v1 규칙 (Task 10~12가 이대로 구현한다)
  - close code: `4400` hello가 첫 메시지가 아님, `4406` 지원하지 않는 프로토콜 버전, `4409` 같은 PC의 새 연결로 교체됨, `4410` 토큰 무효(재등록 또는 PC 삭제)
  - status 최소 간격 5초 (더 자주 오면 서버가 버림)
  - 바이너리 프레임 헤더 형식 (계획 06에서 활성화, 지금은 `binary_not_supported` 오류)

- [ ] **Step 1: 예시 파일 작성**

`protocol/examples/register_request.json`:

```json
{
  "pin": "123456",
  "hostname": "LAB301-13",
  "machine_guid": "3f2a9c4e-1b7d-4e8a-9c2f-5d6e7f8a9b0c",
  "specs": {"cpu": "Intel Core i5-12400", "ram_gb": 16, "os": "Windows 11 Pro 24H2"},
  "version": "2026.1"
}
```

`protocol/examples/register_response.json`:

```json
{"pc_id": 13, "token": "S3cr3tT0kenS3cr3tT0kenS3cr3tT0kenS3cr3tT0k"}
```

`protocol/examples/hello.json`:

```json
{"type": "hello", "proto": 1, "version": "2026.1"}
```

`protocol/examples/status.json`:

```json
{
  "type": "status",
  "cpu": 12.5,
  "mem_used": 8123456789,
  "mem_total": 17179869184,
  "disk_used": 246000000000,
  "disk_total": 512000000000,
  "user": "Student",
  "session": "active",
  "foreground": {"process": "chrome.exe", "title": "자료구조 3주차 - Google Docs - Chrome"}
}
```

`protocol/examples/ping.json`:

```json
{"type": "ping"}
```

`protocol/examples/pong.json`:

```json
{"type": "pong"}
```

`protocol/examples/error_bad_json.json`:

```json
{"type": "error", "error": "bad_json"}
```

`protocol/examples/error_unknown_type.json`:

```json
{"type": "error", "error": "unknown_type"}
```

`protocol/examples/error_binary_not_supported.json`:

```json
{"type": "error", "error": "binary_not_supported"}
```

- [ ] **Step 2: protocol/README.md 작성**

`protocol/README.md`:

````markdown
# 클라이언트-서버 프로토콜 v1

실습실 PC의 클라이언트가 서버와 주고받는 형식이다. 메시지 예시는 `examples/`에 있고, 서버 테스트와 클라이언트 테스트가 같은 파일로 검증한다.

클라이언트는 학내망에서 서버 내부 주소로 직접 접속한다 (`https://<내부 주소>`). 아래 경로는 그 주소 기준이다.

## 1. 등록

`POST /client/register`, `Content-Type: application/json` — 예시 `examples/register_request.json`

| 필드 | 규칙 |
|---|---|
| pin | 숫자 6자리 |
| hostname | 1~64자 |
| machine_guid | 1~64자 (`HKLM\SOFTWARE\Microsoft\Cryptography\MachineGuid`). 같은 값으로 다시 등록하면 같은 PC로 보고 자리를 유지한다 |
| specs | 객체, JSON으로 16KB 이하 |
| version | 20자 이하, 생략 가능 |

| 응답 | 본문 |
|---|---|
| 201 | `{"pc_id", "token"}` (`examples/register_response.json`). 토큰은 다시 받을 수 없으므로 저장한다 |
| 400 | `{"error": "invalid" \| "parse_error", "detail", "fields"?}` |
| 403 | `{"error": "invalid_pin", "detail"}` |
| 429 | `{"error": "too_many_attempts", "detail"}` — 같은 IP에서 PIN 실패 10회면 10분 차단 |

다시 등록하면 토큰이 바뀐다. 이전 토큰은 즉시 무효가 되고, 이전 토큰으로 열려 있던 연결은 close code `4410`으로 닫힌다.

## 2. WebSocket 연결

`GET /client/ws`, 헤더 `Authorization: Bearer <token>`

- 토큰이 없거나 틀리면 핸드셰이크가 HTTP 403으로 거절된다 → 다시 등록해야 한다.
- 첫 메시지는 반드시 `hello`다 (`examples/hello.json`). `proto`는 이 문서의 버전 `1`.
- 연결 상태가 곧 온라인/오프라인이다.
- 재접속: 대기 시간은 1초에서 시작해 두 배씩, 최대 60초. 매번 0~1초 무작위 지연을 더한다. 연결에 성공하면 1초로 되돌린다.
- ping은 20~30초 간격으로 보낸다. 상태 보고와 별개다.

| close code | 의미 | 클라이언트 동작 |
|---|---|---|
| 4400 | 첫 메시지가 hello가 아님 | 버그. 재접속 후 hello부터 |
| 4406 | 지원하지 않는 `proto` | 재접속하지 않는다. 자동 업데이트를 기다린다 (업데이트 경로는 프로토콜 버전과 무관하게 동작) |
| 4409 | 같은 PC의 새 연결로 교체됨 | 인증 실패가 아니다. 백오프 후 재접속 |
| 4410 | 토큰 무효 (재등록되었거나 PC가 삭제됨) | 재접속하지 않는다. 다시 등록이 필요 |

## 3. 클라이언트 → 서버 (텍스트 프레임, JSON)

| type | 예시 | 규칙 |
|---|---|---|
| hello | `hello.json` | 연결 직후 한 번. `proto`(정수), `version`(문자열, 20자) |
| status | `status.json` | 10초마다. 5초보다 자주 오면 서버가 버린다 |
| ping | `ping.json` | 서버가 `pong`으로 답한다. 온라인 판정에는 쓰지 않는다 |

status 필드:

| 필드 | 규칙 |
|---|---|
| cpu | 0~100 숫자 (%) |
| mem_used, mem_total, disk_used, disk_total | 0 이상 숫자 (바이트), 2^53 이하 |
| user | 로그인한 사용자 이름, 문자열, 최대 64자 |
| session | `active`(로그인, 잠금 아님) / `locked` / `none`(로그인 없음). 그 밖의 값은 `none` |
| foreground | 앞에 떠 있는 창 `{"process", "title"}`. 문자열, 각각 최대 128자 / 256자 |

규칙에 맞지 않는 값과 목록에 없는 필드는 서버가 버린다. 숫자는 유한한 값만 받는다 (`NaN`, `Infinity` 불가).

## 4. 서버 → 클라이언트 (텍스트 프레임, JSON)

| 메시지 | 의미 |
|---|---|
| `{"type": "pong"}` | ping 응답 |
| `{"type": "error", "error": "bad_json"}` | JSON이 아니거나 객체가 아님 |
| `{"type": "error", "error": "unknown_type"}` | 모르는 type |
| `{"type": "error", "error": "binary_not_supported"}` | 아직 바이너리 프레임을 받지 않음 (계획 06 전) |

명령 메시지는 계획 04에서 추가한다.

## 5. 바이너리 프레임 (계획 06에서 활성화)

화면 데이터는 바이너리 프레임으로 보낸다. 모든 정수는 리틀 엔디언.

| 바이트 | 내용 |
|---|---|
| 0 | 종류: 1 = 썸네일(WebP), 2 = 크게 보기(H.264 Annex B), 3 = 스크린샷(PNG) |
| 1 | 플래그: bit0 = 키프레임 (H.264일 때) |
| 2-5 | 스트림 id (uint32) |
| 6-9 | seq (uint32) |
| 10-17 | 캡처 시각 (uint64, Unix 밀리초) |
| 18~ | 본문 |
````

- [ ] **Step 3: 이전 문서 삭제와 CLAUDE.md 갱신**

```bash
git rm -q docs/protocol.md
```

`CLAUDE.md` 전체:

```markdown
# WCMS

설계: docs/superpowers/specs/2026-10-24-wcms-2026-1-design.md
계획: docs/superpowers/plans/
클라이언트 프로토콜: protocol/README.md (예시: protocol/examples/)

- server/: Django + DRF + Channels. 명령은 server/ 에서 `uv run ...`. 패키지 추가는 `uv add` (pip 직접 사용 금지)
- frontend/: SvelteKit SPA (계획 03)
- 테스트: `cd server && uv run pytest`
- 버전: 루트 VERSION 파일 (형식 2026.1)
- 학생이 조작할 수 있는 값(창 제목, 프로세스 이름, 사용자 이름, 호스트 이름, 명령 출력)은 신뢰하지 않는다. 비로그인 응답에는 좌석 라벨과 켜짐/꺼짐만
```

- [ ] **Step 4: JSON 형식 확인**

Run: `for f in protocol/examples/*.json; do python3 -m json.tool "$f" > /dev/null || echo "BAD $f"; done`
Expected: 출력 없음

- [ ] **Step 5: Commit**

```bash
git add -A protocol docs/protocol.md CLAUDE.md
git commit -m "docs: client protocol v1 with message examples"
```

---

### Task 10: 클라이언트 등록, 상태 저장소, status 정리

**Files:**
- Create: `server/agent/protocol.py`, `server/agent/state.py`, `server/agent/views.py`
- Modify: `server/agent/urls.py`
- Test: `server/tests/test_agent_register.py`, `server/tests/test_agent_state.py`

**Interfaces:**
- Consumes: `PC.register`, `RegistrationPin.consume`, `FailureLimiter`, `client_ip`, `ApiError`, `pc_group`, `protocol/examples/*.json`
- Produces:
  - `agent.protocol`: `PROTO_VERSION = 1`, `CLOSE_HELLO_REQUIRED = 4400`, `CLOSE_UNSUPPORTED_PROTO = 4406`, `CLOSE_SUPERSEDED = 4409`, `CLOSE_REVOKED = 4410`, `STATUS_MIN_INTERVAL = 5.0`, `bearer_token(scope) -> str | None`, `clean_status(message: dict) -> dict`
  - `agent.state` (Django 캐시, 프로세스 시작마다 바뀌는 `BOOT_ID`로 재시작 전 상태를 오프라인 처리):
    - `get_state(pc_id) -> {"online": bool, "status": dict}`
    - `get_states(pc_ids: list[int]) -> dict[int, dict]`
    - `mark_connected(pc_id, channel) -> None`
    - `mark_disconnected(pc_id, channel) -> bool` (그 channel이 현재 연결일 때만 오프라인으로, 바뀌었으면 True)
    - `save_status(pc_id, channel, status) -> bool` (그 channel이 현재 연결일 때만)
  - `POST /client/register` (인증 없음, OpenAPI 제외). 재등록이면 이전 연결에 `{"type": "pc.revoked"}`

- [ ] **Step 1: 실패하는 테스트 작성**

`server/tests/test_agent_state.py`:

```python
import json
from pathlib import Path

import pytest

from agent import state
from agent.protocol import bearer_token, clean_status

EXAMPLES = Path(__file__).resolve().parents[2] / "protocol" / "examples"


def example(name: str) -> dict:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def test_status_example_survives_cleaning_unchanged():
    message = example("status.json")
    expected = {k: v for k, v in message.items() if k != "type"}
    assert clean_status(message) == expected


@pytest.mark.parametrize("value", [float("inf"), float("nan"), -1, True, "12", 101])
def test_bad_cpu_dropped(value):
    assert "cpu" not in clean_status({"cpu": value})


def test_strings_only_and_truncated():
    cleaned = clean_status(
        {"user": "u" * 100, "session": "weird", "foreground": {"process": {"x": 1}, "title": "t" * 500}}
    )
    assert len(cleaned["user"]) == 64
    assert cleaned["session"] == "none"
    assert cleaned["foreground"] == {"process": "", "title": "t" * 256}


def test_non_string_user_dropped():
    assert "user" not in clean_status({"user": 5})


def test_bearer_token():
    assert bearer_token({"headers": [(b"authorization", b"Bearer abc")]}) == "abc"
    assert bearer_token({"headers": [(b"authorization", b"Basic abc")]}) is None
    assert bearer_token({"headers": []}) is None


def test_state_lifecycle():
    assert state.get_state(1) == {"online": False, "status": {}}
    state.mark_connected(1, "chan-a")
    assert state.get_state(1)["online"] is True
    assert state.save_status(1, "chan-b", {"cpu": 1}) is False
    assert state.save_status(1, "chan-a", {"cpu": 1}) is True
    assert state.get_state(1)["status"] == {"cpu": 1}
    assert state.mark_disconnected(1, "chan-b") is False
    assert state.mark_disconnected(1, "chan-a") is True
    assert state.get_state(1) == {"online": False, "status": {}}


def test_state_from_previous_boot_is_offline(monkeypatch):
    state.mark_connected(2, "chan")
    monkeypatch.setattr(state, "BOOT_ID", "another-boot")
    assert state.get_state(2)["online"] is False


def test_get_states():
    state.mark_connected(3, "c")
    states = state.get_states([3, 4])
    assert states[3]["online"] is True and states[4]["online"] is False
```

`server/tests/test_agent_register.py`:

```python
import json
from pathlib import Path

import pytest
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.test import override_settings

from labs.models import PC, RegistrationPin
from wcms.groups import pc_group

pytestmark = pytest.mark.django_db
EXAMPLES = Path(__file__).resolve().parents[2] / "protocol" / "examples"


def body(pin: str, **override) -> dict:
    data = json.loads((EXAMPLES / "register_request.json").read_text(encoding="utf-8"))
    data["pin"] = pin
    data.update(override)
    return data


def new_pin() -> str:
    return RegistrationPin.issue(user=None, multi_use=True, minutes=10).pin


def post(api, data, **extra):
    return api.post("/client/register", data, format="json", **extra)


def test_register_example_succeeds(api):
    response = post(api, body(new_pin()))
    assert response.status_code == 201
    data = response.json()
    expected_keys = json.loads((EXAMPLES / "register_response.json").read_text()).keys()
    assert data.keys() == expected_keys
    assert PC.from_token(data["token"]).id == data["pc_id"]


def test_invalid_pin(api):
    response = post(api, body("999999"))
    assert response.status_code == 403
    assert response.json()["error"] == "invalid_pin"


@pytest.mark.parametrize(
    "override", [{"pin": "12ab56"}, {"hostname": ""}, {"hostname": "x" * 65}, {"specs": [1]}, {"specs": {"x": "a" * 20000}}]
)
def test_invalid_fields(api, override):
    response = post(api, body(new_pin(), **override))
    assert response.status_code == 400
    assert response.json()["error"] == "invalid"


def test_lockout_after_ten_wrong_pins(api):
    for _ in range(10):
        post(api, body("000000"))
    response = post(api, body(new_pin()))
    assert response.status_code == 429


def test_reregister_revokes_old_connection(api):
    first = post(api, body(new_pin())).json()
    layer = get_channel_layer()
    channel = async_to_sync(layer.new_channel)()
    async_to_sync(layer.group_add)(pc_group(first["pc_id"]), channel)
    second = post(api, body(new_pin())).json()
    assert second["pc_id"] == first["pc_id"]
    assert async_to_sync(layer.receive)(channel) == {"type": "pc.revoked"}


def test_requires_internal_path_when_enabled(api):
    with override_settings(WCMS_REQUIRE_INTERNAL=True):
        assert post(api, body(new_pin())).status_code == 404
        assert post(api, body(new_pin()), HTTP_X_WCMS_VIA="internal").status_code == 201


def test_get_not_allowed(api):
    assert api.get("/client/register").status_code == 405
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `uv run pytest tests/test_agent_state.py tests/test_agent_register.py -v`
Expected: FAIL, `ModuleNotFoundError`

- [ ] **Step 3: agent/protocol.py**

`server/agent/protocol.py`:

```python
import math

PROTO_VERSION = 1
CLOSE_HELLO_REQUIRED = 4400
CLOSE_UNSUPPORTED_PROTO = 4406
CLOSE_SUPERSEDED = 4409
CLOSE_REVOKED = 4410
STATUS_MIN_INTERVAL = 5.0

NUMBER_LIMITS = {
    "cpu": 100,
    "mem_used": 2**53,
    "mem_total": 2**53,
    "disk_used": 2**53,
    "disk_total": 2**53,
}
SESSIONS = ("active", "locked", "none")


def bearer_token(scope: dict) -> str | None:
    for name, value in scope.get("headers", []):
        if name == b"authorization":
            text = value.decode("latin-1")
            if text.startswith("Bearer "):
                return text[len("Bearer "):].strip() or None
    return None


def _number(value, maximum: float) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and 0 <= value <= maximum
    )


def _text(value, limit: int) -> str | None:
    return value[:limit] if isinstance(value, str) else None


def clean_status(message: dict) -> dict:
    status: dict = {key: message[key] for key, limit in NUMBER_LIMITS.items() if _number(message.get(key), limit)}
    user = _text(message.get("user"), 64)
    if user is not None:
        status["user"] = user
    session = message.get("session")
    status["session"] = session if session in SESSIONS else "none"
    foreground = message.get("foreground")
    if isinstance(foreground, dict):
        process = _text(foreground.get("process"), 128)
        title = _text(foreground.get("title"), 256)
        if process is not None or title is not None:
            status["foreground"] = {"process": process or "", "title": title or ""}
    return status
```

- [ ] **Step 4: agent/state.py**

`server/agent/state.py`:

```python
import time
import uuid

from django.core.cache import cache

BOOT_ID = uuid.uuid4().hex
TTL = 24 * 3600
OFFLINE = {"online": False, "status": {}}


def _key(pc_id: int) -> str:
    return f"pcstate:{pc_id}"


def _current(raw: dict | None) -> dict | None:
    if not raw or raw.get("boot") != BOOT_ID:
        return None
    return raw


def _public(raw: dict | None) -> dict:
    raw = _current(raw)
    if raw is None or not raw.get("online"):
        return dict(OFFLINE)
    return {"online": True, "status": raw.get("status", {})}


def get_state(pc_id: int) -> dict:
    return _public(cache.get(_key(pc_id)))


def get_states(pc_ids: list[int]) -> dict[int, dict]:
    found = cache.get_many([_key(pc_id) for pc_id in pc_ids])
    return {pc_id: _public(found.get(_key(pc_id))) for pc_id in pc_ids}


def mark_connected(pc_id: int, channel: str) -> None:
    cache.set(
        _key(pc_id),
        {"boot": BOOT_ID, "online": True, "connection": channel, "status": {}, "since": time.time()},
        TTL,
    )


def mark_disconnected(pc_id: int, channel: str) -> bool:
    raw = _current(cache.get(_key(pc_id)))
    if raw is None or raw.get("connection") != channel:
        return False
    cache.set(_key(pc_id), {**raw, "online": False, "connection": "", "status": {}}, TTL)
    return True


def save_status(pc_id: int, channel: str, status: dict) -> bool:
    raw = _current(cache.get(_key(pc_id)))
    if raw is None or raw.get("connection") != channel:
        return False
    cache.set(_key(pc_id), {**raw, "status": status, "updated": time.time()}, TTL)
    return True
```

- [ ] **Step 5: 등록 뷰**

`server/agent/views.py`:

```python
import json

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from labs.models import PC, RegistrationPin
from wcms.api import ApiError
from wcms.groups import pc_group
from wcms.limits import FailureLimiter
from wcms.net import client_ip

MAX_SPECS_BYTES = 16384
pin_failures = FailureLimiter("register-ip", limit=10, window=600)


class RegisterSerializer(serializers.Serializer):
    pin = serializers.RegexField(r"^\d{6}$")
    hostname = serializers.CharField(max_length=64)
    machine_guid = serializers.CharField(max_length=64)
    specs = serializers.JSONField(required=False, default=dict)
    version = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")

    def validate_specs(self, value) -> dict:
        if not isinstance(value, dict):
            raise serializers.ValidationError("객체여야 합니다.")
        if len(json.dumps(value)) > MAX_SPECS_BYTES:
            raise serializers.ValidationError("너무 큽니다.")
        return value


@extend_schema(exclude=True)
class RegisterView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]

    def post(self, request):
        ip = client_ip(request)
        if pin_failures.blocked(ip):
            raise ApiError("too_many_attempts", "잠시 후 다시 시도하세요.", 429)
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if not RegistrationPin.consume(data["pin"]):
            pin_failures.record(ip)
            raise ApiError("invalid_pin", "PIN이 올바르지 않거나 만료되었습니다.", 403)
        existed = PC.objects.filter(machine_guid=data["machine_guid"]).exists()
        pc, token = PC.register(
            hostname=data["hostname"], machine_guid=data["machine_guid"], specs=data["specs"], version=data["version"]
        )
        if existed:
            async_to_sync(get_channel_layer().group_send)(pc_group(pc.id), {"type": "pc.revoked"})
        return Response({"pc_id": pc.id, "token": token}, status=201)
```

`server/agent/urls.py`:

```python
from django.urls import path

from agent.views import RegisterView

urlpatterns = [
    path("register", RegisterView.as_view()),
]
```

- [ ] **Step 6: 테스트 통과 확인**

Run: `uv run pytest -v`
Expected: 모두 통과

- [ ] **Step 7: Commit**

```bash
git add server/agent server/tests/test_agent_state.py server/tests/test_agent_register.py
git commit -m "feat(server): client registration, live state store, status cleaning"
```

---

### Task 11: 실시간 payload, 스냅샷, 발행, 공개 API

**Files:**
- Create: `server/live/serializers.py`, `server/live/snapshots.py`, `server/live/publish.py`, `server/live/views.py`
- Modify: `server/live/urls.py`, `server/labs/views.py` (`room_changed` 구현을 live로 연결)
- Test: `server/tests/test_live_publish.py`, `server/tests/test_public_api.py`

**Interfaces:**
- Consumes: `PC`, `Room`, `agent.state.get_state/get_states`, `wcms.groups`
- Produces:
  - `live.serializers.LivePCSerializer`: `{"id", "hostname", "label", "room", "row", "col", "version", "online", "session", "user", "foreground": {"process", "title"} | null, "cpu", "mem_used", "mem_total", "disk_used", "disk_total"}` (숫자는 null 가능)
  - `live.serializers.PublicSeatSerializer`: `{"row", "col", "label", "online"}` — 이것 말고는 비로그인에게 아무것도 주지 않는다
  - `live.serializers.PublicRoomSerializer`: `{"id", "name", "rows", "cols", "aisle_after"}`
  - `live.snapshots`: `live_pc(pc, state) -> dict`, `public_seat(pc, state) -> dict`, `room_snapshot(room_id) -> list[dict] | None`, `public_room_snapshot(room_id) -> list[dict] | None`, `pc_snapshot(pc_id) -> dict | None` (방에는 자리 있는 PC만)
  - `live.publish`: `async publish_pc(pc_id: int, *, online_changed: bool)` → 채널 메시지
    - `pc_watch_group`에 `{"type": "live.pc", "topic": "pc:<id>", "pc": LivePC}`
    - 자리 있으면 `room_group`에 `{"type": "live.pc", "topic": "room:<room>", "pc": LivePC}`
    - 자리 있고 `online_changed`면 `room_public_group`에 `{"type": "live.seat", "topic": "room:<room>:public", "seat": PublicSeat}`
  - `live.publish.room_changed(room_id)` (동기) → `room_group`, `room_public_group`에 `{"type": "live.room_changed", "topic": ...}`
  - REST: `GET /api/public/rooms` (누구나), `GET /api/public/rooms/<id>` (누구나) → `{"room": PublicRoom, "seats": [PublicSeat]}`, `GET /api/rooms/<id>/pcs` (관리자) → `[LivePC]`, `GET /api/pcs/<id>/live` (관리자) → `LivePC`

- [ ] **Step 1: 실패하는 테스트 작성**

`server/tests/test_live_publish.py`:

```python
import pytest
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from agent import state
from labs.models import PC, Room
from live.publish import publish_pc, room_changed
from live.snapshots import live_pc, public_room_snapshot, public_seat, room_snapshot
from wcms.groups import pc_watch_group, room_group, room_public_group

pytestmark = pytest.mark.django_db(transaction=True)
PUBLIC_KEYS = {"row", "col", "label", "online"}


def seated_pc(room: Room, n: int = 1) -> PC:
    pc, _ = PC.register(hostname=f"LAB-HOST-{n}", machine_guid=f"g{n}", specs={"cpu": "i5"}, version="2026.1")
    pc.room, pc.row, pc.col = room, 0, n - 1
    pc.save()
    return pc


def listen(group: str) -> str:
    layer = get_channel_layer()
    channel = async_to_sync(layer.new_channel)()
    async_to_sync(layer.group_add)(group, channel)
    return channel


def receive(channel: str) -> dict:
    return async_to_sync(get_channel_layer().receive)(channel)


def test_payload_shapes():
    room = Room.objects.create(name="301", rows=2, cols=4)
    pc = seated_pc(room)
    st = {"online": True, "status": {"user": "Student", "session": "active", "cpu": 3.0}}
    admin = live_pc(pc, st)
    assert admin["hostname"] == "LAB-HOST-1" and admin["user"] == "Student" and admin["label"] == "301-01"
    public = public_seat(pc, st)
    assert set(public) == PUBLIC_KEYS
    assert public == {"row": 0, "col": 0, "label": "301-01", "online": True}


def test_offline_hides_last_status():
    room = Room.objects.create(name="301", rows=2, cols=4)
    pc = seated_pc(room)
    admin = live_pc(pc, {"online": False, "status": {}})
    assert admin["online"] is False and admin["user"] == "" and admin["cpu"] is None


def test_snapshots_only_include_seated():
    room = Room.objects.create(name="301", rows=2, cols=4)
    seated = seated_pc(room)
    PC.register(hostname="UNSEATED", machine_guid="gx", specs={}, version="")
    assert [p["id"] for p in room_snapshot(room.id)] == [seated.id]
    seats = public_room_snapshot(room.id)
    assert len(seats) == 1 and set(seats[0]) == PUBLIC_KEYS
    assert room_snapshot(9999) is None


def test_publish_pc_routes_messages():
    room = Room.objects.create(name="301", rows=2, cols=4)
    pc = seated_pc(room)
    state.mark_connected(pc.id, "c")
    watch, admin_room, public_room = listen(pc_watch_group(pc.id)), listen(room_group(room.id)), listen(room_public_group(room.id))

    async_to_sync(publish_pc)(pc.id, online_changed=False)
    assert receive(watch)["topic"] == f"pc:{pc.id}"
    message = receive(admin_room)
    assert message["type"] == "live.pc" and message["pc"]["online"] is True

    async_to_sync(publish_pc)(pc.id, online_changed=True)
    receive(watch)
    receive(admin_room)
    seat = receive(public_room)
    assert seat["type"] == "live.seat" and seat["topic"] == f"room:{room.id}:public"
    assert set(seat["seat"]) == PUBLIC_KEYS


def test_room_changed_notifies_both_groups():
    admin_room, public_room = listen(room_group(5)), listen(room_public_group(5))
    room_changed(5)
    assert receive(admin_room) == {"type": "live.room_changed", "topic": "room:5"}
    assert receive(public_room) == {"type": "live.room_changed", "topic": "room:5:public"}
```

`server/tests/test_public_api.py`:

```python
import pytest
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from agent import state
from labs.models import PC, Room
from wcms.groups import room_group

pytestmark = pytest.mark.django_db


@pytest.fixture
def room_with_pc():
    room = Room.objects.create(name="301", rows=2, cols=4, aisle_after=2)
    pc, _ = PC.register(hostname="LAB-HOST-SECRET", machine_guid="g1", specs={"cpu": "i5"}, version="2026.1")
    pc.room, pc.row, pc.col = room, 0, 1
    pc.save()
    state.mark_connected(pc.id, "c")
    state.save_status(pc.id, "c", {"user": "StudentName", "session": "active"})
    return room, pc


def test_public_rooms(api, room_with_pc):
    room, _ = room_with_pc
    assert api.get("/api/public/rooms").json() == [
        {"id": room.id, "name": "301", "rows": 2, "cols": 4, "aisle_after": 2}
    ]


def test_public_room_detail_hides_everything_else(api, room_with_pc):
    room, _ = room_with_pc
    response = api.get(f"/api/public/rooms/{room.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["seats"] == [{"row": 0, "col": 1, "label": "301-02", "online": True}]
    text = response.content.decode()
    assert "LAB-HOST-SECRET" not in text and "StudentName" not in text and "i5" not in text


def test_public_unknown_room(api):
    assert api.get("/api/public/rooms/999").status_code == 404


def test_admin_room_pcs(admin_api, api, room_with_pc):
    room, pc = room_with_pc
    assert api.get(f"/api/rooms/{room.id}/pcs").status_code == 401
    rows = admin_api.get(f"/api/rooms/{room.id}/pcs").json()
    assert rows[0]["user"] == "StudentName" and rows[0]["hostname"] == "LAB-HOST-SECRET"
    assert admin_api.get(f"/api/pcs/{pc.id}/live").json()["id"] == pc.id


def test_seat_change_publishes_room_changed(admin_api, room_with_pc):
    room, pc = room_with_pc
    layer = get_channel_layer()
    channel = async_to_sync(layer.new_channel)()
    async_to_sync(layer.group_add)(room_group(room.id), channel)
    admin_api.put(f"/api/rooms/{room.id}/seats", {"seats": []}, format="json")
    assert async_to_sync(layer.receive)(channel) == {"type": "live.room_changed", "topic": f"room:{room.id}"}
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `uv run pytest tests/test_live_publish.py tests/test_public_api.py -v`
Expected: FAIL, `ModuleNotFoundError`

- [ ] **Step 3: serializers, snapshots, publish**

`server/live/serializers.py`:

```python
from rest_framework import serializers


class ForegroundSerializer(serializers.Serializer):
    process = serializers.CharField(allow_blank=True)
    title = serializers.CharField(allow_blank=True)


class LivePCSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    hostname = serializers.CharField()
    label = serializers.CharField()
    room = serializers.IntegerField(allow_null=True)
    row = serializers.IntegerField(allow_null=True)
    col = serializers.IntegerField(allow_null=True)
    version = serializers.CharField(allow_blank=True)
    online = serializers.BooleanField()
    session = serializers.ChoiceField(choices=["active", "locked", "none"])
    user = serializers.CharField(allow_blank=True)
    foreground = ForegroundSerializer(allow_null=True)
    cpu = serializers.FloatField(allow_null=True)
    mem_used = serializers.FloatField(allow_null=True)
    mem_total = serializers.FloatField(allow_null=True)
    disk_used = serializers.FloatField(allow_null=True)
    disk_total = serializers.FloatField(allow_null=True)


class PublicSeatSerializer(serializers.Serializer):
    row = serializers.IntegerField()
    col = serializers.IntegerField()
    label = serializers.CharField()
    online = serializers.BooleanField()


class PublicRoomSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    rows = serializers.IntegerField()
    cols = serializers.IntegerField()
    aisle_after = serializers.IntegerField(allow_null=True)


class PublicRoomDetailSerializer(serializers.Serializer):
    room = PublicRoomSerializer()
    seats = PublicSeatSerializer(many=True)
```

`server/live/snapshots.py`:

```python
from agent import state
from labs.models import PC, Room
from live.serializers import LivePCSerializer, PublicSeatSerializer

NUMBERS = ("cpu", "mem_used", "mem_total", "disk_used", "disk_total")


def live_pc(pc: PC, st: dict) -> dict:
    status = st.get("status", {}) if st.get("online") else {}
    data = {
        "id": pc.id,
        "hostname": pc.hostname,
        "label": pc.label,
        "room": pc.room_id,
        "row": pc.row,
        "col": pc.col,
        "version": pc.client_version,
        "online": bool(st.get("online")),
        "session": status.get("session", "none"),
        "user": status.get("user", ""),
        "foreground": status.get("foreground"),
        **{key: status.get(key) for key in NUMBERS},
    }
    return LivePCSerializer(data).data


def public_seat(pc: PC, st: dict) -> dict:
    return PublicSeatSerializer({"row": pc.row, "col": pc.col, "label": pc.label, "online": bool(st.get("online"))}).data


def _seated_in(room_id: int) -> list[PC]:
    return list(
        PC.objects.select_related("room")
        .filter(room_id=room_id, row__isnull=False, col__isnull=False)
        .order_by("row", "col")
    )


def room_snapshot(room_id: int) -> list[dict] | None:
    if not Room.objects.filter(pk=room_id).exists():
        return None
    pcs = _seated_in(room_id)
    states = state.get_states([pc.id for pc in pcs])
    return [live_pc(pc, states[pc.id]) for pc in pcs]


def public_room_snapshot(room_id: int) -> list[dict] | None:
    if not Room.objects.filter(pk=room_id).exists():
        return None
    pcs = _seated_in(room_id)
    states = state.get_states([pc.id for pc in pcs])
    return [public_seat(pc, states[pc.id]) for pc in pcs]


def pc_snapshot(pc_id: int) -> dict | None:
    pc = PC.objects.select_related("room").filter(pk=pc_id).first()
    if pc is None:
        return None
    return live_pc(pc, state.get_state(pc.id))
```

`server/live/publish.py`:

```python
from asgiref.sync import async_to_sync, sync_to_async
from channels.layers import get_channel_layer

from agent import state
from labs.models import PC
from live.snapshots import live_pc, public_seat
from wcms.groups import pc_watch_group, room_group, room_public_group


def _load(pc_id: int) -> tuple[PC | None, dict]:
    pc = PC.objects.select_related("room").filter(pk=pc_id).first()
    return pc, state.get_state(pc_id)


async def publish_pc(pc_id: int, *, online_changed: bool) -> None:
    pc, st = await sync_to_async(_load)(pc_id)
    if pc is None:
        return
    layer = get_channel_layer()
    payload = await sync_to_async(live_pc)(pc, st)
    await layer.group_send(pc_watch_group(pc.id), {"type": "live.pc", "topic": f"pc:{pc.id}", "pc": payload})
    if not pc.seated:
        return
    await layer.group_send(room_group(pc.room_id), {"type": "live.pc", "topic": f"room:{pc.room_id}", "pc": payload})
    if online_changed:
        seat = await sync_to_async(public_seat)(pc, st)
        await layer.group_send(
            room_public_group(pc.room_id), {"type": "live.seat", "topic": f"room:{pc.room_id}:public", "seat": seat}
        )


def room_changed(room_id: int) -> None:
    send = async_to_sync(get_channel_layer().group_send)
    send(room_group(room_id), {"type": "live.room_changed", "topic": f"room:{room_id}"})
    send(room_public_group(room_id), {"type": "live.room_changed", "topic": f"room:{room_id}:public"})
```

- [ ] **Step 4: REST 뷰와 URL**

`server/live/views.py`:

```python
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from labs.models import Room
from live.serializers import LivePCSerializer, PublicRoomDetailSerializer, PublicRoomSerializer
from live.snapshots import pc_snapshot, public_room_snapshot, room_snapshot
from wcms.api import ApiError, error_responses

ROOM_FIELDS = ("id", "name", "rows", "cols", "aisle_after")


def public_room(room: Room) -> dict:
    return {field: getattr(room, field) for field in ROOM_FIELDS}


class PublicRoomList(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses={200: PublicRoomSerializer(many=True)})
    def get(self, request):
        return Response([public_room(room) for room in Room.objects.all()])


class PublicRoomDetail(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses={200: PublicRoomDetailSerializer, **error_responses(404)})
    def get(self, request, pk: int):
        room = get_object_or_404(Room, pk=pk)
        return Response({"room": public_room(room), "seats": public_room_snapshot(room.id)})


class RoomLivePCs(APIView):
    @extend_schema(responses={200: LivePCSerializer(many=True), **error_responses(404)})
    def get(self, request, pk: int):
        pcs = room_snapshot(pk)
        if pcs is None:
            raise ApiError("not_found", "없는 실습실입니다.", 404)
        return Response(pcs)


class PCLive(APIView):
    @extend_schema(responses={200: LivePCSerializer, **error_responses(404)})
    def get(self, request, pk: int):
        pc = pc_snapshot(pk)
        if pc is None:
            raise ApiError("not_found", "없는 PC입니다.", 404)
        return Response(pc)
```

`server/live/urls.py`:

```python
from django.urls import path

from live import views

urlpatterns = [
    path("public/rooms", views.PublicRoomList.as_view()),
    path("public/rooms/<int:pk>", views.PublicRoomDetail.as_view()),
    path("rooms/<int:pk>/pcs", views.RoomLivePCs.as_view()),
    path("pcs/<int:pk>/live", views.PCLive.as_view()),
]
```

- [ ] **Step 5: labs의 room_changed를 live에 연결**

`server/labs/views.py`에서 아래 함수를

```python
def room_changed(room_id: int) -> None:
    """좌석이나 실습실 정보가 바뀌었을 때 부른다. 실시간 알림은 live 앱이 연결한다."""
```

삭제하고, import 부분에 다음 한 줄을 추가한다.

```python
from live.publish import room_changed
```

- [ ] **Step 6: 테스트 통과 확인**

Run: `uv run pytest -v`
Expected: 모두 통과

- [ ] **Step 7: Commit**

```bash
git add server/live server/labs/views.py server/tests/test_live_publish.py server/tests/test_public_api.py
git commit -m "feat(server): live payloads, snapshots, publishing and public room API"
```

---

### Task 12: 클라이언트 WebSocket (`/client/ws`)

**Files:**
- Create: `server/agent/consumers.py`
- Modify: `server/wcms/routing.py`
- Test: `server/tests/test_agent_ws.py`

**Interfaces:**
- Consumes: `agent.protocol`, `agent.state`, `PC.from_token`, `live.publish.publish_pc`, `wcms.net.is_internal_scope`, `wcms.groups.pc_group`, `protocol/examples/*.json`
- Produces: `AgentConsumer` at `/client/ws`, `protocol/README.md` 2~4절 그대로. 채널 메시지 `pc.superseded` → close 4409, `pc.revoked` → close 4410

- [ ] **Step 1: 실패하는 테스트 작성**

`server/tests/test_agent_ws.py`:

```python
import json
from pathlib import Path

import pytest
from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from django.test import override_settings

from agent import consumers, protocol, state
from labs.models import PC
from wcms.asgi import application
from wcms.groups import pc_group

pytestmark = pytest.mark.django_db(transaction=True)
EXAMPLES = Path(__file__).resolve().parents[2] / "protocol" / "examples"


@pytest.fixture(autouse=True)
def fresh_locks():
    # asyncio.Lock은 처음 경합한 이벤트 루프에 묶이므로 테스트마다 비운다
    consumers._locks.clear()


def example(name: str) -> dict:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


@database_sync_to_async
def make_pc() -> tuple[PC, str]:
    return PC.register(hostname="LAB-01", machine_guid="g1", specs={}, version="2026.1")


def connect(token: str | None, internal: bool = False) -> WebsocketCommunicator:
    headers = [(b"authorization", f"Bearer {token}".encode())] if token else []
    if internal:
        headers.append((b"x-wcms-via", b"internal"))
    return WebsocketCommunicator(application, "/client/ws", headers=headers)


async def open_with_hello(token: str) -> WebsocketCommunicator:
    ws = connect(token)
    connected, _ = await ws.connect()
    assert connected
    await ws.send_json_to(example("hello.json"))
    return ws


async def sync(ws: WebsocketCommunicator) -> None:
    await ws.send_json_to(example("ping.json"))
    assert await ws.receive_json_from() == example("pong.json")


async def current_state(pc_id: int) -> dict:
    return await sync_to_async(state.get_state)(pc_id)


@pytest.fixture(autouse=True)
def no_status_throttle(monkeypatch):
    monkeypatch.setattr(protocol, "STATUS_MIN_INTERVAL", 0.0)


async def test_rejects_missing_and_wrong_token():
    await make_pc()
    assert (await connect(None).connect())[0] is False
    assert (await connect("wrong").connect())[0] is False


async def test_rejects_non_internal_when_required():
    _, token = await make_pc()
    with override_settings(WCMS_REQUIRE_INTERNAL=True):
        assert (await connect(token).connect())[0] is False
        ws = connect(token, internal=True)
        assert (await ws.connect())[0] is True
        await ws.disconnect()


async def test_first_message_must_be_hello():
    _, token = await make_pc()
    ws = connect(token)
    await ws.connect()
    await ws.send_json_to(example("ping.json"))
    closed = await ws.receive_output(timeout=1)
    assert closed["type"] == "websocket.close" and closed["code"] == protocol.CLOSE_HELLO_REQUIRED


async def test_unsupported_proto():
    _, token = await make_pc()
    ws = connect(token)
    await ws.connect()
    await ws.send_json_to({"type": "hello", "proto": 99, "version": "x"})
    closed = await ws.receive_output(timeout=1)
    assert closed["code"] == protocol.CLOSE_UNSUPPORTED_PROTO


async def test_connect_status_disconnect():
    pc, token = await make_pc()
    ws = await open_with_hello(token)
    await sync(ws)
    assert (await current_state(pc.id))["online"] is True
    await ws.send_json_to(example("status.json"))
    await sync(ws)
    status = (await current_state(pc.id))["status"]
    assert status["user"] == "Student" and status["cpu"] == 12.5
    await ws.disconnect()
    assert (await current_state(pc.id))["online"] is False


async def test_hello_saves_version():
    pc, token = await make_pc()
    ws = connect(token)
    await ws.connect()
    await ws.send_json_to({"type": "hello", "proto": 1, "version": "2026.9"})
    await sync(ws)
    refreshed = await database_sync_to_async(PC.objects.get)(pk=pc.id)
    assert refreshed.client_version == "2026.9"
    await ws.disconnect()


async def test_status_too_frequent_is_dropped(monkeypatch):
    monkeypatch.setattr(protocol, "STATUS_MIN_INTERVAL", 60.0)
    pc, token = await make_pc()
    ws = await open_with_hello(token)
    await ws.send_json_to({"type": "status", "cpu": 1})
    await ws.send_json_to({"type": "status", "cpu": 2})
    await sync(ws)
    assert (await current_state(pc.id))["status"]["cpu"] == 1
    await ws.disconnect()


async def test_bad_frames_keep_connection():
    _, token = await make_pc()
    ws = await open_with_hello(token)
    await ws.send_to(text_data="{not json")
    assert await ws.receive_json_from() == example("error_bad_json.json")
    await ws.send_to(bytes_data=b"\x01\x00")
    assert await ws.receive_json_from() == example("error_binary_not_supported.json")
    await ws.send_json_to({"type": "nope"})
    assert await ws.receive_json_from() == example("error_unknown_type.json")
    await sync(ws)
    await ws.disconnect()


async def test_new_connection_supersedes_old():
    pc, token = await make_pc()
    first = await open_with_hello(token)
    await sync(first)
    second = await open_with_hello(token)
    closed = await first.receive_output(timeout=1)
    assert closed["code"] == protocol.CLOSE_SUPERSEDED
    await first.disconnect()
    await sync(second)
    assert (await current_state(pc.id))["online"] is True
    await second.disconnect()


async def test_revoked_closes_connection():
    pc, token = await make_pc()
    ws = await open_with_hello(token)
    await sync(ws)
    await get_channel_layer().group_send(pc_group(pc.id), {"type": "pc.revoked"})
    closed = await ws.receive_output(timeout=1)
    assert closed["code"] == protocol.CLOSE_REVOKED
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `uv run pytest tests/test_agent_ws.py -v`
Expected: FAIL (연결 실패)

- [ ] **Step 3: AgentConsumer 구현**

`server/agent/consumers.py`:

```python
import asyncio
import time
from collections import defaultdict

from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from agent import protocol, state
from labs.models import PC
from live.publish import publish_pc
from wcms.groups import pc_group
from wcms.net import is_internal_scope

# ASGI 서버는 프로세스 하나로 고정이므로 PC별 상태 변경은 이 잠금으로 순서를 지킨다.
_locks: defaultdict[int, asyncio.Lock] = defaultdict(asyncio.Lock)


@database_sync_to_async
def _pc_id_for_token(token: str) -> int | None:
    pc = PC.from_token(token)
    return pc.id if pc else None


@database_sync_to_async
def _save_version(pc_id: int, version: str) -> None:
    PC.objects.filter(pk=pc_id).update(client_version=version[:20])


def _error(code: str) -> dict:
    return {"type": "error", "error": code}


class AgentConsumer(AsyncJsonWebsocketConsumer):
    pc_id: int | None = None
    hello_done = False
    last_status: float | None = None

    async def connect(self) -> None:
        token = protocol.bearer_token(self.scope)
        pc_id = await _pc_id_for_token(token) if token and is_internal_scope(self.scope) else None
        if pc_id is None:
            await self.close()
            return
        self.pc_id = pc_id
        group = pc_group(pc_id)
        await self.channel_layer.group_send(group, {"type": "pc.superseded"})
        await self.channel_layer.group_add(group, self.channel_name)
        async with _locks[pc_id]:
            await sync_to_async(state.mark_connected)(pc_id, self.channel_name)
        await self.accept()
        await publish_pc(pc_id, online_changed=True)

    async def disconnect(self, code: int) -> None:
        if self.pc_id is None:
            return
        await self.channel_layer.group_discard(pc_group(self.pc_id), self.channel_name)
        async with _locks[self.pc_id]:
            changed = await sync_to_async(state.mark_disconnected)(self.pc_id, self.channel_name)
        if changed:
            await publish_pc(self.pc_id, online_changed=True)

    async def receive(self, text_data=None, bytes_data=None) -> None:
        if text_data is None:
            await self.send_json(_error("binary_not_supported"))
            return
        try:
            message = await self.decode_json(text_data)
        except (ValueError, RecursionError):
            await self.send_json(_error("bad_json"))
            return
        if not isinstance(message, dict):
            await self.send_json(_error("bad_json"))
            return
        await self.handle(message)

    async def handle(self, message: dict) -> None:
        kind = message.get("type")
        if not self.hello_done:
            if kind != "hello":
                await self.close(code=protocol.CLOSE_HELLO_REQUIRED)
                return
            if message.get("proto") != protocol.PROTO_VERSION:
                await self.close(code=protocol.CLOSE_UNSUPPORTED_PROTO)
                return
            self.hello_done = True
            version = message.get("version")
            if isinstance(version, str):
                await _save_version(self.pc_id, version)
            return
        if kind == "status":
            now = time.monotonic()
            if self.last_status is not None and now - self.last_status < protocol.STATUS_MIN_INTERVAL:
                return
            self.last_status = now
            async with _locks[self.pc_id]:
                saved = await sync_to_async(state.save_status)(
                    self.pc_id, self.channel_name, protocol.clean_status(message)
                )
            if saved:
                await publish_pc(self.pc_id, online_changed=False)
        elif kind == "ping":
            await self.send_json({"type": "pong"})
        else:
            await self.send_json(_error("unknown_type"))

    async def pc_superseded(self, event: dict) -> None:
        await self.close(code=protocol.CLOSE_SUPERSEDED)

    async def pc_revoked(self, event: dict) -> None:
        await self.close(code=protocol.CLOSE_REVOKED)
```

`last_status`는 `None`으로 시작해서 연결 후 첫 status는 항상 받는다.

`server/wcms/routing.py`:

```python
from django.urls import path

from agent.consumers import AgentConsumer

websocket_urlpatterns = [
    path("client/ws", AgentConsumer.as_asgi()),
]
```

- [ ] **Step 4: 테스트 통과 확인 (반복 실행 포함)**

Run: `uv run pytest tests/test_agent_ws.py -v` 를 3번, 그다음 `uv run pytest`
Expected: 매번 모두 통과, 경고 없음

- [ ] **Step 5: Commit**

```bash
git add server/agent/consumers.py server/wcms/routing.py server/tests/test_agent_ws.py
git commit -m "feat(server): client WebSocket per protocol v1"
```

---

### Task 13: 브라우저 실시간 WebSocket (`/ws/live`)

**Files:**
- Create: `server/live/consumers.py`
- Modify: `server/wcms/routing.py`
- Test: `server/tests/test_live_ws.py`

**Interfaces:**
- Consumes: `live.snapshots`, `wcms.groups`, `wcms.api.is_admin`, 채널 메시지 `live.pc`, `live.seat`, `live.room_changed`, `session.end`
- Produces: `LiveConsumer` at `/ws/live` (Origin 검사, 세션 인증). 브라우저 ↔ 서버 메시지:
  - 브라우저 → 서버: `{"type": "subscribe", "topic": T}`, `{"type": "unsubscribe", "topic": T}`. T는 `room:<id>`(관리자), `room:<id>:public`(누구나), `pc:<id>`(관리자)
  - 서버 → 브라우저:
    - 구독 직후 `{"type": "snapshot", "topic": T, "pcs": [LivePC]}` (room), `{"type": "snapshot", "topic": T, "seats": [PublicSeat]}` (room public), `{"type": "snapshot", "topic": T, "pc": LivePC}` (pc)
    - 변경 `{"type": "pc", "topic": T, "pc": LivePC}`, `{"type": "seat", "topic": T, "seat": PublicSeat}`
    - 좌석 구성 변경 `{"type": "room_changed", "topic": T}` → 브라우저는 다시 구독해서 새 스냅샷을 받는다
    - 오류 `{"type": "error", "error": "bad_json" | "unknown_type" | "bad_topic" | "forbidden_topic" | "not_found", "topic"?}`
  - 로그아웃·계정 삭제 시 close code `4401`
  - 구독할 때마다 관리자 권한을 DB에서 다시 확인한다

- [ ] **Step 1: 실패하는 테스트 작성**

`server/tests/test_live_ws.py`:

```python
import pytest
from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

from agent import consumers, protocol
from labs.models import PC, Room
from live.consumers import LiveConsumer
from live.publish import room_changed
from wcms.asgi import application
from wcms.groups import user_group

pytestmark = pytest.mark.django_db(transaction=True)
ADMIN_ONLY = {"hostname", "user", "session", "foreground", "cpu", "version", "id"}


@pytest.fixture(autouse=True)
def no_status_throttle(monkeypatch):
    monkeypatch.setattr(protocol, "STATUS_MIN_INTERVAL", 0.0)


@pytest.fixture(autouse=True)
def fresh_locks():
    consumers._locks.clear()


@database_sync_to_async
def make_room_and_pc() -> tuple[Room, PC, str]:
    room = Room.objects.create(name="301", rows=2, cols=4)
    pc, token = PC.register(hostname="LAB-HOST-1", machine_guid="g1", specs={}, version="2026.1")
    pc.room, pc.row, pc.col = room, 0, 0
    pc.save()
    return room, pc, token


@database_sync_to_async
def make_staff(is_staff: bool = True):
    return get_user_model().objects.create_user("staff", password="pw-very-long-123", is_staff=is_staff)


async def live_as(user) -> WebsocketCommunicator:
    ws = WebsocketCommunicator(LiveConsumer.as_asgi(), "/ws/live")
    ws.scope["user"] = user
    connected, _ = await ws.connect()
    assert connected
    return ws


async def agent(token: str) -> WebsocketCommunicator:
    ws = WebsocketCommunicator(application, "/client/ws", headers=[(b"authorization", f"Bearer {token}".encode())])
    assert (await ws.connect())[0]
    await ws.send_json_to({"type": "hello", "proto": 1, "version": "2026.1"})
    return ws


async def test_anonymous_public_room_flow():
    room, pc, token = await make_room_and_pc()
    ws = await live_as(AnonymousUser())
    await ws.send_json_to({"type": "subscribe", "topic": f"room:{room.id}:public"})
    snapshot = await ws.receive_json_from()
    assert snapshot == {
        "type": "snapshot",
        "topic": f"room:{room.id}:public",
        "seats": [{"row": 0, "col": 0, "label": "301-01", "online": False}],
    }
    client = await agent(token)
    seat = await ws.receive_json_from(timeout=2)
    assert seat["type"] == "seat" and seat["seat"]["online"] is True
    await client.send_json_to({"type": "status", "user": "Student", "session": "active"})
    await client.send_json_to({"type": "ping"})
    await client.receive_json_from()
    assert await ws.receive_nothing(timeout=0.3)
    await client.disconnect()
    offline = await ws.receive_json_from(timeout=2)
    assert offline["seat"]["online"] is False and not ADMIN_ONLY & offline["seat"].keys()
    await ws.disconnect()


async def test_anonymous_cannot_subscribe_admin_topics():
    room, pc, _ = await make_room_and_pc()
    ws = await live_as(AnonymousUser())
    for topic in (f"room:{room.id}", f"pc:{pc.id}"):
        await ws.send_json_to({"type": "subscribe", "topic": topic})
        assert (await ws.receive_json_from())["error"] == "forbidden_topic"
    await ws.disconnect()


async def test_admin_room_flow():
    room, pc, token = await make_room_and_pc()
    ws = await live_as(await make_staff())
    await ws.send_json_to({"type": "subscribe", "topic": f"room:{room.id}"})
    snapshot = await ws.receive_json_from()
    assert snapshot["pcs"][0]["hostname"] == "LAB-HOST-1" and snapshot["pcs"][0]["online"] is False
    client = await agent(token)
    assert (await ws.receive_json_from(timeout=2))["pc"]["online"] is True
    await client.send_json_to({"type": "status", "user": "Student", "session": "active"})
    update = await ws.receive_json_from(timeout=2)
    assert update == {"type": "pc", "topic": f"room:{room.id}", "pc": update["pc"]}
    assert update["pc"]["user"] == "Student"
    await client.disconnect()
    assert (await ws.receive_json_from(timeout=2))["pc"]["online"] is False
    await ws.disconnect()


async def test_admin_pc_topic():
    _, pc, _ = await make_room_and_pc()
    ws = await live_as(await make_staff())
    await ws.send_json_to({"type": "subscribe", "topic": f"pc:{pc.id}"})
    snapshot = await ws.receive_json_from()
    assert snapshot["type"] == "snapshot" and snapshot["pc"]["id"] == pc.id
    await ws.disconnect()


async def test_bad_requests():
    ws = await live_as(await make_staff())
    await ws.send_to(text_data="{nope")
    assert (await ws.receive_json_from())["error"] == "bad_json"
    await ws.send_json_to({"type": "dance"})
    assert (await ws.receive_json_from())["error"] == "unknown_type"
    for topic in ("room:abc", "pc:1:public", 5):
        await ws.send_json_to({"type": "subscribe", "topic": topic})
        assert (await ws.receive_json_from())["error"] == "bad_topic"
    await ws.send_json_to({"type": "subscribe", "topic": "room:999"})
    assert (await ws.receive_json_from())["error"] == "not_found"
    await ws.disconnect()


async def test_demoted_user_loses_admin_topics():
    room, _, _ = await make_room_and_pc()
    user = await make_staff()
    ws = await live_as(user)
    await database_sync_to_async(get_user_model().objects.filter(pk=user.pk).update)(is_staff=False)
    await ws.send_json_to({"type": "subscribe", "topic": f"room:{room.id}"})
    assert (await ws.receive_json_from())["error"] == "forbidden_topic"
    await ws.disconnect()


async def test_session_end_closes():
    user = await make_staff()
    ws = await live_as(user)
    await get_channel_layer().group_send(user_group(user.pk), {"type": "session.end"})
    closed = await ws.receive_output(timeout=1)
    assert closed["type"] == "websocket.close" and closed["code"] == 4401


async def test_room_changed_forwarded_and_unsubscribe():
    room, _, _ = await make_room_and_pc()
    ws = await live_as(AnonymousUser())
    topic = f"room:{room.id}:public"
    await ws.send_json_to({"type": "subscribe", "topic": topic})
    await ws.receive_json_from()
    await sync_to_async(room_changed)(room.id)
    assert await ws.receive_json_from() == {"type": "room_changed", "topic": topic}
    await ws.send_json_to({"type": "unsubscribe", "topic": topic})
    await sync_to_async(room_changed)(room.id)
    assert await ws.receive_nothing(timeout=0.3)
    await ws.disconnect()


async def test_foreign_origin_rejected():
    ws = WebsocketCommunicator(
        application, "/ws/live", headers=[(b"origin", b"http://evil.example"), (b"host", b"localhost")]
    )
    assert (await ws.connect())[0] is False


async def test_same_origin_accepted():
    ws = WebsocketCommunicator(
        application, "/ws/live", headers=[(b"origin", b"http://localhost"), (b"host", b"localhost")]
    )
    assert (await ws.connect())[0] is True
    await ws.disconnect()
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `uv run pytest tests/test_live_ws.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'live.consumers'`

- [ ] **Step 3: LiveConsumer 구현**

`server/live/consumers.py`:

```python
import re

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth import get_user_model

from live.snapshots import pc_snapshot, public_room_snapshot, room_snapshot
from wcms.api import is_admin
from wcms.groups import pc_watch_group, room_group, room_public_group, user_group

TOPIC = re.compile(r"^(room|pc):(\d{1,10})(:public)?$")
CLOSE_SESSION_ENDED = 4401


@database_sync_to_async
def _still_admin(user_id: int) -> bool:
    return get_user_model().objects.filter(pk=user_id, is_active=True, is_staff=True).exists()


@database_sync_to_async
def _snapshot(kind: str, ident: int, public: bool):
    if kind == "pc":
        return "pc", pc_snapshot(ident)
    if public:
        return "seats", public_room_snapshot(ident)
    return "pcs", room_snapshot(ident)


def _group(kind: str, ident: int, public: bool) -> str:
    if kind == "pc":
        return pc_watch_group(ident)
    return room_public_group(ident) if public else room_group(ident)


class LiveConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self) -> None:
        self.user = self.scope.get("user")
        self.admin = is_admin(self.user)
        self.topics: dict[str, str] = {}
        await self.accept()
        if self.admin:
            await self.channel_layer.group_add(user_group(self.user.pk), self.channel_name)

    async def disconnect(self, code: int) -> None:
        for group in self.topics.values():
            await self.channel_layer.group_discard(group, self.channel_name)
        if self.admin:
            await self.channel_layer.group_discard(user_group(self.user.pk), self.channel_name)

    async def receive(self, text_data=None, bytes_data=None) -> None:
        try:
            message = await self.decode_json(text_data) if text_data is not None else None
        except (ValueError, RecursionError):
            message = None
        if not isinstance(message, dict):
            await self.send_json({"type": "error", "error": "bad_json"})
            return
        kind = message.get("type")
        if kind == "subscribe":
            await self.subscribe(message.get("topic"))
        elif kind == "unsubscribe":
            await self.unsubscribe(message.get("topic"))
        else:
            await self.send_json({"type": "error", "error": "unknown_type"})

    async def subscribe(self, topic) -> None:
        match = TOPIC.match(topic) if isinstance(topic, str) else None
        if match is None or (match.group(1) == "pc" and match.group(3)):
            await self.send_json({"type": "error", "error": "bad_topic"})
            return
        kind, ident, public = match.group(1), int(match.group(2)), bool(match.group(3))
        if not public and not (self.admin and await _still_admin(self.user.pk)):
            await self.send_json({"type": "error", "error": "forbidden_topic", "topic": topic})
            return
        key, snapshot = await _snapshot(kind, ident, public)
        if snapshot is None:
            await self.send_json({"type": "error", "error": "not_found", "topic": topic})
            return
        if topic not in self.topics:
            group = _group(kind, ident, public)
            await self.channel_layer.group_add(group, self.channel_name)
            self.topics[topic] = group
        await self.send_json({"type": "snapshot", "topic": topic, key: snapshot})

    async def unsubscribe(self, topic) -> None:
        group = self.topics.pop(topic, None) if isinstance(topic, str) else None
        if group is not None:
            await self.channel_layer.group_discard(group, self.channel_name)

    async def live_pc(self, event: dict) -> None:
        if event["topic"] in self.topics:
            await self.send_json({"type": "pc", "topic": event["topic"], "pc": event["pc"]})

    async def live_seat(self, event: dict) -> None:
        if event["topic"] in self.topics:
            await self.send_json({"type": "seat", "topic": event["topic"], "seat": event["seat"]})

    async def live_room_changed(self, event: dict) -> None:
        if event["topic"] in self.topics:
            await self.send_json({"type": "room_changed", "topic": event["topic"]})

    async def session_end(self, event: dict) -> None:
        await self.close(code=CLOSE_SESSION_ENDED)
```

`server/wcms/routing.py`:

```python
from channels.security.websocket import AllowedHostsOriginValidator
from django.urls import path

from agent.consumers import AgentConsumer
from live.consumers import LiveConsumer

websocket_urlpatterns = [
    path("client/ws", AgentConsumer.as_asgi()),
    path("ws/live", AllowedHostsOriginValidator(LiveConsumer.as_asgi())),
]
```

`/client/ws`에는 Origin 검사를 붙이지 않는다. 클라이언트는 쿠키가 아니라 토큰으로 인증하고 Origin 헤더를 보내지 않는다.

- [ ] **Step 4: 테스트 통과 확인 (반복 실행 포함)**

Run: `uv run pytest tests/test_live_ws.py -v` 를 3번, 그다음 `uv run pytest`
Expected: 매번 모두 통과, 경고 없음

- [ ] **Step 5: Commit**

```bash
git add server/live/consumers.py server/wcms/routing.py server/tests/test_live_ws.py
git commit -m "feat(server): browser live WebSocket with topic subscriptions"
```

---

### Task 14: OpenAPI 스키마

프론트엔드(계획 03)가 이 파일에서 TypeScript 타입을 만든다.

**Files:**
- Create: `server/openapi.yaml` (생성물, 커밋한다)
- Modify: 경고가 나오는 뷰의 `extend_schema` (필요할 때만)
- Test: `server/tests/test_openapi.py`

**Interfaces:**
- Produces: `server/openapi.yaml` — 모든 `/api/*` 경로, 컴포넌트 `LivePC`, `PublicSeat`, `PublicRoom`, `Error`, `Me` 포함. `/client/register` 제외

- [ ] **Step 1: 실패하는 테스트 작성**

`server/tests/test_openapi.py`:

```python
from pathlib import Path

import yaml
from django.core.management import call_command

SERVER_DIR = Path(__file__).resolve().parents[1]


def generate(tmp_path) -> str:
    target = tmp_path / "openapi.yaml"
    call_command("spectacular", "--file", str(target), "--validate", "--fail-on-warn")
    return target.read_text(encoding="utf-8")


def test_schema_is_committed_and_current(tmp_path):
    assert (SERVER_DIR / "openapi.yaml").read_text(encoding="utf-8") == generate(tmp_path)


def test_schema_contents(tmp_path):
    schema = yaml.safe_load(generate(tmp_path))
    components = schema["components"]["schemas"]
    for name in ("LivePC", "PublicSeat", "PublicRoom", "Error", "Me"):
        assert name in components
    assert "/client/register" not in schema["paths"]
    assert "/api/public/rooms/{id}" in schema["paths"]
    assert set(components["PublicSeat"]["properties"]) == {"row", "col", "label", "online"}
```

`yaml`은 drf-spectacular가 의존하는 PyYAML이다. 없으면 `uv add --dev pyyaml`.

- [ ] **Step 2: 스키마 생성과 경고 정리**

Run: `uv run python manage.py spectacular --file openapi.yaml --validate --fail-on-warn`

경고가 나오면 경고가 가리키는 뷰에 `extend_schema`로 `request`/`responses`를 명시하거나, path 파라미터 타입을 `extend_schema(parameters=[OpenApiParameter("pk", int, OpenApiParameter.PATH)])`로 적는다. 컴포넌트 이름은 serializer 이름에서 `Serializer`를 뺀 것이므로 `LivePCSerializer` → `LivePC`, `PublicSeatSerializer` → `PublicSeat`, `ErrorSerializer` → `Error`, `MeSerializer` → `Me`가 된다. 경고 없이 끝날 때까지 반복한다.

- [ ] **Step 3: 테스트 통과 확인**

Run: `uv run pytest -v`
Expected: 모두 통과

- [ ] **Step 4: Commit**

```bash
git add server
git commit -m "feat(server): committed OpenAPI schema with freshness test"
```

---

### Task 15: 개발용 가짜 클라이언트, 실행 문서, 통합 확인

**Files:**
- Create: `server/tools/fake_client.py`
- Modify: `README.md`, `.gitignore`

**Interfaces:**
- Consumes: `protocol/README.md`
- Produces: `uv run python tools/fake_client.py --server http://localhost:8000 --pin <PIN> --count N`. 토큰은 `server/tools/.fake_clients.json`에 저장. close 4410을 받으면 그 PC의 토큰을 지우고 멈춘다

- [ ] **Step 1: 가짜 클라이언트 작성**

`server/tools/fake_client.py`:

```python
"""개발용 가짜 클라이언트. C++ 클라이언트 없이 서버와 화면을 확인할 때 쓴다. 프로토콜은 protocol/README.md.

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
CLOSE_REVOKED = 4410
APPS = [
    ("chrome.exe", "자료구조 3주차 - Google Docs - Chrome"),
    ("chrome.exe", "YouTube - Chrome"),
    ("Code.exe", "main.cpp - Visual Studio Code"),
    ("explorer.exe", "파일 탐색기"),
]


def load_tokens() -> dict[str, str]:
    return json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}


def save_tokens(tokens: dict[str, str]) -> None:
    STATE_FILE.write_text(json.dumps(tokens))


def register(server: str, pin: str, index: int) -> str:
    body = json.dumps(
        {
            "pin": pin,
            "hostname": f"FAKE-{index:02d}",
            "machine_guid": f"fake-{index}",
            "specs": {"cpu": "Fake CPU", "ram_gb": 16, "os": "Windows 11"},
            "version": "2026.1",
        }
    ).encode()
    request = urllib.request.Request(
        f"{server}/client/register", data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(request) as response:
        return json.load(response)["token"]


def fake_status() -> dict:
    session = random.choices(["active", "locked", "none"], weights=[8, 1, 1])[0]
    process, title = random.choice(APPS)
    status = {
        "type": "status",
        "cpu": round(random.uniform(1, 60), 1),
        "mem_used": random.randint(4, 12) * 1024**3,
        "mem_total": 16 * 1024**3,
        "disk_used": 246 * 1000**3,
        "disk_total": 512 * 1000**3,
        "session": session,
        "user": "Student" if session != "none" else "",
    }
    if session == "active":
        status["foreground"] = {"process": process, "title": title}
    return status


async def run_one(ws_url: str, index: int, tokens: dict[str, str]) -> None:
    headers = {"Authorization": f"Bearer {tokens[str(index)]}"}
    async for ws in websockets.connect(ws_url, additional_headers=headers):
        try:
            await ws.send(json.dumps({"type": "hello", "proto": 1, "version": "2026.1"}))
            while True:
                await ws.send(json.dumps(fake_status()))
                await asyncio.sleep(10)
        except websockets.ConnectionClosed as closed:
            if closed.rcvd is not None and closed.rcvd.code == CLOSE_REVOKED:
                tokens.pop(str(index), None)
                save_tokens(tokens)
                print(f"FAKE-{index:02d}: 토큰이 무효가 되어 멈춥니다. --pin으로 다시 등록하세요.")
                return


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", default="http://localhost:8000")
    parser.add_argument("--pin")
    parser.add_argument("--count", type=int, default=8)
    args = parser.parse_args()
    server = args.server.rstrip("/")

    tokens = load_tokens()
    for index in range(1, args.count + 1):
        if str(index) not in tokens:
            if not args.pin:
                parser.error(f"FAKE-{index:02d}의 토큰이 없습니다. --pin을 주세요.")
            tokens[str(index)] = register(server, args.pin, index)
            save_tokens(tokens)

    ws_url = server.replace("http", "ws", 1) + "/client/ws"
    await asyncio.gather(*(run_one(ws_url, i, tokens) for i in range(1, args.count + 1)))


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: README와 .gitignore**

`README.md` 전체:

````markdown
# WCMS

실습실 PC 원격 관리 시스템.

| 폴더 | 내용 |
|---|---|
| `server/` | Django + DRF + Channels |
| `frontend/` | SvelteKit SPA (계획 03) |
| `client/` | C++ Windows 클라이언트 (계획 05) |
| `protocol/` | 클라이언트-서버 프로토콜과 메시지 예시 |

설계 문서: `docs/superpowers/specs/2026-10-24-wcms-2026-1-design.md`

## 서버 실행 (개발)

```bash
cd server
uv sync
uv run python manage.py migrate
uv run python manage.py createadmin <아이디>
uv run uvicorn wcms.asgi:application --port 8000 --reload
```

`createadmin`이 출력한 `/enroll/...` 링크에서 비밀번호와 인증 앱을 등록한다 (화면은 계획 03).

가짜 클라이언트: `uv run python tools/fake_client.py --pin <PIN> --count 8`

## 테스트

```bash
cd server
uv run pytest
```

OpenAPI 스키마를 바꾼 뒤에는 `uv run python manage.py spectacular --file openapi.yaml --validate --fail-on-warn`으로 다시 만든다.
````

`.gitignore`에 `server/tools/.fake_clients.json`이 있는지 확인하고 없으면 추가한다.

- [ ] **Step 3: 실제 서버로 통합 확인**

임시 DB를 쓰고, 끝나면 지운다.

```bash
cd server
export WCMS_DB_PATH="$(mktemp -d)/wcms.sqlite3"
uv run python manage.py migrate
uv run python manage.py shell -c "from labs.models import Room, RegistrationPin; r=Room.objects.create(name='301', rows=5, cols=8, aisle_after=4); print(r.id, RegistrationPin.issue(user=None, multi_use=True, minutes=10).pin)"
uv run uvicorn wcms.asgi:application --port 8765 &
```

1. `curl -s http://127.0.0.1:8765/healthz` → `ok`
2. 다른 터미널에서 `uv run python tools/fake_client.py --server http://127.0.0.1:8765 --pin <PIN> --count 3`, 15초 대기
3. 셸에서 FAKE-01을 301의 (0, 0)에 앉히기: `uv run python manage.py shell -c "from labs.models import PC, Room; PC.objects.filter(hostname='FAKE-01').update(room=Room.objects.get(name='301'), row=0, col=0)"`
4. `curl -s http://127.0.0.1:8765/api/public/rooms/<room id>` → `seats`에 `{"row": 0, "col": 0, "label": "301-01", "online": true}`, 응답에 `FAKE-01` 없음
5. `curl -s http://127.0.0.1:8765/api/rooms` → `401`, `{"error": "not_authenticated", ...}`
6. 가짜 클라이언트를 끄고 3초 뒤 4번을 다시 → `"online": false`
7. 서버를 끄고, `server/tools/.fake_clients.json`과 임시 DB를 지운다. `git status`에 의도한 파일만 남았는지 확인

- [ ] **Step 4: 전체 테스트**

Run: `uv run pytest`
Expected: 모두 통과, 경고 없음

- [ ] **Step 5: Commit**

```bash
git add server/tools/fake_client.py README.md .gitignore
git commit -m "feat(server): fake client for protocol v1 and run instructions"
```

---

## 실행 결과 및 다음 계획으로 넘기는 항목

계획 02는 완료됐다 (테스트 259개 통과, 15개는 비로그인 허용 목록이라 건너뜀). 실행 중 계획과 달라진 점:

- DRF의 CSRF 실패도 `csrf_failed`로 답한다. 등록 링크는 조건부 UPDATE로 한 번만 쓰이고, 등록을 마치지 않은 관리자를 재설정하면 새 등록 링크(NEW)를 준다.
- PIN은 6자리 ASCII 숫자 문자열만 받는다. status 숫자는 범위를 먼저 보고 유한한 값만 받는다. hello의 `proto`는 정수 1만 받는다.
- 학생이 보낸 문자열의 짝 없는 surrogate: 등록 값(호스트 이름, GUID, 버전, specs)은 400, status 문자열은 `?`로 바꾼다. REST 응답은 `UNICODE_JSON=False`(비ASCII를 `\uXXXX`로)라 어떤 값도 500을 만들지 못한다.
- 두 consumer 모두 처리 중 예외는 기록하고 1011로 닫는다. 연결 교체·그룹 가입·상태 기록·publish는 PC별 잠금 안에서 한다.
- `/ws/live`는 그룹에 먼저 들어간 뒤 스냅샷을 만든다. 토픽은 정규형(`room:5`, 앞자리 0 없음)만 받는다.
- 채널 그룹 만료(24시간, Redis 재시작) 대응: 클라이언트 ping마다(10초에 한 번까지) 그룹 재가입과 상태 TTL 갱신, 상태가 사라졌으면 되살린다. 다른 연결이 PC를 쥐고 있으면 4409로 닫는다. `/ws/live`에 ping/pong을 더해 그룹 재가입과 관리자 권한·세션 재확인(없으면 4401). 계획 03 Task 3에 25초 ping을 넣었다.
- `/api` 아래는 404·500도 JSON. OpenAPI 후처리 훅이 응답 필드 required와 401/403 오류 응답을 채운다.
- 모든 `/api/` 경로가 비로그인에 401을 주는지 URLconf를 돌며 확인하는 테스트(`tests/test_anonymous_access.py`). 허용 목록은 테스트 안의 고정 집합이다.
- 브라우저 실시간 규약 문서 `docs/live-ws.md`.

### 계획 03에서 처리

- 등록 링크 화면은 `GET /api/auth/enroll/<token>`이 CSRF 쿠키를 준다 (`/me` 먼저 부를 필요 없음)
- `pc:<id>` 구독자는 자리 이동·이름 변경·PC 삭제 때 아무 메시지도 받지 않는다. PC 상세 화면이 생기면(계획 04) 같이 정한다
- 스키마: 작은 정수 필드가 int64로 나옴, `Error.fields`가 자유 형식, `X-CSRFToken` 헤더 미기재

### 계획 04에서 처리

- `AuditLog.actor`가 SET_NULL이라 관리자를 지우면 누가 했는지 사라진다. `actor_name` 스냅샷 추가, `record(actor, action, target, detail: dict)`로 시그니처 정리
- 연결 시 `from_token`과 `group_add` 사이의 폐기 경합: 잠금 안에서 토큰을 다시 확인
- 관리자 강등 기능을 만들면 그 사용자의 실시간 세션을 끝낸다 (`end_live_sessions`)

### 계획 05에서 처리

- hello 전에도 온라인으로 보이고 hello 시간 제한이 없음
- protocol/README.md 보강: 오류 `fields` 모양, 429의 Retry-After, TLS 신뢰(자체 루트 CA), 핸드셰이크 403과 그 밖의 실패 구분, 4410 뒤 재등록 흐름, hello 전 JSON이지만 객체가 아닌 프레임

### 계획 06에서 처리

- 바이너리 프레임 플래그 비트, 방향, seq 순환

### 계획 09에서 처리

- `DEBUG` 기본값을 끄는 쪽으로, `DEBUG=0`이면 `WCMS_REDIS_URL`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`가 없을 때 시작 실패
- 환경: `SECRET_KEY`, `WCMS_BEHIND_TLS_PROXY`, `WCMS_REQUIRE_INTERNAL=1`, `WCMS_TRUST_X_REAL_IP=1` (없으면 IP 시도 제한이 전체 공용이 되어 로그인 20회 실패로 모두 잠김)
- nginx: 두 server 블록 모두 `X-Real-IP`를 덮어쓰고, `X-WCMS-Via`는 내부 블록에서만 설정
- uvicorn 워커 하나, ws ping 간격과 최대 메시지 크기
- Redis 지속성(또는 재시작 절차 문서화). 재시작하면 세션이 사라지고 그룹·상태는 ping으로 복구된다
- 정리 작업: 쓰지 않은 등록 PIN, 기록 보존 기간
- `createadmin` 입력 검증과 원자성
- SQLite 잠금 대기(timeout 20초)는 동기 처리 스레드 하나를 통째로 멈추므로 트랜잭션을 짧게, timeout 재검토
- 상태 키가 축출된 순간 교체가 겹치면 밀려난 연결이 상태를 되살릴 수 있음 (Redis noeviction이면 생기지 않음)
