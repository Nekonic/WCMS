"""게이트웨이 내부 API 검증 테스트.

모든 테스트는 pytest-django 와 DRF APIClient 를 사용한다.
인증은 settings.WCMS_INTERNAL_TOKEN 공유 베어러 토큰으로 수행한다.
"""
from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from django.conf import settings
from django.utils import timezone
from rest_framework.test import APIClient

from commands.models import Command
from fleet.models import Client, ClientDynamicInfo, NetworkEvent

TOKEN = settings.WCMS_INTERNAL_TOKEN
AUTH = f"Bearer {TOKEN}"
WRONG_AUTH = "Bearer wrong-token-xyz"


# ---------------------------------------------------------------------------
# 픽스처
# ---------------------------------------------------------------------------

@pytest.fixture
def api() -> APIClient:
    """올바른 베어러 토큰을 가진 APIClient."""
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=AUTH)
    return client


@pytest.fixture
def anon_api() -> APIClient:
    """인증 헤더 없는 APIClient."""
    return APIClient()


@pytest.fixture
def wrong_api() -> APIClient:
    """잘못된 베어러 토큰을 가진 APIClient."""
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=WRONG_AUTH)
    return c


@pytest.fixture
def pc(db) -> Client:
    """테스트용 Client 픽스처."""
    return Client.objects.create(hostname="test-pc-01")


@pytest.fixture
def command(db, pc) -> Command:
    """PENDING 상태의 큐 명령 픽스처."""
    return Command.objects.create(
        client=pc,
        command_type="shutdown",
        delivery_mode=Command.DeliveryMode.QUEUE,
        status=Command.Status.PENDING,
    )


# ---------------------------------------------------------------------------
# 인증 거부 테스트 (모든 엔드포인트)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@pytest.mark.parametrize("method,path,body", [
    ("post", "/internal/presence/", {"client_id": str(uuid.uuid4()), "event": "connect"}),
    ("post", "/internal/telemetry/heartbeat/",
     {"client_id": str(uuid.uuid4()), "full": False, "cpu_usage": 0.1, "ram_usage_percent": 0.1}),
    ("post", "/internal/telemetry/command-result/", {"command_id": 1, "status": "completed"}),
    ("post", "/internal/telemetry/command-ack/", {"command_id": 1}),
    ("get", f"/internal/clients/{uuid.uuid4()}/pending-commands/", None),
])
def test_missing_token_rejected(anon_api, method, path, body):
    """Authorization 헤더 없으면 401 또는 403 을 반환한다."""
    fn = getattr(anon_api, method)
    resp = fn(path, body, format="json") if body else fn(path)
    assert resp.status_code in (401, 403), f"{path}: got {resp.status_code}"


@pytest.mark.django_db
@pytest.mark.parametrize("method,path,body", [
    ("post", "/internal/presence/", {"client_id": str(uuid.uuid4()), "event": "connect"}),
    ("post", "/internal/telemetry/heartbeat/",
     {"client_id": str(uuid.uuid4()), "full": False, "cpu_usage": 0.1, "ram_usage_percent": 0.1}),
    ("post", "/internal/telemetry/command-result/", {"command_id": 1, "status": "completed"}),
    ("post", "/internal/telemetry/command-ack/", {"command_id": 1}),
    ("get", f"/internal/clients/{uuid.uuid4()}/pending-commands/", None),
])
def test_wrong_token_rejected(wrong_api, method, path, body):
    """잘못된 베어러 토큰은 401 또는 403 을 반환한다."""
    fn = getattr(wrong_api, method)
    resp = fn(path, body, format="json") if body else fn(path)
    assert resp.status_code in (401, 403), f"{path}: got {resp.status_code}"


# ---------------------------------------------------------------------------
# 프레즌스: connect
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_presence_connect_sets_online(api, pc):
    """connect 이벤트: Client.is_online=True, last_seen 갱신."""
    pc.is_online = False
    pc.save()

    resp = api.post(
        "/internal/presence/",
        {"client_id": str(pc.id), "event": "connect"},
        format="json",
    )
    assert resp.status_code == 204

    pc.refresh_from_db()
    assert pc.is_online is True
    assert pc.last_seen is not None


