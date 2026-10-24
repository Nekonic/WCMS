import json
from pathlib import Path

import pytest
from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from django.test import override_settings

from agent import consumers, protocol, state
from labs.models import PC
from wcms.asgi import application
from wcms.groups import pc_group

pytestmark = pytest.mark.django_db(transaction=True)
EXAMPLES = Path(__file__).resolve().parents[2] / "protocol" / "examples"


@pytest.fixture(autouse=True)
def fresh_locks():
    # asyncio.Lock은 처음 경합한 이벤트 루프에 묶이므로 테스트마다 비운다
    consumers._locks.clear()


def example(name: str) -> dict:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


@database_sync_to_async
def make_pc() -> tuple[PC, str]:
    return PC.register(hostname="LAB-01", machine_guid="g1", specs={}, version="2026.1")


def connect(token: str | None, internal: bool = False) -> WebsocketCommunicator:
    headers = [(b"authorization", f"Bearer {token}".encode())] if token else []
    if internal:
        headers.append((b"x-wcms-via", b"internal"))
    return WebsocketCommunicator(application, "/client/ws", headers=headers)


async def open_with_hello(token: str) -> WebsocketCommunicator:
    ws = connect(token)
    connected, _ = await ws.connect()
    assert connected
    await ws.send_json_to(example("hello.json"))
    return ws


async def sync(ws: WebsocketCommunicator) -> None:
    await ws.send_json_to(example("ping.json"))
    assert await ws.receive_json_from() == example("pong.json")


async def current_state(pc_id: int) -> dict:
    return await sync_to_async(state.get_state)(pc_id)


@pytest.fixture(autouse=True)
def no_status_throttle(monkeypatch):
    monkeypatch.setattr(protocol, "STATUS_MIN_INTERVAL", 0.0)


async def test_rejects_missing_and_wrong_token():
    await make_pc()
    assert (await connect(None).connect())[0] is False
    assert (await connect("wrong").connect())[0] is False


async def test_rejects_non_internal_when_required():
    _, token = await make_pc()
    with override_settings(WCMS_REQUIRE_INTERNAL=True):
        assert (await connect(token).connect())[0] is False
        ws = connect(token, internal=True)
        assert (await ws.connect())[0] is True
        await ws.disconnect()


async def test_first_message_must_be_hello():
    _, token = await make_pc()
    ws = connect(token)
    await ws.connect()
    await ws.send_json_to(example("ping.json"))
    closed = await ws.receive_output(timeout=1)
    assert closed["type"] == "websocket.close" and closed["code"] == protocol.CLOSE_HELLO_REQUIRED


async def test_unsupported_proto():
    _, token = await make_pc()
    ws = connect(token)
    await ws.connect()
    await ws.send_json_to({"type": "hello", "proto": 99, "version": "x"})
    closed = await ws.receive_output(timeout=1)
    assert closed["code"] == protocol.CLOSE_UNSUPPORTED_PROTO


async def test_connect_status_disconnect():
    pc, token = await make_pc()
    ws = await open_with_hello(token)
    await sync(ws)
    assert (await current_state(pc.id))["online"] is True
    await ws.send_json_to(example("status.json"))
    await sync(ws)
    status = (await current_state(pc.id))["status"]
    assert status["user"] == "Student" and status["cpu"] == 12.5
    await ws.disconnect()
    assert (await current_state(pc.id))["online"] is False


async def test_hello_saves_version():
    pc, token = await make_pc()
    ws = connect(token)
    await ws.connect()
    await ws.send_json_to({"type": "hello", "proto": 1, "version": "2026.9"})
    await sync(ws)
    refreshed = await database_sync_to_async(PC.objects.get)(pk=pc.id)
    assert refreshed.client_version == "2026.9"
    await ws.disconnect()


async def test_status_too_frequent_is_dropped(monkeypatch):
    monkeypatch.setattr(protocol, "STATUS_MIN_INTERVAL", 60.0)
    pc, token = await make_pc()
    ws = await open_with_hello(token)
    await ws.send_json_to({"type": "status", "cpu": 1})
    await ws.send_json_to({"type": "status", "cpu": 2})
    await sync(ws)
    assert (await current_state(pc.id))["status"]["cpu"] == 1
    await ws.disconnect()


async def test_bad_frames_keep_connection():
    _, token = await make_pc()
    ws = await open_with_hello(token)
    await ws.send_to(text_data="{not json")
    assert await ws.receive_json_from() == example("error_bad_json.json")
    await ws.send_to(bytes_data=b"\x01\x00")
    assert await ws.receive_json_from() == example("error_binary_not_supported.json")
    await ws.send_json_to({"type": "nope"})
    assert await ws.receive_json_from() == example("error_unknown_type.json")
    await sync(ws)
    await ws.disconnect()


async def test_new_connection_supersedes_old():
    pc, token = await make_pc()
    first = await open_with_hello(token)
    await sync(first)
    second = await open_with_hello(token)
    closed = await first.receive_output(timeout=1)
    assert closed["code"] == protocol.CLOSE_SUPERSEDED
    await first.disconnect()
    await sync(second)
    assert (await current_state(pc.id))["online"] is True
    await second.disconnect()


async def test_revoked_closes_connection():
    pc, token = await make_pc()
    ws = await open_with_hello(token)
    await sync(ws)
    await get_channel_layer().group_send(pc_group(pc.id), {"type": "pc.revoked"})
    closed = await ws.receive_output(timeout=1)
    assert closed["code"] == protocol.CLOSE_REVOKED
