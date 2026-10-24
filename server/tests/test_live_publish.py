import pytest
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from agent import state
from labs.models import PC, Room
from live.publish import publish_pc, room_changed
from live.snapshots import live_pc, public_room_snapshot, public_seat, room_snapshot
from wcms.groups import pc_watch_group, room_group, room_public_group

pytestmark = pytest.mark.django_db(transaction=True)
PUBLIC_KEYS = {"row", "col", "label", "online"}


def seated_pc(room: Room, n: int = 1) -> PC:
    pc, _ = PC.register(hostname=f"LAB-HOST-{n}", machine_guid=f"g{n}", specs={"cpu": "i5"}, version="2026.1")
    pc.room, pc.row, pc.col = room, 0, n - 1
    pc.save()
    return pc


def listen(group: str) -> str:
    layer = get_channel_layer()
    channel = async_to_sync(layer.new_channel)()
    async_to_sync(layer.group_add)(group, channel)
    return channel


def receive(channel: str) -> dict:
    return async_to_sync(get_channel_layer().receive)(channel)


def test_payload_shapes():
    room = Room.objects.create(name="301", rows=2, cols=4)
    pc = seated_pc(room)
    st = {"online": True, "status": {"user": "Student", "session": "active", "cpu": 3.0}}
    admin = live_pc(pc, st)
    assert admin["hostname"] == "LAB-HOST-1" and admin["user"] == "Student" and admin["label"] == "301-01"
    public = public_seat(pc, st)
    assert set(public) == PUBLIC_KEYS
    assert public == {"row": 0, "col": 0, "label": "301-01", "online": True}


def test_offline_hides_last_status():
    room = Room.objects.create(name="301", rows=2, cols=4)
    pc = seated_pc(room)
    admin = live_pc(pc, {"online": False, "status": {}})
    assert admin["online"] is False and admin["user"] == "" and admin["cpu"] is None


def test_snapshots_only_include_seated():
    room = Room.objects.create(name="301", rows=2, cols=4)
    seated = seated_pc(room)
    PC.register(hostname="UNSEATED", machine_guid="gx", specs={}, version="")
    assert [p["id"] for p in room_snapshot(room.id)] == [seated.id]
    seats = public_room_snapshot(room.id)
    assert len(seats) == 1 and set(seats[0]) == PUBLIC_KEYS
    assert room_snapshot(9999) is None


def test_publish_pc_routes_messages():
    room = Room.objects.create(name="301", rows=2, cols=4)
    pc = seated_pc(room)
    state.mark_connected(pc.id, "c")
    watch, admin_room, public_room = listen(pc_watch_group(pc.id)), listen(room_group(room.id)), listen(room_public_group(room.id))

    async_to_sync(publish_pc)(pc.id, online_changed=False)
    assert receive(watch)["topic"] == f"pc:{pc.id}"
    message = receive(admin_room)
    assert message["type"] == "live.pc" and message["pc"]["online"] is True

    async_to_sync(publish_pc)(pc.id, online_changed=True)
    receive(watch)
    receive(admin_room)
    seat = receive(public_room)
    assert seat["type"] == "live.seat" and seat["topic"] == f"room:{room.id}:public"
    assert set(seat["seat"]) == PUBLIC_KEYS


def test_room_changed_notifies_both_groups():
    admin_room, public_room = listen(room_group(5)), listen(room_public_group(5))
    room_changed(5)
    assert receive(admin_room) == {"type": "live.room_changed", "topic": "room:5"}
    assert receive(public_room) == {"type": "live.room_changed", "topic": "room:5:public"}
