import pytest
from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.backends.cache import SessionStore

from agent import consumers, protocol, state
from labs.models import PC, Room
from live import consumers as consumers_live
from live.consumers import LiveConsumer
from live.publish import publish_pc, room_changed
from wcms.asgi import application
from wcms.groups import room_group, room_public_group, user_group

pytestmark = pytest.mark.django_db(transaction=True)
ADMIN_ONLY = {"hostname", "user", "session", "foreground", "cpu", "version", "id"}


@pytest.fixture(autouse=True)
def no_status_throttle(monkeypatch):
    monkeypatch.setattr(protocol, "STATUS_MIN_INTERVAL", 0.0)


@pytest.fixture(autouse=True)
def fresh_locks():
    consumers._locks.clear()


@database_sync_to_async
def make_room_and_pc() -> tuple[Room, PC, str]:
    room = Room.objects.create(name="301", rows=2, cols=4)
    pc, token = PC.register(hostname="LAB-HOST-1", machine_guid="g1", specs={}, version="2026.1")
    pc.room, pc.row, pc.col = room, 0, 0
    pc.save()
    return room, pc, token


@database_sync_to_async
def make_staff(is_staff: bool = True):
    return get_user_model().objects.create_user("staff", password="pw-very-long-123", is_staff=is_staff)


@sync_to_async
def new_session() -> SessionStore:
    session = SessionStore()
    session.create()
    return session


async def live_as(user, session: SessionStore | None = None) -> WebsocketCommunicator:
    ws = WebsocketCommunicator(LiveConsumer.as_asgi(), "/ws/live")
    ws.scope["user"] = user
    # AuthMiddlewareStack처럼 쿠키의 세션을 scope에 넣는다
    ws.scope["session"] = session or await new_session()
    connected, _ = await ws.connect()
    assert connected
    return ws


async def agent(token: str) -> WebsocketCommunicator:
    ws = WebsocketCommunicator(application, "/client/ws", headers=[(b"authorization", f"Bearer {token}".encode())])
    assert (await ws.connect())[0]
    await ws.send_json_to({"type": "hello", "proto": 1, "version": "2026.1"})
    return ws


async def test_anonymous_public_room_flow():
    room, pc, token = await make_room_and_pc()
    ws = await live_as(AnonymousUser())
    await ws.send_json_to({"type": "subscribe", "topic": f"room:{room.id}:public"})
    snapshot = await ws.receive_json_from()
    assert snapshot == {
        "type": "snapshot",
        "topic": f"room:{room.id}:public",
        "seats": [{"row": 0, "col": 0, "label": "301-01", "online": False}],
    }
    client = await agent(token)
    seat = await ws.receive_json_from(timeout=2)
    assert seat["type"] == "seat" and seat["seat"]["online"] is True
    await client.send_json_to({"type": "status", "user": "Student", "session": "active"})
    await client.send_json_to({"type": "ping"})
    await client.receive_json_from()
    assert await ws.receive_nothing(timeout=0.3)
    await client.disconnect()
    offline = await ws.receive_json_from(timeout=2)
    assert offline["seat"]["online"] is False and not ADMIN_ONLY & offline["seat"].keys()
    await ws.disconnect()


async def test_anonymous_cannot_subscribe_admin_topics():
    room, pc, _ = await make_room_and_pc()
    ws = await live_as(AnonymousUser())
    for topic in (f"room:{room.id}", f"pc:{pc.id}"):
        await ws.send_json_to({"type": "subscribe", "topic": topic})
        assert (await ws.receive_json_from())["error"] == "forbidden_topic"
    await ws.disconnect()


async def test_admin_room_flow():
    room, pc, token = await make_room_and_pc()
    ws = await live_as(await make_staff())
    await ws.send_json_to({"type": "subscribe", "topic": f"room:{room.id}"})
    snapshot = await ws.receive_json_from()
    assert snapshot["pcs"][0]["hostname"] == "LAB-HOST-1" and snapshot["pcs"][0]["online"] is False
    client = await agent(token)
    assert (await ws.receive_json_from(timeout=2))["pc"]["online"] is True
    await client.send_json_to({"type": "status", "user": "Student", "session": "active"})
    update = await ws.receive_json_from(timeout=2)
    assert update == {"type": "pc", "topic": f"room:{room.id}", "pc": update["pc"]}
    assert update["pc"]["user"] == "Student"
    await client.disconnect()
    assert (await ws.receive_json_from(timeout=2))["pc"]["online"] is False
    await ws.disconnect()


