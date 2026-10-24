import json

import pytest
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from agent import state
from agent.protocol import clean_status
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


def test_unencodable_status_strings_are_replaced_and_render(admin_api):
    room = Room.objects.create(name="302", rows=1, cols=1)
    pc, _ = PC.register(hostname="LAB-X", machine_guid="gx", specs={}, version="2026.1")
    pc.room, pc.row, pc.col = room, 0, 0
    pc.save()
    state.mark_connected(pc.id, "c")
    message = json.loads(
        '{"type": "status", "user": "\\ud800kim", "session": "active",'
        ' "foreground": {"process": "a\\udfff.exe", "title": "\\udc00\\ud800"}}'
    )
    state.save_status(pc.id, "c", clean_status(message))
    stored = state.get_state(pc.id)["status"]
    assert stored["user"] == "?kim"
    assert stored["foreground"] == {"process": "a?.exe", "title": "??"}
    for url in (f"/api/rooms/{room.id}/pcs", f"/api/pcs/{pc.id}/live"):
        response = admin_api.get(url)
        assert response.status_code == 200 and response["Content-Type"] == "application/json"
        response.json()


def test_json_output_survives_unencodable_strings(admin_api):
    # 저장 전에 걸러지지 않은 값이 있어도 응답은 500이 아니라 ASCII 이스케이프된 JSON이어야 한다
    PC.register(hostname="LAB-Y", machine_guid="gy", specs={"cpu": "\ud800"}, version="")
    response = admin_api.get("/api/pcs")
    assert response.status_code == 200
    assert response.json()[0]["specs"] == {"cpu": "\ud800"}
