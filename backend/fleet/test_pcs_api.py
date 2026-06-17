"""PC(Client) 조회 API 검증."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from fleet.models import Client, ClientDynamicInfo, ClientSpecs, Room

User = get_user_model()
PW = "contract-pw-123!"


@pytest.fixture
def auth_api(db):
    User.objects.create_user("admin", password=PW)
    api = APIClient()
    assert api.login(username="admin", password=PW)
    return api


@pytest.mark.django_db
def test_pcs_list_requires_auth():
    assert APIClient().get("/api/pcs/").status_code in (401, 403)


@pytest.mark.django_db
def test_pcs_list_and_filters(auth_api):
    room = Room.objects.create(name="1실습실")
    Client.objects.create(hostname="PC-1", room=room, is_online=True)
    Client.objects.create(hostname="PC-2", is_online=False)

    resp = auth_api.get("/api/pcs/")
    assert resp.status_code == 200
    assert {c["hostname"] for c in resp.data} == {"PC-1", "PC-2"}
    # 목록 직렬화에 room 이름이 들어간다
    pc1 = next(c for c in resp.data if c["hostname"] == "PC-1")
    assert pc1["room"] == "1실습실"

    assert {c["hostname"] for c in auth_api.get("/api/pcs/?room=1실습실").data} == {"PC-1"}
    assert {c["hostname"] for c in auth_api.get("/api/pcs/?online=true").data} == {"PC-1"}


@pytest.mark.django_db
def test_pc_detail_includes_specs_and_dynamic(auth_api):
    client = Client.objects.create(hostname="PC-1")
    ClientSpecs.objects.create(
        client=client, cpu_model="i5", cpu_cores=4, cpu_threads=8,
        ram_total=16.0, disk_info={"C:": {"total_gb": 237.0}},
        os_edition="Win11 Pro", os_version="23H2",
    )
    ClientDynamicInfo.objects.create(
        client=client, cpu_usage=12.5, ram_used=6.0, ram_usage_percent=40.0, uptime=3600,
    )
    resp = auth_api.get(f"/api/pcs/{client.id}/")
    assert resp.status_code == 200
    assert resp.data["specs"]["cpu_model"] == "i5"
    assert resp.data["dynamic"]["cpu_usage"] == 12.5


@pytest.mark.django_db
def test_pc_detail_without_specs_returns_null(auth_api):
    client = Client.objects.create(hostname="PC-bare")
    resp = auth_api.get(f"/api/pcs/{client.id}/")
    assert resp.status_code == 200
    assert resp.data["specs"] is None
    assert resp.data["dynamic"] is None


@pytest.mark.django_db
def test_pc_delete(auth_api):
    client = Client.objects.create(hostname="PC-X")
    assert auth_api.delete(f"/api/pcs/{client.id}/").status_code == 204
    assert not Client.objects.filter(id=client.id).exists()