async def test_admin_pc_topic():
    _, pc, _ = await make_room_and_pc()
    ws = await live_as(await make_staff())
    await ws.send_json_to({"type": "subscribe", "topic": f"pc:{pc.id}"})
    snapshot = await ws.receive_json_from()
    assert snapshot["type"] == "snapshot" and snapshot["pc"]["id"] == pc.id
    await ws.disconnect()


async def test_bad_requests():
    ws = await live_as(await make_staff())
    await ws.send_to(text_data="{nope")
    assert (await ws.receive_json_from())["error"] == "bad_json"
    await ws.send_json_to({"type": "dance"})
    assert (await ws.receive_json_from())["error"] == "unknown_type"
    for topic in ("room:abc", "pc:1:public", 5):
        await ws.send_json_to({"type": "subscribe", "topic": topic})
        assert (await ws.receive_json_from())["error"] == "bad_topic"
    await ws.send_json_to({"type": "subscribe", "topic": "room:999"})
    assert (await ws.receive_json_from())["error"] == "not_found"
    await ws.disconnect()


async def test_demoted_user_loses_admin_topics():
    room, _, _ = await make_room_and_pc()
    user = await make_staff()
    ws = await live_as(user)
    await database_sync_to_async(get_user_model().objects.filter(pk=user.pk).update)(is_staff=False)
    await ws.send_json_to({"type": "subscribe", "topic": f"room:{room.id}"})
    assert (await ws.receive_json_from())["error"] == "forbidden_topic"
    await ws.disconnect()


async def test_session_end_closes():
    user = await make_staff()
    ws = await live_as(user)
    await get_channel_layer().group_send(user_group(user.pk), {"type": "session.end"})
    closed = await ws.receive_output(timeout=1)
    assert closed["type"] == "websocket.close" and closed["code"] == 4401


async def test_room_changed_forwarded_and_unsubscribe():
    room, _, _ = await make_room_and_pc()
    ws = await live_as(AnonymousUser())
    topic = f"room:{room.id}:public"
    await ws.send_json_to({"type": "subscribe", "topic": topic})
    await ws.receive_json_from()
    await sync_to_async(room_changed)(room.id)
    assert await ws.receive_json_from() == {"type": "room_changed", "topic": topic}
    await ws.send_json_to({"type": "unsubscribe", "topic": topic})
    await sync_to_async(room_changed)(room.id)
    assert await ws.receive_nothing(timeout=0.3)
    await ws.disconnect()


async def test_foreign_origin_rejected():
    ws = WebsocketCommunicator(
        application, "/ws/live", headers=[(b"origin", b"http://evil.example"), (b"host", b"localhost")]
    )
    assert (await ws.connect())[0] is False


async def test_same_origin_accepted():
    ws = WebsocketCommunicator(
        application, "/ws/live", headers=[(b"origin", b"http://localhost"), (b"host", b"localhost")]
    )
    assert (await ws.connect())[0] is True
    await ws.disconnect()


async def test_handler_error_closes_connection_and_cleans_groups(monkeypatch):
    room, _, _ = await make_room_and_pc()
    ws = await live_as(AnonymousUser())
    topic = f"room:{room.id}:public"
    await ws.send_json_to({"type": "subscribe", "topic": topic})
    await ws.receive_json_from()

    async def boom(*args):
        raise RuntimeError("db down")

    monkeypatch.setattr("live.consumers._snapshot", boom)
    await ws.send_json_to({"type": "subscribe", "topic": f"room:{room.id}:public"})
    closed = await ws.receive_output(timeout=1)
    assert closed["type"] == "websocket.close" and closed["code"] == 1011
    await ws.send_input({"type": "websocket.disconnect", "code": 1011})
    await ws.wait()
    assert not get_channel_layer().groups.get(room_public_group(room.id))


async def test_change_during_snapshot_is_not_lost(monkeypatch):
    room, pc, _ = await make_room_and_pc()
    real_snapshot = consumers_live._snapshot

    async def snapshot_then_change(*args):
        result = await real_snapshot(*args)
        await sync_to_async(state.mark_connected)(pc.id, "chan")
        await publish_pc(pc.id, online_changed=True)
        return result

    monkeypatch.setattr("live.consumers._snapshot", snapshot_then_change)
    ws = await live_as(AnonymousUser())
    topic = f"room:{room.id}:public"
    await ws.send_json_to({"type": "subscribe", "topic": topic})
    snapshot = await ws.receive_json_from()
    assert snapshot["type"] == "snapshot" and snapshot["seats"][0]["online"] is False
    seat = await ws.receive_json_from(timeout=2)
    assert seat["type"] == "seat" and seat["topic"] == topic and seat["seat"]["online"] is True
    await ws.disconnect()


