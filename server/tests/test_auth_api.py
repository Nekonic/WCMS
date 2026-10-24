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
