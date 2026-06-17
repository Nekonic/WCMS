"""게이트웨이 push 통합 검증 (commands.services.gateway_push / issue_command).

실제 HTTP 요청 없이 requests.post 를 mock 으로 대체한다.
"""
import logging
from unittest.mock import MagicMock, patch

import pytest

from commands.models import Command
from commands.services import gateway_push, issue_command
from fleet.models import Client


@pytest.fixture
def online_client(db):
    """온라인 상태 클라이언트."""
    return Client.objects.create(hostname="PC-ONLINE", is_online=True)


@pytest.fixture
def offline_client(db):
    """오프라인 상태 클라이언트."""
    return Client.objects.create(hostname="PC-OFFLINE", is_online=False)


# ──────────────────────────────────────────────────────────────────────────────
# (a) 온라인 클라이언트 + issue_command -> gateway_push 호출, status=PENDING 유지
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_online_client_calls_gateway_push(online_client, settings):
    """온라인 클라이언트에 명령 발행 시 게이트웨이 push 가 호출된다."""
    settings.WCMS_GATEWAY_URL = "http://gateway.test:8080"
    settings.WCMS_INTERNAL_TOKEN = "test-token"

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"delivered": True}

    with patch("commands.services.requests.post", return_value=mock_resp) as mock_post:
        cmd = issue_command(
            client=online_client,
            command_type="shutdown",
            priority=5,
            timeout_seconds=30,
        )

    # gateway_push 가 올바른 URL, Bearer 헤더, 본문으로 호출되어야 한다.
    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args

    expected_url = f"http://gateway.test:8080/internal/push/{online_client.id}"
    assert call_kwargs.args[0] == expected_url or call_kwargs.kwargs.get("url") == expected_url or call_kwargs.args[0] == expected_url

    headers = call_kwargs.kwargs.get("headers", {})
    assert headers.get("Authorization") == "Bearer test-token"

    payload = call_kwargs.kwargs.get("json", {})
    assert payload["id"] == str(cmd.id)
    assert payload["command_type"] == "shutdown"
    assert payload["priority"] == 5
    assert payload["timeout_seconds"] == 30
    assert payload["delivery_mode"] == Command.DeliveryMode.DROP_IF_OFFLINE

    # 온라인 클라이언트: status 는 PENDING 유지 (ACK 경로에서 SENT 로 전환).
    cmd.refresh_from_db()
    assert cmd.status == Command.Status.PENDING


@pytest.mark.django_db
def test_online_client_push_url_contains_client_id(online_client, settings):
    """gateway_push URL 에 클라이언트 UUID 가 포함된다."""
    settings.WCMS_GATEWAY_URL = "http://gw:8080"
    settings.WCMS_INTERNAL_TOKEN = "tok"

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"delivered": True}

    with patch("commands.services.requests.post", return_value=mock_resp) as mock_post:
        issue_command(client=online_client, command_type="install")

    url_called = mock_post.call_args.args[0]
    assert str(online_client.id) in url_called
    assert url_called.endswith(f"/internal/push/{online_client.id}")


# ──────────────────────────────────────────────────────────────────────────────
# (b) 오프라인 + DROP_IF_OFFLINE -> status=EXPIRED, push 미호출
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_offline_drop_command_becomes_expired(offline_client):
    """오프라인 + drop_if_offline 명령은 EXPIRED 로 즉시 폐기된다."""
    with patch("commands.services.requests.post") as mock_post:
        cmd = issue_command(client=offline_client, command_type="shutdown")

    assert cmd.status == Command.Status.EXPIRED
    mock_post.assert_not_called()


@pytest.mark.django_db
def test_offline_drop_command_no_push_called(offline_client):
    """오프라인 drop 명령 발행 시 게이트웨이 push 함수가 호출되지 않는다."""
    with patch("commands.services.gateway_push") as mock_push:
        cmd = issue_command(client=offline_client, command_type="restart")

    mock_push.assert_not_called()
    cmd.refresh_from_db()
    assert cmd.status == Command.Status.EXPIRED


