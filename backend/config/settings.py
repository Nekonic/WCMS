"""
WCMS 관리 백엔드 (Django) 설정.

DB 는 DATABASE_URL 환경변수로 지정한다(운영: PostgreSQL). 미지정 시 개발/검증용
SQLite 로 폴백한다. 관리자 인증은 Django 기본 auth(세션 + CSRF)를 사용한다.
"""
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, True),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY", default="django-insecure-dev-only-change-me")
DEBUG = env.bool("DJANGO_DEBUG")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "accounts",
    "fleet",
    "enrollment",
    "commands",
    "clientlogs",
    "internalapi",
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

ROOT_URLCONF = "config.urls"

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
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Database — DATABASE_URL 미지정 시 SQLite(개발/검증). 운영은 postgres://... 지정.
DATABASES = {
    "default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'dev.sqlite3'}"),
}


AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization
LANGUAGE_CODE = "ko-kr"
TIME_ZONE = "Asia/Seoul"
USE_I18N = True
USE_TZ = True


# Static files
STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# 관리자 인증: 세션 + CSRF (설계 4.2 - 클라이언트 인증서 스킴과 분리)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = env.bool("DJANGO_COOKIE_SECURE", default=not DEBUG)
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE


# PKC CA 경로 — 운영 환경에서는 환경변수로 실제 CA 경로를 지정한다.
# 미지정 시 BASE_DIR/ca/ 아래의 기본 경로를 사용한다.
WCMS_CA_CERT_PATH = env(
    "WCMS_CA_CERT_PATH", default=str(BASE_DIR / "ca" / "ca.crt")
)
WCMS_CA_KEY_PATH = env(
    "WCMS_CA_KEY_PATH", default=str(BASE_DIR / "ca" / "ca.key")
)

# 게이트웨이 전용 내부 API 공유 토큰 (설계 §3).
# 운영 환경에서는 반드시 환경변수로 강력한 난수 값을 지정한다.
WCMS_INTERNAL_TOKEN = env(
    "WCMS_INTERNAL_TOKEN", default="dev-internal-token-change-me"
)

# nginx 가 mTLS 클라이언트 인증서를 전달할 때 사용하는 요청 META 헤더 이름.
# nginx: proxy_set_header X-SSL-Client-Cert $ssl_client_escaped_cert;
# Django META 변환: HTTP_X_SSL_CLIENT_CERT (헤더명의 '-' -> '_', 'HTTP_' 접두사 추가).
# 값이 URL-인코딩(percent-encoded) PEM 일 수 있으므로 인증 클래스에서 unquote 처리.
WCMS_CLIENT_CERT_HEADER = env(
    "WCMS_CLIENT_CERT_HEADER", default="HTTP_X_SSL_CLIENT_CERT"
)


# DRF — 관리자 API 기본값은 세션 인증 + 로그인 필요.
# 클라이언트용 엔드포인트(enrollment 등)는 뷰별로 권한/인증을 재정의한다.
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    # rate limit 범위별 상한 (설계 4.5 참조).
    # 실시간/WS 경로의 per-client 신원 기준 rate limit 은 Rust 게이트웨이가 담당(Phase 2).
    "DEFAULT_THROTTLE_RATES": {
        "login": "10/min",
        "enroll": "20/min",
    },
}
