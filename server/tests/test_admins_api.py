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


def test_reset_before_first_enroll_still_asks_for_password(admin_api):
    created = create_admin(admin_api).json()
    url = admin_api.post(f"/api/admins/{created['admin']['id']}/reset").json()["enroll_url"]
    anon = APIClient()
    data = anon.get(f"/api/auth{url}").json()
    assert data["needs_password"] is True

    code = pyotp.TOTP(data["secret"]).now()
    done = anon.post(f"/api/auth{url}", {"password": "kim-long-password-42", "code": code}, format="json")
    assert done.status_code == 204

    login = APIClient()
    step = login.post("/api/auth/login", {"username": "kim", "password": "kim-long-password-42"}, format="json")
    assert step.json() == {"next": "otp"}
    assert AuditLog.objects.filter(action="admin.reset", detail__purpose=EnrollmentToken.NEW).exists()


def test_enroll_page_gets_csrf_cookie_and_can_post(admin_api):
    url = create_admin(admin_api).json()["enroll_url"]
    anon = APIClient(enforce_csrf_checks=True)
    info = anon.get(f"/api/auth{url}")
    assert info.status_code == 200
    csrf = info.cookies["csrftoken"].value
    blocked = anon.post(f"/api/auth{url}", {"password": "kim-long-password-42", "code": "000000"}, format="json")
    assert blocked.status_code == 403 and blocked.json()["error"] == "csrf_failed"
    code = pyotp.TOTP(info.json()["secret"]).now()
    done = anon.post(
        f"/api/auth{url}",
        {"password": "kim-long-password-42", "code": code},
        format="json",
        HTTP_X_CSRFTOKEN=csrf,
    )
    assert done.status_code == 204


@pytest.mark.parametrize("variant", ["ａｄｍｉｎ", "ＡDMIN"])
def test_create_rejects_compatibility_form_of_existing_username(admin_api, variant):
    response = create_admin(admin_api, variant)
    assert response.status_code == 400
    assert "username" in response.json()["fields"]
    assert User.objects.count() == 1


def test_create_stores_normalized_username(admin_api):
    response = create_admin(admin_api, "ｋｉｍ")
    assert response.status_code == 201
    assert response.json()["admin"]["username"] == "kim"
    assert User.objects.filter(username="kim").exists()


@pytest.mark.parametrize("raw", ["a½", "ﷺ" * 10])
def test_create_revalidates_normalized_username(admin_api, raw):
    response = create_admin(admin_api, raw)
    assert response.status_code == 400
    assert "username" in response.json()["fields"]
    assert User.objects.count() == 1


def test_delete_admin_ends_their_live_sessions(admin_api, monkeypatch):
    ended = []
    monkeypatch.setattr("accounts.views.end_live_sessions", ended.append)
    target_id = create_admin(admin_api).json()["admin"]["id"]
    admin_api.delete(f"/api/admins/{target_id}")
    assert ended == [target_id]
