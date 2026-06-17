"""클라이언트 로그 조회 API 검증."""
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from clientlogs.models import ClientLog
from fleet.models import Client

User = get_user_model()
PW = "contract-pw-123!"


@pytest.fixture
def auth_api(db):
    User.objects.create_user("admin", password=PW)
    api = APIClient()
    assert api.login(username="admin", password=PW)
    return api


@pytest.fixture
def pc(db):
    return Client.objects.create(hostname="PC-1")


@pytest.mark.django_db
def test_logs_requires_auth():
    assert APIClient().get("/api/logs/").status_code in (401, 403)


@pytest.mark.django_db
def test_logs_list_empty(auth_api):
    resp = auth_api.get("/api/logs/")
    assert resp.status_code == 200
    assert resp.data == []


@pytest.mark.django_db
def test_logs_list_with_data(auth_api, pc):
    ClientLog.objects.create(client=pc, level="info", message="시작")
    ClientLog.objects.create(client=pc, level="error", message="오류 발생")
    resp = auth_api.get("/api/logs/")
    assert resp.status_code == 200
    assert len(resp.data) == 2


@pytest.mark.django_db
def test_logs_filter_by_client(auth_api, pc):
    pc2 = Client.objects.create(hostname="PC-2")
    ClientLog.objects.create(client=pc, level="info", message="PC-1 로그")
    ClientLog.objects.create(client=pc2, level="info", message="PC-2 로그")
    resp = auth_api.get(f"/api/logs/?client={pc.id}")
    assert resp.status_code == 200
    assert len(resp.data) == 1
    assert resp.data[0]["message"] == "PC-1 로그"


@pytest.mark.django_db
def test_logs_filter_by_level(auth_api, pc):
    ClientLog.objects.create(client=pc, level="debug", message="디버그")
    ClientLog.objects.create(client=pc, level="critical", message="심각")
    resp = auth_api.get("/api/logs/?level=critical")
    assert resp.status_code == 200
    assert len(resp.data) == 1
    assert resp.data[0]["level"] == "critical"


@pytest.mark.django_db
def test_logs_filter_by_since(auth_api, pc):
    now = timezone.now()
    old_log = ClientLog.objects.create(client=pc, level="info", message="이전 로그")
    # created_at 을 과거로 강제 설정
    ClientLog.objects.filter(pk=old_log.pk).update(
        created_at=now - timezone.timedelta(hours=2)
    )
    ClientLog.objects.create(client=pc, level="info", message="최신 로그")
    # isoformat() 에 '+' 가 있으면 URL 에서 공백으로 해석되므로 'Z' 형식으로 변환
    since_dt = now - timezone.timedelta(hours=1)
    since_str = since_dt.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"
    resp = auth_api.get(f"/api/logs/?since={since_str}")
    assert resp.status_code == 200
    assert len(resp.data) == 1
    assert resp.data[0]["message"] == "최신 로그"


@pytest.mark.django_db
def test_logs_response_fields(auth_api, pc):
    ClientLog.objects.create(client=pc, level="warning", message="경고", source="main.py")
    resp = auth_api.get("/api/logs/")
    assert resp.status_code == 200
    entry = resp.data[0]
    for field in ["id", "client", "level", "message", "detail", "source", "client_ts", "created_at"]:
        assert field in entry
