import pytest
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from audit.models import AuditLog
from labs.models import PC, RegistrationPin, Room
from wcms.groups import pc_group

pytestmark = pytest.mark.django_db


def make_pc(n: int) -> PC:
    pc, _ = PC.register(hostname=f"LAB-{n:02d}", machine_guid=f"g{n}", specs={}, version="2026.1")
    return pc


def seat(pc: PC, room: Room, row: int, col: int) -> None:
    pc.room, pc.row, pc.col = room, row, col
    pc.save()


def test_requires_admin(api):
    for url in ["/api/rooms", "/api/pcs", "/api/pins"]:
        assert api.get(url).status_code == 401


def test_room_crud(admin_api):
    created = admin_api.post("/api/rooms", {"name": "301", "rows": 5, "cols": 8, "aisle_after": 4}, format="json")
    assert created.status_code == 201
    room_id = created.json()["id"]
    assert admin_api.get("/api/rooms").json()[0]["name"] == "301"
    patched = admin_api.patch(f"/api/rooms/{room_id}", {"name": "302"}, format="json")
    assert patched.json()["name"] == "302"
    assert admin_api.delete(f"/api/rooms/{room_id}").status_code == 204
    assert AuditLog.objects.filter(action__startswith="room.").count() == 3


@pytest.mark.parametrize(
    "body", [{"rows": 0}, {"cols": 21}, {"aisle_after": 8}, {"aisle_after": 0}]
)
def test_room_validation(admin_api, body):
    response = admin_api.post("/api/rooms", {"name": "301", "rows": 5, "cols": 8, **body}, format="json")
    assert response.status_code == 400
    assert response.json()["error"] == "invalid"


def test_shrinking_room_unseats_out_of_range(admin_api):
    room = Room.objects.create(name="301", rows=2, cols=4)
    inside, outside = make_pc(1), make_pc(2)
    seat(inside, room, 0, 0)
    seat(outside, room, 0, 3)
    admin_api.patch(f"/api/rooms/{room.id}", {"cols": 3}, format="json")
    outside.refresh_from_db()
    inside.refresh_from_db()
    assert outside.room is None and outside.row is None
    assert inside.room == room


def test_delete_room_unseats(admin_api):
    room = Room.objects.create(name="301", rows=2, cols=4)
    pc = make_pc(1)
    seat(pc, room, 1, 1)
    admin_api.delete(f"/api/rooms/{room.id}")
    pc.refresh_from_db()
    assert (pc.room, pc.row, pc.col) == (None, None, None)


def test_replace_seats(admin_api):
    room = Room.objects.create(name="301", rows=2, cols=4)
    a, b, c = make_pc(1), make_pc(2), make_pc(3)
    seat(c, room, 1, 3)
    response = admin_api.put(
        f"/api/rooms/{room.id}/seats",
        {"seats": [{"row": 0, "col": 0, "pc": a.id}, {"row": 1, "col": 3, "pc": b.id}]},
        format="json",
    )
    assert response.status_code == 200
    for pc in (a, b, c):
        pc.refresh_from_db()
    assert (a.row, a.col, b.row, b.col) == (0, 0, 1, 3)
    assert c.room is None
    assert sorted(s["pc"] for s in admin_api.get(f"/api/rooms/{room.id}/seats").json()["seats"]) == [a.id, b.id]


@pytest.mark.parametrize("problem", ["dup_pc", "dup_seat", "out_of_range", "missing_pc"])
def test_seat_validation(admin_api, problem):
    room = Room.objects.create(name="301", rows=2, cols=4)
    a, b = make_pc(1), make_pc(2)
    seats = {
        "dup_pc": [{"row": 0, "col": 0, "pc": a.id}, {"row": 0, "col": 1, "pc": a.id}],
        "dup_seat": [{"row": 0, "col": 0, "pc": a.id}, {"row": 0, "col": 0, "pc": b.id}],
        "out_of_range": [{"row": 2, "col": 0, "pc": a.id}],
        "missing_pc": [{"row": 0, "col": 0, "pc": 9999}],
    }[problem]
    response = admin_api.put(f"/api/rooms/{room.id}/seats", {"seats": seats}, format="json")
    assert response.status_code == 400
    a.refresh_from_db()
    assert a.room is None


def test_pc_list_and_delete(admin_api):
    pc = make_pc(1)
    rows = admin_api.get("/api/pcs").json()
    assert rows[0]["hostname"] == "LAB-01" and rows[0]["label"] == "LAB-01"
    layer = get_channel_layer()
    channel = async_to_sync(layer.new_channel)()
    async_to_sync(layer.group_add)(pc_group(pc.id), channel)
    assert admin_api.delete(f"/api/pcs/{pc.id}").status_code == 204
    assert async_to_sync(layer.receive)(channel) == {"type": "pc.revoked"}
    assert not PC.objects.exists()


def test_pins(admin_api):
    created = admin_api.post("/api/pins", {"multi_use": True, "minutes": 60}, format="json")
    assert created.status_code == 201
    pin = created.json()
    assert len(pin["pin"]) == 6 and pin["multi_use"] is True
    assert [p["id"] for p in admin_api.get("/api/pins").json()] == [pin["id"]]
    assert admin_api.delete(f"/api/pins/{pin['id']}").status_code == 204
    assert admin_api.get("/api/pins").json() == []
    assert RegistrationPin.objects.get(id=pin["id"]).revoked is True


def test_pin_minutes_must_be_allowed(admin_api):
    response = admin_api.post("/api/pins", {"multi_use": False, "minutes": 30}, format="json")
    assert response.status_code == 400


def test_room_changes_notify_live_viewers(admin_api, monkeypatch):
    changed = []
    monkeypatch.setattr("labs.views.room_changed", changed.append)
    room, other = Room.objects.create(name="301", rows=2, cols=4), Room.objects.create(name="302", rows=2, cols=4)
    a, b = make_pc(1), make_pc(2)
    seat(b, other, 0, 0)
    admin_api.patch(f"/api/rooms/{room.id}", {"name": "303"}, format="json")
    assert changed == [room.id]
    admin_api.put(f"/api/rooms/{room.id}/seats", {"seats": [{"row": 0, "col": 0, "pc": b.id}]}, format="json")
    assert sorted(changed[1:]) == sorted([room.id, other.id])
    del changed[:]
    admin_api.delete(f"/api/pcs/{b.id}")
    admin_api.delete(f"/api/pcs/{a.id}")
    assert changed == [room.id]
    admin_api.delete(f"/api/rooms/{room.id}")
    assert changed == [room.id, room.id]
