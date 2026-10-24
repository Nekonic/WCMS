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