async def test_not_found_leaves_no_subscription():
    ws = await live_as(await make_staff())
    await ws.send_json_to({"type": "subscribe", "topic": "room:999"})
    assert (await ws.receive_json_from())["error"] == "not_found"
    await sync_to_async(room_changed)(999)
    assert await ws.receive_nothing(timeout=0.3)
    assert not get_channel_layer().groups.get(room_group(999))
    await ws.disconnect()


def _member(group: str) -> str:
    (channel,) = get_channel_layer().groups[group]
    return channel


async def test_ping_replies_pong_and_restores_expired_groups():
    room, _, _ = await make_room_and_pc()
    user = await make_staff()
    ws = await live_as(user)
    topic = f"room:{room.id}"
    await ws.send_json_to({"type": "subscribe", "topic": topic})
    await ws.receive_json_from()
    layer = get_channel_layer()
    # 그룹 만료(24시간)나 Redis 재시작으로 구독이 사라진 상황
    channel = _member(room_group(room.id))
    await layer.group_discard(room_group(room.id), channel)
    await layer.group_discard(user_group(user.pk), channel)
    await sync_to_async(room_changed)(room.id)
    assert await ws.receive_nothing(timeout=0.3)

    await ws.send_json_to({"type": "ping"})
    assert await ws.receive_json_from() == {"type": "pong"}
    await sync_to_async(room_changed)(room.id)
    assert await ws.receive_json_from(timeout=1) == {"type": "room_changed", "topic": topic}
    await layer.group_send(user_group(user.pk), {"type": "session.end"})
    closed = await ws.receive_output(timeout=1)
    assert closed["type"] == "websocket.close" and closed["code"] == 4401


async def test_anonymous_ping_restores_public_group_only():
    room, _, _ = await make_room_and_pc()
    ws = await live_as(AnonymousUser())
    await ws.send_json_to({"type": "ping"})
    assert await ws.receive_json_from() == {"type": "pong"}
    topic = f"room:{room.id}:public"
    await ws.send_json_to({"type": "subscribe", "topic": topic})
    await ws.receive_json_from()
    layer = get_channel_layer()
    await layer.group_discard(room_public_group(room.id), _member(room_public_group(room.id)))
    await ws.send_json_to({"type": "ping"})
    assert await ws.receive_json_from() == {"type": "pong"}
    await sync_to_async(room_changed)(room.id)
    assert await ws.receive_json_from(timeout=1) == {"type": "room_changed", "topic": topic}
    assert not layer.groups.get(room_group(room.id))
    await ws.disconnect()


async def test_non_canonical_topics_rejected():
    room, _, _ = await make_room_and_pc()
    ws = await live_as(await make_staff())
    for topic in (
        f"room:0{room.id}",
        f"room:{room.id}\n",
        f"room:{room.id}:public\n",
        "room:١",  # 아랍-인도 숫자 1
        "room:１",  # 전각 숫자 1
        "room:00",
        "pc:01",
        " room:1",
    ):
        await ws.send_json_to({"type": "subscribe", "topic": topic})
        assert (await ws.receive_json_from())["error"] == "bad_topic", topic
    await ws.disconnect()


async def test_room_zero_is_canonical():
    ws = await live_as(await make_staff())
    await ws.send_json_to({"type": "subscribe", "topic": "room:0"})
    assert (await ws.receive_json_from())["error"] == "not_found"
    await ws.disconnect()


async def test_public_silent_on_status_only_change():
    room, pc, _ = await make_room_and_pc()
    ws = await live_as(AnonymousUser())
    await ws.send_json_to({"type": "subscribe", "topic": f"room:{room.id}:public"})
    await ws.receive_json_from()
    await sync_to_async(state.mark_connected)(pc.id, "chan")
    await publish_pc(pc.id, online_changed=False)
    assert await ws.receive_nothing(timeout=0.3)
    await ws.disconnect()


@database_sync_to_async
def unseat(pc: PC) -> None:
    pc.row = pc.col = None
    pc.save()


async def test_public_silent_for_unseated_pc():
    room, pc, token = await make_room_and_pc()
    await unseat(pc)
    ws = await live_as(AnonymousUser())
    await ws.send_json_to({"type": "subscribe", "topic": f"room:{room.id}:public"})
    assert (await ws.receive_json_from())["seats"] == []
    client = await agent(token)
    await client.send_json_to({"type": "ping"})
    await client.receive_json_from()
    assert await ws.receive_nothing(timeout=0.3)
    await client.disconnect()
    assert await ws.receive_nothing(timeout=0.3)
    await ws.disconnect()


async def test_missing_origin_rejected():
    ws = WebsocketCommunicator(application, "/ws/live", headers=[(b"host", b"localhost")])
    assert (await ws.connect())[0] is False


