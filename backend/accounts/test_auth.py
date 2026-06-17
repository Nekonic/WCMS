"""관리자 인증 API 검증."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()
PW = "contract-pw-123!"


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def admin_user(db):
    return User.objects.create_user("admin", password=PW, is_staff=True, is_superuser=True)


@pytest.mark.django_db
def test_login_success(api, admin_user):
    resp = api.post("/api/auth/login/", {"username": "admin", "password": PW}, format="json")
    assert resp.status_code == 200
    assert resp.data["username"] == "admin"
    assert resp.data["is_superuser"] is True


@pytest.mark.django_db
def test_login_wrong_password_returns_401(api, admin_user):
    resp = api.post("/api/auth/login/", {"username": "admin", "password": "wrong"}, format="json")
    assert resp.status_code == 401


@pytest.mark.django_db
def test_login_missing_fields_returns_400(api):
    assert api.post("/api/auth/login/", {"username": "admin"}, format="json").status_code == 400


@pytest.mark.django_db
def test_me_requires_auth(api):
    assert api.get("/api/auth/me/").status_code in (401, 403)


@pytest.mark.django_db
def test_me_after_login(api, admin_user):
    api.post("/api/auth/login/", {"username": "admin", "password": PW}, format="json")
    resp = api.get("/api/auth/me/")
    assert resp.status_code == 200
    assert resp.data["username"] == "admin"


@pytest.mark.django_db
def test_logout_ends_session(api, admin_user):
    api.post("/api/auth/login/", {"username": "admin", "password": PW}, format="json")
    assert api.post("/api/auth/logout/").status_code == 204
    assert api.get("/api/auth/me/").status_code in (401, 403)


@pytest.mark.django_db
def test_csrf_endpoint_returns_token(api):
    resp = api.get("/api/auth/csrf/")
    assert resp.status_code == 200
    assert resp.data["csrfToken"]