@pytest.mark.django_db
def test_presence_connect_closes_open_network_event(api, pc):
    """connect 이벤트: 열린 NetworkEvent(online_at is null)를 닫는다."""
    offline_at = timezone.now() - timedelta(minutes=10)
    event = NetworkEvent.objects.create(
        client=pc,
        offline_at=offline_at,
        reason="disconnect",
    )
    assert event.online_at is None

    connect_at = timezone.now()
    resp = api.post(
        "/internal/presence/",
        {"client_id": str(pc.id), "event": "connect", "at": connect_at.isoformat()},
        format="json",
    )
    assert resp.status_code == 204

    event.refresh_from_db()
    assert event.online_at is not None
    assert event.duration_sec is not None
    assert event.duration_sec >= 0


@pytest.mark.django_db
def test_presence_connect_unknown_client_404(api):
    """존재하지 않는 client_id: 404 반환."""
    resp = api.post(
        "/internal/presence/",
        {"client_id": str(uuid.uuid4()), "event": "connect"},
        format="json",
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 프레즌스: disconnect
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_presence_disconnect_sets_offline(api, pc):
    """disconnect 이벤트: Client.is_online=False."""
    pc.is_online = True
    pc.save()

    resp = api.post(
        "/internal/presence/",
        {"client_id": str(pc.id), "event": "disconnect"},
        format="json",
    )
    assert resp.status_code == 204

    pc.refresh_from_db()
    assert pc.is_online is False


@pytest.mark.django_db
def test_presence_disconnect_creates_network_event(api, pc):
    """disconnect 이벤트: 열린 NetworkEvent 없으면 새로 생성한다."""
    assert not NetworkEvent.objects.filter(client=pc, online_at__isnull=True).exists()

    resp = api.post(
        "/internal/presence/",
        {"client_id": str(pc.id), "event": "disconnect"},
        format="json",
    )
    assert resp.status_code == 204

    event = NetworkEvent.objects.filter(client=pc, online_at__isnull=True).first()
    assert event is not None
    assert event.reason == "disconnect"


@pytest.mark.django_db
def test_presence_disconnect_no_duplicate_event(api, pc):
    """disconnect 이벤트: 이미 열린 NetworkEvent 있으면 새로 생성하지 않는다."""
    NetworkEvent.objects.create(client=pc, offline_at=timezone.now(), reason="disconnect")
    count_before = NetworkEvent.objects.filter(client=pc, online_at__isnull=True).count()

    api.post(
        "/internal/presence/",
        {"client_id": str(pc.id), "event": "disconnect"},
        format="json",
    )

    count_after = NetworkEvent.objects.filter(client=pc, online_at__isnull=True).count()
    assert count_after == count_before


@pytest.mark.django_db
def test_presence_disconnect_unknown_client_404(api):
    """존재하지 않는 client_id: 404 반환."""
    resp = api.post(
        "/internal/presence/",
        {"client_id": str(uuid.uuid4()), "event": "disconnect"},
        format="json",
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 하트비트
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_heartbeat_light_creates_dynamic_info(api, pc):
    """라이트 하트비트: ClientDynamicInfo 생성 + Client.last_seen 갱신."""
    assert not ClientDynamicInfo.objects.filter(client=pc).exists()

    resp = api.post(
        "/internal/telemetry/heartbeat/",
        {
            "client_id": str(pc.id),
            "full": False,
            "cpu_usage": 12.5,
            "ram_usage_percent": 45.0,
        },
        format="json",
    )
    assert resp.status_code == 204

    dyn = ClientDynamicInfo.objects.get(client=pc)
    assert dyn.cpu_usage == pytest.approx(12.5)
    assert dyn.ram_usage_percent == pytest.approx(45.0)

    pc.refresh_from_db()
    assert pc.is_online is True
    assert pc.last_seen is not None


@pytest.mark.django_db
def test_heartbeat_light_updates_only_core_fields(api, pc):
    """라이트 하트비트: 기존 current_user 를 덮어쓰지 않는다."""
    ClientDynamicInfo.objects.create(
        client=pc,
        cpu_usage=5.0,
        ram_usage_percent=30.0,
        ram_used=4.0,
        uptime=1000,
        current_user="alice",
    )

    api.post(
        "/internal/telemetry/heartbeat/",
        {
            "client_id": str(pc.id),
            "full": False,
            "cpu_usage": 20.0,
            "ram_usage_percent": 60.0,
        },
        format="json",
    )

    dyn = ClientDynamicInfo.objects.get(client=pc)
    assert dyn.cpu_usage == pytest.approx(20.0)
    # current_user 는 라이트 업데이트 시 건드리지 않으므로 원래 값 유지
    assert dyn.current_user == "alice"


@pytest.mark.django_db
def test_heartbeat_full_upserts_all_fields(api, pc):
    """풀 하트비트: 모든 제공 필드를 저장한다."""
    resp = api.post(
        "/internal/telemetry/heartbeat/",
        {
            "client_id": str(pc.id),
            "full": True,
            "cpu_usage": 33.3,
            "ram_usage_percent": 55.5,
            "ram_used": 8.0,
            "disk_usage": {"C:": {"total": 500, "used": 200}},
            "current_user": "bob",
            "uptime": 3600,
            "processes": [{"name": "explorer.exe", "pid": 100}],
            "ip_address": "192.168.1.10",
        },
        format="json",
    )
    assert resp.status_code == 204

    dyn = ClientDynamicInfo.objects.get(client=pc)
    assert dyn.cpu_usage == pytest.approx(33.3)
    assert dyn.ram_used == pytest.approx(8.0)
    assert dyn.current_user == "bob"
    assert dyn.uptime == 3600
    assert dyn.processes == [{"name": "explorer.exe", "pid": 100}]

    pc.refresh_from_db()
    assert str(pc.ip_address) == "192.168.1.10"


@pytest.mark.django_db
def test_heartbeat_ip_address_updated(api, pc):
    """ip_address 가 제공되면 Client.ip_address 를 갱신한다."""
    resp = api.post(
        "/internal/telemetry/heartbeat/",
        {
            "client_id": str(pc.id),
            "full": False,
            "cpu_usage": 1.0,
            "ram_usage_percent": 1.0,
            "ip_address": "10.0.0.5",
        },
        format="json",
    )
    assert resp.status_code == 204
    pc.refresh_from_db()
    assert str(pc.ip_address) == "10.0.0.5"


@pytest.mark.django_db
def test_heartbeat_unknown_client_404(api):
    """존재하지 않는 client_id: 404 반환."""
    resp = api.post(
        "/internal/telemetry/heartbeat/",
        {
            "client_id": str(uuid.uuid4()),
            "full": False,
            "cpu_usage": 0.0,
            "ram_usage_percent": 0.0,
        },
        format="json",
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 명령 결과
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_command_result_completed(api, command):
    """completed 결과: Command.status=COMPLETED, completed_at 설정."""
    resp = api.post(
        "/internal/telemetry/command-result/",
        {"command_id": command.id, "status": "completed", "output": "ok"},
        format="json",
    )
    assert resp.status_code == 204

    command.refresh_from_db()
    assert command.status == Command.Status.COMPLETED
    assert command.completed_at is not None
    assert command.result == "ok"


@pytest.mark.django_db
def test_command_result_error(api, command):
    """error 결과: Command.status=ERROR, error_message 설정."""
    resp = api.post(
        "/internal/telemetry/command-result/",
        {
            "command_id": command.id,
            "status": "error",
            "error_message": "connection refused",
        },
        format="json",
    )
    assert resp.status_code == 204

    command.refresh_from_db()
    assert command.status == Command.Status.ERROR
    assert command.error_message == "connection refused"
    assert command.completed_at is not None


@pytest.mark.django_db
def test_command_result_timeout(api, command):
    """timeout 결과: Command.status=TIMEOUT."""
    resp = api.post(
        "/internal/telemetry/command-result/",
        {"command_id": command.id, "status": "timeout"},
        format="json",
    )
    assert resp.status_code == 204

    command.refresh_from_db()
    assert command.status == Command.Status.TIMEOUT


@pytest.mark.django_db
def test_command_result_unknown_command_404(api):
    """존재하지 않는 command_id: 404 반환."""
    resp = api.post(
        "/internal/telemetry/command-result/",
        {"command_id": 99999, "status": "completed"},
        format="json",
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 명령 ACK
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_command_ack_sets_sent(api, command):
    """PENDING 명령에 ACK: status=SENT, sent_at 설정."""
    resp = api.post(
        "/internal/telemetry/command-ack/",
        {"command_id": command.id},
        format="json",
    )
    assert resp.status_code == 204

    command.refresh_from_db()
    assert command.status == Command.Status.SENT
    assert command.sent_at is not None


@pytest.mark.django_db
def test_command_ack_already_sent_idempotent(api, pc):
    """이미 SENT 상태인 명령에 ACK: 상태 변경 없이 204 반환."""
    cmd = Command.objects.create(
        client=pc,
        command_type="restart",
        status=Command.Status.SENT,
    )
    resp = api.post(
        "/internal/telemetry/command-ack/",
        {"command_id": cmd.id},
        format="json",
    )
    assert resp.status_code == 204
    cmd.refresh_from_db()
    assert cmd.status == Command.Status.SENT


@pytest.mark.django_db
def test_command_ack_unknown_command_404(api):
    """존재하지 않는 command_id: 404 반환."""
    resp = api.post(
        "/internal/telemetry/command-ack/",
        {"command_id": 99999},
        format="json",
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 대기 중 명령 목록
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_pending_commands_returns_queue_pending(api, pc):
    """큐 + 대기 중 명령만 반환한다."""
    q_cmd = Command.objects.create(
        client=pc,
        command_type="install",
        delivery_mode=Command.DeliveryMode.QUEUE,
        status=Command.Status.PENDING,
    )
    # drop_if_offline 명령 → 반환 안 됨
    Command.objects.create(
        client=pc,
        command_type="shutdown",
        delivery_mode=Command.DeliveryMode.DROP_IF_OFFLINE,
        status=Command.Status.PENDING,
    )
    # SENT 상태 → 반환 안 됨
    Command.objects.create(
        client=pc,
        command_type="restart",
        delivery_mode=Command.DeliveryMode.QUEUE,
        status=Command.Status.SENT,
    )

    resp = api.get(f"/internal/clients/{pc.id}/pending-commands/")
    assert resp.status_code == 200
    assert len(resp.data) == 1
    assert resp.data[0]["id"] == q_cmd.id
    assert resp.data[0]["command_type"] == "install"


@pytest.mark.django_db
def test_pending_commands_excludes_expired(api, pc):
    """만료된 명령(expires_at < now)은 반환하지 않는다."""
    # 유효한 명령
    valid_cmd = Command.objects.create(
        client=pc,
        command_type="install",
        delivery_mode=Command.DeliveryMode.QUEUE,
        status=Command.Status.PENDING,
        expires_at=timezone.now() + timedelta(hours=1),
    )
    # 만료된 명령
    Command.objects.create(
        client=pc,
        command_type="update",
        delivery_mode=Command.DeliveryMode.QUEUE,
        status=Command.Status.PENDING,
        expires_at=timezone.now() - timedelta(hours=1),
    )
    # expires_at=None → TTL 없음, 반환됨
    no_ttl_cmd = Command.objects.create(
        client=pc,
        command_type="scan",
        delivery_mode=Command.DeliveryMode.QUEUE,
        status=Command.Status.PENDING,
        expires_at=None,
    )

    resp = api.get(f"/internal/clients/{pc.id}/pending-commands/")
    assert resp.status_code == 200
    returned_ids = {item["id"] for item in resp.data}
    assert valid_cmd.id in returned_ids
    assert no_ttl_cmd.id in returned_ids
    assert len(returned_ids) == 2


@pytest.mark.django_db
def test_pending_commands_ordered_by_priority_then_created(api, pc):
    """priority ASC, created_at ASC 순서로 정렬된다."""
    cmd_low_pri = Command.objects.create(
        client=pc, command_type="a",
        delivery_mode=Command.DeliveryMode.QUEUE,
        status=Command.Status.PENDING, priority=10,
    )
    cmd_high_pri = Command.objects.create(
        client=pc, command_type="b",
        delivery_mode=Command.DeliveryMode.QUEUE,
        status=Command.Status.PENDING, priority=1,
    )

    resp = api.get(f"/internal/clients/{pc.id}/pending-commands/")
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.data]
    assert ids[0] == cmd_high_pri.id
    assert ids[1] == cmd_low_pri.id


@pytest.mark.django_db
def test_pending_commands_response_fields(api, pc):
    """응답 항목에 필요한 필드가 포함되어 있다."""
    Command.objects.create(
        client=pc, command_type="check",
        delivery_mode=Command.DeliveryMode.QUEUE,
        status=Command.Status.PENDING,
        parameters={"key": "val"},
        priority=3,
        timeout_seconds=120,
    )

    resp = api.get(f"/internal/clients/{pc.id}/pending-commands/")
    assert resp.status_code == 200
    item = resp.data[0]
    assert "id" in item
    assert "command_type" in item
    assert "parameters" in item
    assert "priority" in item
    assert "timeout_seconds" in item
    assert "created_at" in item


@pytest.mark.django_db
def test_pending_commands_unknown_client_404(api):
    """존재하지 않는 client_id: 404 반환."""
    resp = api.get(f"/internal/clients/{uuid.uuid4()}/pending-commands/")
    assert resp.status_code == 404
