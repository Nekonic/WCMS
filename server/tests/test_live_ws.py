import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone

from labs.live import broadcast_pc
from labs.models import PC
from wcms.asgi import application
from web.consumers import LiveConsumer

pytestmark = pytest.mark.django_db(transaction=True)

ADMIN_ONLY_KEYS = {"hostname", "user", "session", "foreground", "cpu", "version"}


@database_sync_to_async
def make_pc() -> PC:
    pc, _ = PC.register(hostname="LAB-01", machine_guid="g1", specs={}, version="2026.1")
    pc.online = True
    pc.last_seen = timezone.now()
    pc.status = {"user": "Student", "session": "active"}
    pc.save()
    return pc


@database_sync_to_async
def make_staff():
    return get_user_model().objects.create_user("admin", password="pw-123456", is_staff=True)


async def connect_as(user) -> WebsocketCommunicator:
    ws = WebsocketCommunicator(LiveConsumer.as_asgi(), "/ws/live")
    ws.scope["user"] = user
    connected, _ = await ws.connect()
    assert connected
    return ws


async def test_anonymous_receives_public_payload():
    pc = await make_pc()
    ws = await connect_as(AnonymousUser())
    await broadcast_pc(pc.id)
    message = await ws.receive_json_from()
    assert message["type"] == "pc"
    assert message["pc"]["state"] == "in_use"
    assert not ADMIN_ONLY_KEYS & message["pc"].keys()
    await ws.disconnect()


async def test_admin_receives_details():
    pc = await make_pc()
    ws = await connect_as(await make_staff())
    await broadcast_pc(pc.id)
    message = await ws.receive_json_from()
    assert message["pc"]["user"] == "Student"
    assert message["pc"]["state"] == "active"
    await ws.disconnect()


async def test_foreign_origin_rejected():
    ws = WebsocketCommunicator(
        application,
        "/ws/live",
        headers=[(b"origin", b"http://evil.example"), (b"host", b"localhost")],
    )
    connected, _ = await ws.connect()
    assert not connected


async def test_same_origin_accepted():
    ws = WebsocketCommunicator(
        application,
        "/ws/live",
        headers=[(b"origin", b"http://localhost"), (b"host", b"localhost")],
    )
    connected, _ = await ws.connect()
    assert connected
    await ws.disconnect()


async def test_client_status_reaches_browser_grids():
    _, token = await database_sync_to_async(PC.register)(
        hostname="LAB-02", machine_guid="g2", specs={}, version="2026.1"
    )
    anonymous = await connect_as(AnonymousUser())
    staff = await connect_as(await make_staff())

    client = WebsocketCommunicator(
        application, "/client/ws", headers=[(b"authorization", f"Bearer {token}".encode())]
    )
    connected, _ = await client.connect()
    assert connected
    # The connect itself broadcasts once to every browser socket.
    assert (await anonymous.receive_json_from(timeout=2))["type"] == "pc"
    assert (await staff.receive_json_from(timeout=2))["type"] == "pc"

    await client.send_json_to(
        {
            "type": "status",
            "user": "Student",
            "session": "active",
            "foreground": {"process": "chrome.exe", "title": "t"},
        }
    )
    public = await anonymous.receive_json_from(timeout=2)
    assert public["type"] == "pc"
    assert public["pc"]["state"] == "in_use"
    assert not ADMIN_ONLY_KEYS & public["pc"].keys()
    detail = await staff.receive_json_from(timeout=2)
    assert detail["pc"]["user"] == "Student"
    assert detail["pc"]["state"] == "active"

    await client.disconnect()
    assert (await anonymous.receive_json_from(timeout=2))["pc"]["state"] == "offline"
    assert (await staff.receive_json_from(timeout=2))["pc"]["state"] == "offline"
    await anonymous.disconnect()
    await staff.disconnect()