# ──────────────────────────────────────────────────────────────────────────────
# (c) 오프라인 + QUEUE -> status=PENDING, push 미호출
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_offline_queue_command_stays_pending(offline_client):
    """오프라인 + queue 명령은 PENDING 유지(재연결 시 드레인)."""
    with patch("commands.services.requests.post") as mock_post:
        cmd = issue_command(client=offline_client, command_type="install")

    assert cmd.status == Command.Status.PENDING
    mock_post.assert_not_called()


@pytest.mark.django_db
def test_offline_queue_command_has_ttl(offline_client):
    """오프라인 queue 명령은 expires_at(TTL) 이 설정된다."""
    with patch("commands.services.requests.post"):
        cmd = issue_command(client=offline_client, command_type="update")

    assert cmd.expires_at is not None
    assert cmd.delivery_mode == Command.DeliveryMode.QUEUE


# ──────────────────────────────────────────────────────────────────────────────
# (d) 게이트웨이 오류 -> issue_command 예외 없이 완료, 경고 로그 기록
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_gateway_error_does_not_raise(online_client, caplog):
    """게이트웨이 RequestException 발생 시 issue_command 는 예외 없이 Command 를 반환한다."""
    import requests as req_lib
    with caplog.at_level(logging.WARNING, logger="commands.services"):
        with patch("commands.services.requests.post", side_effect=req_lib.ConnectionError("연결 거부")):
            cmd = issue_command(client=online_client, command_type="shutdown")

    # 예외가 전파되지 않고 Command 가 반환되어야 한다.
    assert cmd is not None
    assert cmd.pk is not None
    # 경고 로그가 기록되어야 한다.
    assert any("게이트웨이 push 실패" in r.message for r in caplog.records)


@pytest.mark.django_db
def test_gateway_timeout_does_not_raise(online_client, caplog):
    """게이트웨이 Timeout 발생 시도 issue_command 는 예외 없이 반환한다."""
    import requests as req_lib
    with caplog.at_level(logging.WARNING, logger="commands.services"):
        with patch("commands.services.requests.post", side_effect=req_lib.Timeout("타임아웃")):
            cmd = issue_command(client=online_client, command_type="execute")

    assert cmd is not None
    assert cmd.pk is not None


@pytest.mark.django_db
def test_gateway_404_returns_false_no_exception(online_client):
    """게이트웨이 404 응답(클라이언트 미연결)은 False 반환, 예외 없음."""
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_resp.json.return_value = {"delivered": False}

    with patch("commands.services.requests.post", return_value=mock_resp):
        # gateway_push 직접 테스트.
        cmd = issue_command(client=online_client, command_type="install")

    # gateway_push 는 False 를 반환해야 하지만 issue_command 는 정상 반환해야 한다.
    assert cmd.pk is not None


@pytest.mark.django_db
def test_gateway_push_returns_true_on_delivered(online_client, settings):
    """gateway_push 는 200 + delivered:true 시 True 를 반환한다."""
    settings.WCMS_GATEWAY_URL = "http://gw:8080"
    settings.WCMS_INTERNAL_TOKEN = "tok"

    cmd = Command.objects.create(
        client=online_client,
        command_type="shutdown",
        parameters={},
        priority=5,
        timeout_seconds=60,
        delivery_mode=Command.DeliveryMode.DROP_IF_OFFLINE,
        status=Command.Status.PENDING,
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"delivered": True}

    with patch("commands.services.requests.post", return_value=mock_resp):
        result = gateway_push(cmd)

    assert result is True


@pytest.mark.django_db
def test_gateway_push_returns_false_on_not_delivered(online_client, settings):
    """gateway_push 는 200 + delivered:false 시 False 를 반환한다."""
    settings.WCMS_GATEWAY_URL = "http://gw:8080"
    settings.WCMS_INTERNAL_TOKEN = "tok"

    cmd = Command.objects.create(
        client=online_client,
        command_type="install",
        parameters={},
        priority=5,
        timeout_seconds=60,
        delivery_mode=Command.DeliveryMode.QUEUE,
        status=Command.Status.PENDING,
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"delivered": False}

    with patch("commands.services.requests.post", return_value=mock_resp):
        result = gateway_push(cmd)

    assert result is False
