"""명령 발행/조회 API 검증."""
import pytest
from unittest.mock import MagicMock, patch
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from commands.models import Command
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
def test_issue_command_requires_auth(pc):
    resp = APIClient().post(f"/api/pcs/{pc.id}/commands/", {"command_type": "shutdown"}, format="json")
    assert resp.status_code in (401, 403)


@pytest.mark.django_db
def test_issue_time_sensitive_command_is_drop(auth_api, pc):
    # pc 는 기본적으로 오프라인(is_online=False). drop_if_offline 명령은 즉시 EXPIRED 처리.
    with patch("commands.services.requests.post") as mock_post:
        resp = auth_api.post(f"/api/pcs/{pc.id}/commands/",
                             {"command_type": "shutdown", "parameters": {"delay": 0}}, format="json")
    assert resp.status_code == 201
    assert resp.data["command_type"] == "shutdown"
    assert resp.data["delivery_mode"] == Command.DeliveryMode.DROP_IF_OFFLINE
    assert resp.data["status"] == Command.Status.EXPIRED  # 오프라인 + drop -> 즉시 폐기
    assert resp.data["issuer"] == "admin"
    assert resp.data["expires_at"] is None
    assert resp.data["parameters"] == {"delay": 0}
    mock_post.assert_not_called()  # 오프라인이므로 게이트웨이 push 없음


@pytest.mark.django_db
def test_issue_install_command_is_queue_with_ttl(auth_api, pc):
    resp = auth_api.post(f"/api/pcs/{pc.id}/commands/",
                         {"command_type": "install", "parameters": {"package": "vscode"}}, format="json")
    assert resp.status_code == 201
    assert resp.data["delivery_mode"] == Command.DeliveryMode.QUEUE
    assert resp.data["expires_at"] is not None


@pytest.mark.django_db
def test_issue_command_explicit_delivery_mode_overrides(auth_api, pc):
    resp = auth_api.post(f"/api/pcs/{pc.id}/commands/",
                         {"command_type": "shutdown", "delivery_mode": "queue"}, format="json")
    assert resp.status_code == 201
    assert resp.data["delivery_mode"] == Command.DeliveryMode.QUEUE


@pytest.mark.django_db
def test_issue_unknown_pc_returns_404(auth_api):
    import uuid
    resp = auth_api.post(f"/api/pcs/{uuid.uuid4()}/commands/",
                         {"command_type": "shutdown"}, format="json")
    assert resp.status_code == 404


@pytest.mark.django_db
def test_list_commands_for_pc(auth_api, pc):
    auth_api.post(f"/api/pcs/{pc.id}/commands/", {"command_type": "shutdown"}, format="json")
    auth_api.post(f"/api/pcs/{pc.id}/commands/", {"command_type": "restart"}, format="json")
    resp = auth_api.get(f"/api/pcs/{pc.id}/commands/")
    assert resp.status_code == 200
    assert len(resp.data) == 2
    assert {c["command_type"] for c in resp.data} == {"shutdown", "restart"}


@pytest.mark.django_db
def test_bulk_command_issues_to_all(auth_api):
    c1 = Client.objects.create(hostname="PC-1")
    c2 = Client.objects.create(hostname="PC-2")
    resp = auth_api.post("/api/commands/bulk/",
                         {"pc_ids": [str(c1.id), str(c2.id)], "command_type": "shutdown"},
                         format="json")
    assert resp.status_code == 201
    assert resp.data["created"] == 2
    assert Command.objects.filter(command_type="shutdown").count() == 2


@pytest.mark.django_db
def test_bulk_command_requires_pc_ids(auth_api):
    resp = auth_api.post("/api/commands/bulk/", {"command_type": "shutdown"}, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_command_audit_list_with_status_filter(auth_api, pc):
    # queue 모드 명령(install)은 오프라인이어도 PENDING 유지 -> status=pending 필터 검증.
    with patch("commands.services.requests.post"):
        auth_api.post(f"/api/pcs/{pc.id}/commands/", {"command_type": "install"}, format="json")
    resp = auth_api.get("/api/commands/?status=pending")
    assert resp.status_code == 200
    assert len(resp.data) == 1
    assert resp.data[0]["issuer"] == "admin"
