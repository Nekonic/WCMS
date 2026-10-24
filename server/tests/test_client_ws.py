import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator

from labs.models import PC
from wcms.asgi import application

pytestmark = pytest.mark.django_db(transaction=True)


@database_sync_to_async
def make_pc() -> tuple[PC, str]:
    return PC.register(hostname="LAB-01", machine_guid="g1", specs={}, version="2026.1")


@database_sync_to_async
def reload(pc_id: int) -> PC:
    return PC.objects.get(pk=pc_id)


def communicator(token: str | None) -> WebsocketCommunicator:
    headers = [(b"authorization", f"Bearer {token}".encode())] if token else []
    return WebsocketCommunicator(application, "/client/ws", headers=headers)


async def test_rejects_missing_token():
    connected, _ = await communicator(None).connect()
    assert not connected


async def test_rejects_wrong_token():
    await make_pc()
    connected, _ = await communicator("wrong").connect()
    assert not connected


async def test_connect_and_disconnect_toggle_online():
    pc, token = await make_pc()
    ws = communicator(token)
    connected, _ = await ws.connect()
    assert connected
    assert (await reload(pc.id)).online is True
    await ws.disconnect()
    assert (await reload(pc.id)).online is False


async def test_status_is_cleaned_and_stored():
    pc, token = await make_pc()
    ws = communicator(token)
    await ws.connect()
    await ws.send_json_to(
        {
            "type": "status",
            "cpu": 12.5,
            "mem_used": -1,
            "user": "Student",
            "session": "weird",
            "foreground": {"process": "chrome.exe", "title": "x" * 500},
            "evil": True,
        }
    )
    await ws.send_json_to({"type": "ping"})
    assert await ws.receive_json_from() == {"type": "pong"}

    stored = (await reload(pc.id)).status
    assert stored["cpu"] == 12.5
    assert "mem_used" not in stored
    assert stored["session"] == "none"
    assert len(stored["foreground"]["title"]) == 256
    assert "evil" not in stored
    await ws.disconnect()


async def test_hello_stores_version():
    pc, token = await make_pc()
    ws = communicator(token)
    await ws.connect()
    await ws.send_json_to({"type": "hello", "version": "2026.2"})
    await ws.send_json_to({"type": "ping"})
    await ws.receive_json_from()
    assert (await reload(pc.id)).client_version == "2026.2"
    await ws.disconnect()


async def test_unknown_type_returns_error():
    _, token = await make_pc()
    ws = communicator(token)
    await ws.connect()
    await ws.send_json_to({"type": "nope"})
    assert await ws.receive_json_from() == {"type": "error", "error": "unknown_type"}
    await ws.disconnect()


async def test_new_connection_supersedes_old():
    pc, token = await make_pc()
    first = communicator(token)
    await first.connect()
    second = communicator(token)
    await second.connect()

    closed = await first.receive_output(timeout=1)
    assert closed["type"] == "websocket.close"
    assert closed["code"] == 4409
    await first.disconnect()

    assert (await reload(pc.id)).online is True
    await second.disconnect()
    assert (await reload(pc.id)).online is False


async def test_invalid_json_returns_error_and_keeps_connection():
    pc, token = await make_pc()
    ws = communicator(token)
    await ws.connect()
    await ws.send_to(text_data="{not json")
    assert await ws.receive_json_from() == {"type": "error", "error": "bad_json"}
    await ws.send_json_to({"type": "ping"})
    assert await ws.receive_json_from() == {"type": "pong"}
    assert (await reload(pc.id)).online is True
    await ws.disconnect()
    assert (await reload(pc.id)).online is False


async def test_binary_frame_returns_error():
    _, token = await make_pc()
    ws = communicator(token)
    await ws.connect()
    await ws.send_to(bytes_data=b"\x00\x01")
    assert await ws.receive_json_from() == {"type": "error", "error": "bad_json"}
    await ws.disconnect()
