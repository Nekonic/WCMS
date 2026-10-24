import pyotp
import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client

from accounts import views
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


def test_otp_lockout_applies_across_sessions(client, device):
    password_step(client)
    for _ in range(5):
        client.post("/login/otp/", {"code": "abcdef"})

    fresh = Client()
    response = password_step(fresh)
    assert response.status_code == 200
    assert "잠시 후" in response.content.decode()
    assert not logged_in(fresh)
    assert fresh.get("/login/otp/").url == "/login/"


def test_password_throttled_after_ten_failures(client, staff, monkeypatch):
    for _ in range(10):
        response = password_step(client, password="wrong")
        assert response.status_code == 200

    def fail_if_called(*args, **kwargs):
        raise AssertionError("authenticate must not run while throttled")

    monkeypatch.setattr(views, "authenticate", fail_if_called)
    response = password_step(client)
    assert response.status_code == 200
    assert "잠시 후" in response.content.decode()
    assert not logged_in(client)
    assert client.get("/login/otp/setup/").url == "/login/"


def test_successful_otp_login_clears_failure_counter(client, device):
    password_step(client)
    client.post("/login/otp/", {"code": "abcdef"})
    client.post("/login/otp/", {"code": "abcdef"})
    assert cache.get(f"otp-fail:{device.user_id}") == 2

    response = client.post("/login/otp/", {"code": pyotp.TOTP(device.secret).now()})
    assert response.url == "/"
    assert logged_in(client)
    assert cache.get(f"otp-fail:{device.user_id}") is None
