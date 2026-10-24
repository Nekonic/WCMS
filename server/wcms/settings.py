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
if not DEBUG and (not SECRET_KEY or SECRET_KEY == DEV_SECRET_KEY):
    raise ImproperlyConfigured("WCMS_DEBUG=0이면 WCMS_SECRET_KEY를 반드시 설정해야 합니다.")

PRODUCTION_REQUIRED = ["WCMS_REDIS_URL", "WCMS_ALLOWED_HOSTS", "WCMS_CSRF_TRUSTED_ORIGINS"]
if not DEBUG:
    missing = [name for name in PRODUCTION_REQUIRED if not os.environ.get(name)]
    if missing:
        raise ImproperlyConfigured(f"WCMS_DEBUG=0이면 다음 환경 변수가 필요합니다: {', '.join(missing)}")

ALLOWED_HOSTS = env_list("WCMS_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("WCMS_CSRF_TRUSTED_ORIGINS", "http://localhost:5173")

INSTALLED_APPS = [
    "wcms",
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
    "wcms.middleware.InternalOnlyMiddleware",
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
    # 학생이 보낸 문자열에 짝 없는 서로게이트가 섞여 있어도 응답이 500이 되지 않도록 ASCII 이스케이프로 출력한다
    "UNICODE_JSON": False,
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
    "POSTPROCESSING_HOOKS": [
        "drf_spectacular.hooks.postprocess_schema_enums",
        "wcms.schema.postprocess_responses",
    ],
}
