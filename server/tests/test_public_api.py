import pytest
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from agent import state
from labs.models import PC, Room
from wcms.groups import room_group

pytestmark = pytest.mark.django_db


@pytest.fixture
def room_with_pc():
    room = Room.objects.create(name="301", rows=2, cols=4, aisle_after=2)
    pc, _ = PC.register(hostname="LAB-HOST-SECRET", machine_guid="g1", specs={"cpu": "i5"}, version="2026.1")
    pc.room, pc.row, pc.col = room, 0, 1
    pc.save()
    state.mark_connected(pc.id, "c")
    state.save_status(pc.id, "c", {"user": "StudentName", "session": "active"})
    return room, pc


def test_public_rooms(api, room_with_pc):
    room, _ = room_with_pc
    assert api.get("/api/public/rooms").json() == [
        {"id": room.id, "name": "301", "rows": 2, "cols": 4, "aisle_after": 2}
    ]


def test_public_room_detail_hides_everything_else(api, room_with_pc):
    room, _ = room_with_pc
    response = api.get(f"/api/public/rooms/{room.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["seats"] == [{"row": 0, "col": 1, "label": "301-02", "online": True}]
    text = response.content.decode()
    assert "LAB-HOST-SECRET" not in text and "StudentName" not in text and "i5" not in text


def test_public_unknown_room(api):
    assert api.get("/api/public/rooms/999").status_code == 404


def test_admin_room_pcs(admin_api, api, room_with_pc):
    room, pc = room_with_pc
    assert api.get(f"/api/rooms/{room.id}/pcs").status_code == 401
    rows = admin_api.get(f"/api/rooms/{room.id}/pcs").json()
    assert rows[0]["user"] == "StudentName" and rows[0]["hostname"] == "LAB-HOST-SECRET"
    assert admin_api.get(f"/api/pcs/{pc.id}/live").json()["id"] == pc.id


def test_seat_change_publishes_room_changed(admin_api, room_with_pc):
    room, pc = room_with_pc
    layer = get_channel_layer()
    channel = async_to_sync(layer.new_channel)()
    async_to_sync(layer.group_add)(room_group(room.id), channel)
    admin_api.put(f"/api/rooms/{room.id}/seats", {"seats": []}, format="json")
    assert async_to_sync(layer.receive)(channel) == {"type": "live.room_changed", "topic": f"room:{room.id}"}