async def test_documented_message_edges():
    room, _, _ = await make_room_and_pc()
    ws = await live_as(AnonymousUser())
    await ws.send_to(bytes_data=b"\x00")
    assert await ws.receive_json_from() == {"type": "error", "error": "bad_json"}
    for raw in ("[1]", '"subscribe"', "null"):
        await ws.send_to(text_data=raw)
        assert await ws.receive_json_from() == {"type": "error", "error": "bad_json"}
    await ws.send_json_to({"type": "subscribe", "topic": f"room:{room.id}"})
    assert await ws.receive_json_from() == {"type": "error", "error": "forbidden_topic", "topic": f"room:{room.id}"}
    await ws.send_json_to({"type": "subscribe", "topic": "room:99:public"})
    assert await ws.receive_json_from() == {"type": "error", "error": "not_found", "topic": "room:99:public"}
    await ws.send_json_to({"type": "subscribe", "topic": "room:x"})
    assert await ws.receive_json_from() == {"type": "error", "error": "bad_topic"}
    await ws.send_json_to({"type": "unsubscribe", "topic": "room:12345"})
    assert await ws.receive_nothing(timeout=0.2)

    topic = f"room:{room.id}:public"
    for _ in range(2):
        await ws.send_json_to({"type": "subscribe", "topic": topic})
        assert (await ws.receive_json_from())["type"] == "snapshot"
    await sync_to_async(room_changed)(room.id)
    assert await ws.receive_json_from() == {"type": "room_changed", "topic": topic}
    assert await ws.receive_nothing(timeout=0.3)
    await ws.disconnect()


async def test_unseated_pc_reaches_pc_topic_only():
    room, pc, _ = await make_room_and_pc()
    await unseat(pc)
    ws = await live_as(await make_staff())
    await ws.send_json_to({"type": "subscribe", "topic": f"room:{room.id}"})
    assert (await ws.receive_json_from())["pcs"] == []
    await ws.send_json_to({"type": "subscribe", "topic": f"pc:{pc.id}"})
    assert (await ws.receive_json_from())["pc"]["online"] is False
    await sync_to_async(state.mark_connected)(pc.id, "chan")
    await publish_pc(pc.id, online_changed=True)
    update = await ws.receive_json_from(timeout=1)
    assert update["topic"] == f"pc:{pc.id}" and update["pc"]["online"] is True
    assert await ws.receive_nothing(timeout=0.3)
    await ws.disconnect()


async def test_admin_ping_with_live_session_gets_pong():
    ws = await live_as(await make_staff())
    await ws.send_json_to({"type": "ping"})
    assert await ws.receive_json_from() == {"type": "pong"}
    await ws.disconnect()


async def test_admin_ping_after_session_flushed_closes_4401():
    # 로그아웃 알림(session.end)을 놓친 연결도 다음 ping에서 끊긴다
    session = await new_session()
    ws = await live_as(await make_staff(), session)
    await sync_to_async(session.flush)()
    await ws.send_json_to({"type": "ping"})
    closed = await ws.receive_output(timeout=1)
    assert closed["type"] == "websocket.close" and closed["code"] == 4401


async def test_admin_ping_without_session_closes_4401():
    ws = WebsocketCommunicator(LiveConsumer.as_asgi(), "/ws/live")
    ws.scope["user"] = await make_staff()
    assert (await ws.connect())[0]
    await ws.send_json_to({"type": "ping"})
    closed = await ws.receive_output(timeout=1)
    assert closed["type"] == "websocket.close" and closed["code"] == 4401


async def test_admin_ping_after_demotion_closes_4401():
    user = await make_staff()
    ws = await live_as(user)
    await database_sync_to_async(get_user_model().objects.filter(pk=user.pk).update)(is_staff=False)
    await ws.send_json_to({"type": "ping"})
    closed = await ws.receive_output(timeout=1)
    assert closed["type"] == "websocket.close" and closed["code"] == 4401


async def test_admin_ping_after_deactivation_closes_4401():
    user = await make_staff()
    ws = await live_as(user)
    await database_sync_to_async(get_user_model().objects.filter(pk=user.pk).update)(is_active=False)
    await ws.send_json_to({"type": "ping"})
    closed = await ws.receive_output(timeout=1)
    assert closed["type"] == "websocket.close" and closed["code"] == 4401


async def test_anonymous_ping_ignores_session():
    session = await new_session()
    ws = await live_as(AnonymousUser(), session)
    await sync_to_async(session.flush)()
    await ws.send_json_to({"type": "ping"})
    assert await ws.receive_json_from() == {"type": "pong"}
    await ws.disconnect()
