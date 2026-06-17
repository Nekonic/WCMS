"""등록 토큰 API 검증."""
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from enrollment.models import EnrollmentToken

User = get_user_model()
PW = "contract-pw-123!"


@pytest.fixture
def auth_api(db):
    User.objects.create_user("admin", password=PW)
    api = APIClient()
    assert api.login(username="admin", password=PW)
    return api


@pytest.mark.django_db
def test_tokens_requires_auth():
    assert APIClient().get("/api/tokens/").status_code in (401, 403)


@pytest.mark.django_db
def test_tokens_create_single(auth_api):
    payload = {"usage_type": "single", "expires_in": 600}
    resp = auth_api.post("/api/tokens/", payload, format="json")
    assert resp.status_code == 201
    data = resp.data
    assert len(data["token"]) == 6
    assert data["token"].isdigit()
    assert data["usage_type"] == "single"
    assert data["created_by"] == "admin"
    assert data["expires_at"] is not None


@pytest.mark.django_db
def test_tokens_create_multi(auth_api):
    payload = {"usage_type": "multi", "expires_in": 3600}
    resp = auth_api.post("/api/tokens/", payload, format="json")
    assert resp.status_code == 201
    assert resp.data["usage_type"] == "multi"


@pytest.mark.django_db
def test_tokens_create_invalid_expires_in(auth_api):
    resp = auth_api.post("/api/tokens/", {"usage_type": "single", "expires_in": 30}, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_tokens_list_only_valid(auth_api):
    now = timezone.now()
    EnrollmentToken.objects.create(
        token="111111", usage_type="single", expires_in=600,
        expires_at=now + timezone.timedelta(seconds=600), created_by="admin",
    )
    # 만료된 토큰 (is_expired=True)
    EnrollmentToken.objects.create(
        token="222222", usage_type="single", expires_in=600,
        expires_at=now + timezone.timedelta(seconds=600), created_by="admin",
        is_expired=True,
    )
    # 만료 시각이 과거인 토큰
    EnrollmentToken.objects.create(
        token="333333", usage_type="single", expires_in=600,
        expires_at=now - timezone.timedelta(seconds=1), created_by="admin",
    )
    resp = auth_api.get("/api/tokens/")
    assert resp.status_code == 200
    assert len(resp.data) == 1
    assert resp.data[0]["token"] == "111111"


@pytest.mark.django_db
def test_tokens_delete(auth_api):
    now = timezone.now()
    obj = EnrollmentToken.objects.create(
        token="444444", usage_type="multi", expires_in=3600,
        expires_at=now + timezone.timedelta(hours=1), created_by="admin",
    )
    resp = auth_api.delete(f"/api/tokens/{obj.pk}/")
    assert resp.status_code == 204
    assert not EnrollmentToken.objects.filter(pk=obj.pk).exists()


@pytest.mark.django_db
def test_tokens_delete_unknown_returns_404(auth_api):
    resp = auth_api.delete("/api/tokens/99999/")
    assert resp.status_code == 404
