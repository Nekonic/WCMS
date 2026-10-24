import asyncio
import json
from pathlib import Path

import pytest
from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from django.core.cache import cache
from django.test import override_settings

from agent import consumers, protocol, state
from labs.models import PC, Room
from wcms.asgi import application
from wcms.groups import pc_group, room_public_group

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
    monkeypatch.setattr(protocol, "PING_REFRESH_INTERVAL", 0.0)


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


async def test_unsupported_proto_types():
    _, token = await make_pc()
    for proto in (True, 1.0, "1"):
        ws = connect(token)
        await ws.connect()
        await ws.send_json_to({"type": "hello", "proto": proto})
        closed = await ws.receive_output(timeout=1)
        assert closed["code"] == protocol.CLOSE_UNSUPPORTED_PROTO, proto


async def test_unencodable_version_is_ignored():
    pc, token = await make_pc()
    ws = connect(token)
    await ws.connect()
    await ws.send_to(text_data='{"type":"hello","proto":1,"version":"\\ud800"}')
    await sync(ws)
    assert (await current_state(pc.id))["online"] is True
    refreshed = await database_sync_to_async(PC.objects.get)(pk=pc.id)
    assert refreshed.client_version == "2026.1"
    await ws.disconnect()


async def test_handler_exception_closes_and_cleans_up(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    pc, token = await make_pc()
    ws = await open_with_hello(token)
    await sync(ws)
    monkeypatch.setattr(state, "save_status", boom)
    await ws.send_json_to(example("status.json"))
    closed = await ws.receive_output(timeout=1)
    assert closed["type"] == "websocket.close" and closed["code"] == 1011
    await ws.disconnect()
    assert (await current_state(pc.id))["online"] is False


async def test_simultaneous_connections_leave_exactly_one(monkeypatch):
    layer = get_channel_layer()
    original = type(layer).group_send

    async def yielding_group_send(self, group, message):
        await original(self, group, message)
        await asyncio.sleep(0)  # 시간 지연이 아니라 다른 연결에 실행을 넘겨 경합을 만든다

    monkeypatch.setattr(type(layer), "group_send", yielding_group_send)
    pc, token = await make_pc()
    a, b = connect(token), connect(token)
    results = await asyncio.gather(a.connect(), b.connect())
    assert all(connected for connected, _ in results)
    for ws in (a, b):
        await ws.send_json_to(example("hello.json"))
        await ws.send_json_to(example("ping.json"))
    # 한쪽은 4409 종료, 다른 쪽은 pong. 첫 출력만 읽으므로 시간 초과로 앱이 취소되는 일이 없다
    first_a, first_b = await asyncio.gather(a.receive_output(timeout=1), b.receive_output(timeout=1))
    closed = [o for o in (first_a, first_b) if o["type"] == "websocket.close"]
    assert [o["code"] for o in closed] == [protocol.CLOSE_SUPERSEDED]
    survivor, loser = (b, a) if first_a["type"] == "websocket.close" else (a, b)
    await loser.disconnect()
    assert (await current_state(pc.id))["online"] is True
    await survivor.disconnect()
    assert (await current_state(pc.id))["online"] is False


@database_sync_to_async
def make_seated_pc() -> tuple[PC, str]:
    room = Room.objects.create(name="301", rows=1, cols=1)
    pc, token = PC.register(hostname="LAB-01", machine_guid="g1", specs={}, version="2026.1")
    pc.room, pc.row, pc.col = room, 0, 0
    pc.save()
    return pc, token


async def connection_of(pc_id: int) -> str:
    return (await sync_to_async(cache.get)(f"pcstate:{pc_id}"))["connection"]


async def listen(group: str) -> str:
    layer = get_channel_layer()
    channel = await layer.new_channel()
    await layer.group_add(group, channel)
    return channel


async def drain(channel: str) -> list[dict]:
    messages = []
    while True:
        try:
            messages.append(await asyncio.wait_for(get_channel_layer().receive(channel), 0.2))
        except asyncio.TimeoutError:
            return messages


async def test_ping_rejoins_expired_group():
    # 채널 레이어는 group_expiry가 지나거나 Redis가 재시작되면 그룹 가입을 잊는다
    pc, token = await make_pc()
    layer = get_channel_layer()
    first = await open_with_hello(token)
    await sync(first)
    await layer.group_discard(pc_group(pc.id), await connection_of(pc.id))
    await sync(first)
    second = await open_with_hello(token)
    closed = await first.receive_output(timeout=1)
    assert closed["code"] == protocol.CLOSE_SUPERSEDED
    await first.disconnect()

    await sync(second)
    await layer.group_discard(pc_group(pc.id), await connection_of(pc.id))
    await sync(second)
    await layer.group_send(pc_group(pc.id), {"type": "pc.revoked"})
    closed = await second.receive_output(timeout=1)
    assert closed["code"] == protocol.CLOSE_REVOKED


async def test_status_after_state_loss_brings_pc_back_online():
    pc, token = await make_seated_pc()
    ws = await open_with_hello(token)
    await sync(ws)
    public = await listen(room_public_group(pc.room_id))
    await sync_to_async(cache.delete)(f"pcstate:{pc.id}")
    assert (await current_state(pc.id))["online"] is False
    await ws.send_json_to(example("status.json"))
    await sync(ws)
    assert (await current_state(pc.id))["online"] is True
    assert (await current_state(pc.id))["status"]["user"] == "Student"
    seats = [m["seat"] for m in await drain(public) if m["type"] == "live.seat"]
    assert seats and seats[-1]["online"] is True
    await ws.disconnect()
    assert (await current_state(pc.id))["online"] is False


async def test_ping_after_state_loss_brings_pc_back_online():
    pc, token = await make_seated_pc()
    ws = await open_with_hello(token)
    await sync(ws)
    public = await listen(room_public_group(pc.room_id))
    await sync_to_async(cache.delete)(f"pcstate:{pc.id}")
    await sync(ws)
    assert (await current_state(pc.id))["online"] is True
    seats = [m["seat"] for m in await drain(public) if m["type"] == "live.seat"]
    assert seats and seats[-1]["online"] is True
    await ws.disconnect()


async def test_status_from_replaced_connection_closes_superseded():
    # 교체 알림(pc.superseded)을 놓친 연결은 다음 status에서 4409로 닫히고 상태는 건드리지 않는다
    pc, token = await make_pc()
    ws = await open_with_hello(token)
    await sync(ws)
    await sync_to_async(state.mark_connected)(pc.id, "someone-else")
    await ws.send_json_to(example("status.json"))
    closed = await ws.receive_output(timeout=1)
    assert closed["type"] == "websocket.close" and closed["code"] == protocol.CLOSE_SUPERSEDED
    assert await connection_of(pc.id) == "someone-else"
    assert (await current_state(pc.id))["status"] == {}
    await ws.disconnect()
    assert (await current_state(pc.id))["online"] is True


async def test_ping_from_replaced_connection_closes_superseded():
    pc, token = await make_pc()
    ws = await open_with_hello(token)
    await sync(ws)
    await sync_to_async(state.mark_connected)(pc.id, "someone-else")
    await ws.send_json_to(example("ping.json"))
    closed = await ws.receive_output(timeout=1)
    assert closed["type"] == "websocket.close" and closed["code"] == protocol.CLOSE_SUPERSEDED
    await ws.disconnect()
    assert await connection_of(pc.id) == "someone-else"
    assert (await current_state(pc.id))["online"] is True


async def test_connect_publish_failure_keeps_connection_and_cleans_up(monkeypatch):
    # mark_connected 뒤에 알림이 실패해도 연결은 살아 있어야 disconnect()가 돌아 offline이 된다
    real = consumers.publish_pc
    calls = []

    async def fail_first(pc_id, **kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            raise RuntimeError("channel layer down")
        await real(pc_id, **kwargs)

    monkeypatch.setattr(consumers, "publish_pc", fail_first)
    pc, token = await make_pc()
    ws = await open_with_hello(token)
    await sync(ws)
    assert (await current_state(pc.id))["online"] is True
    await ws.disconnect()
    assert (await current_state(pc.id))["online"] is False
    assert len(calls) == 2


async def test_disconnect_after_state_loss_publishes_offline():
    pc, token = await make_seated_pc()
    ws = await open_with_hello(token)
    await sync(ws)
    public = await listen(room_public_group(pc.room_id))
    await sync_to_async(cache.delete)(f"pcstate:{pc.id}")
    await ws.disconnect()
    seats = [m["seat"] for m in await drain(public) if m["type"] == "live.seat"]
    assert seats and seats[-1]["online"] is False


async def test_rapid_pings_refresh_state_once(monkeypatch):
    monkeypatch.setattr(protocol, "PING_REFRESH_INTERVAL", 60.0)
    touches = []
    real_touch = state.touch

    def counting_touch(*args):
        touches.append(args)
        return real_touch(*args)

    monkeypatch.setattr(state, "touch", counting_touch)
    layer = get_channel_layer()
    joins = []
    real_group_add = type(layer).group_add

    async def counting_group_add(self, group, channel):
        joins.append(group)
        await real_group_add(self, group, channel)

    monkeypatch.setattr(type(layer), "group_add", counting_group_add)
    pc, token = await make_pc()
    ws = await open_with_hello(token)
    for _ in range(5):
        await sync(ws)
    assert len(touches) == 1
    assert joins.count(pc_group(pc.id)) == 2  # 연결할 때 한 번, 첫 ping에서 한 번
    await ws.disconnect()


async def test_connect_publish_cannot_be_overtaken_by_next_connection(monkeypatch):
    # 새 연결의 online 알림은 잠금 안에서 accept 전에 보낸다. 잠금 밖에서 보내면 그 사이에
    # 다음 연결이 들어왔다 나가며 보낸 offline 뒤에 늦은 online이 도착해 공개 좌석이 online으로 남는다
    layer = get_channel_layer()
    original = type(layer).group_send
    delaying = asyncio.Event()

    async def slow_first_online_seat(self, group, message):
        if message.get("type") == "live.seat" and message["seat"]["online"] and not delaying.is_set():
            delaying.set()
            await asyncio.sleep(0.2)
        await original(self, group, message)

    pc, token = await make_seated_pc()
    public = await listen(room_public_group(pc.room_id))
    monkeypatch.setattr(type(layer), "group_send", slow_first_online_seat)
    first = connect(token)
    first_connecting = asyncio.create_task(first.connect())
    await delaying.wait()
    second = await open_with_hello(token)
    await sync(second)
    await second.disconnect()
    assert (await first_connecting)[0] is True
    closed = await first.receive_output(timeout=1)
    assert closed["code"] == protocol.CLOSE_SUPERSEDED
    await first.disconnect()
    assert (await current_state(pc.id))["online"] is False
    seats = [m["seat"] for m in await drain(public) if m["type"] == "live.seat"]
    assert seats[-1]["online"] is False


async def test_old_offline_publish_cannot_overtake_new_online(monkeypatch):
    # 끊긴 연결이 offline 상태를 읽고 보내기 전에 새 연결이 online을 알리면 공개 좌석이 offline으로 남는다.
    # 상태를 읽은 뒤 보내기까지의 틈을 넓히려고 offline 좌석 알림만 늦춘다
    layer = get_channel_layer()
    original = type(layer).group_send

    async def slow_offline_seat(self, group, message):
        if message.get("type") == "live.seat" and not message["seat"]["online"]:
            await asyncio.sleep(0.2)
        await original(self, group, message)

    monkeypatch.setattr(type(layer), "group_send", slow_offline_seat)
    pc, token = await make_seated_pc()
    old = await open_with_hello(token)
    await sync(old)
    public = await listen(room_public_group(pc.room_id))
    leaving = asyncio.create_task(old.disconnect())
    while (await current_state(pc.id))["online"]:
        await asyncio.sleep(0.005)
    new = await open_with_hello(token)
    await sync(new)
    await leaving
    assert (await current_state(pc.id))["online"] is True
    seats = [m["seat"] for m in await drain(public) if m["type"] == "live.seat"]
    assert seats[-1]["online"] is True
    await new.disconnect()
