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
