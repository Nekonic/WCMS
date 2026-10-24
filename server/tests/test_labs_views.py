import pytest
from django.contrib.auth import get_user_model

from labs.models import PC, RegistrationPin, Room

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client(client):
    user = get_user_model().objects.create_user("admin", password="pw-123456", is_staff=True)
    client.force_login(user)
    return client


def make_pc(n: int) -> PC:
    pc, _ = PC.register(hostname=f"LAB-{n:02d}", machine_guid=f"g{n}", specs={}, version="2026.1")
    return pc


def room_fields(**override) -> dict:
    data = {"name": "301", "rows": "5", "cols": "8", "aisle_after": "4", "sort_order": "0"}
    data.update(override)
    return data


@pytest.mark.parametrize("url", ["/rooms/manage/", "/pins/"])
def test_anonymous_redirected_to_login(client, url):
    response = client.get(url)
    assert response.status_code == 302
    assert response.url.startswith("/login/")


def test_create_room(admin_client):
    response = admin_client.post("/rooms/manage/", room_fields())
    room = Room.objects.get(name="301")
    assert response.url == f"/rooms/{room.id}/edit/"
    assert (room.rows, room.cols, room.aisle_after) == (5, 8, 4)


def test_aisle_must_be_inside_room(admin_client):
    response = admin_client.post("/rooms/manage/", room_fields(aisle_after="8"))
    assert response.status_code == 200
    assert not Room.objects.exists()


def test_assign_seats(admin_client):
    room = Room.objects.create(name="301", rows=2, cols=4)
    a, b = make_pc(1), make_pc(2)
    data = room_fields(rows="2", cols="4", aisle_after="")
    data.update({"seat-0-0": str(a.id), "seat-1-3": str(b.id)})
    response = admin_client.post(f"/rooms/{room.id}/edit/", data)
    assert response.status_code == 302
    a.refresh_from_db()
    b.refresh_from_db()
    assert (a.room, a.row, a.col) == (room, 0, 0)
    assert (b.room, b.row, b.col) == (room, 1, 3)


def test_same_pc_twice_rejected(admin_client):
    room = Room.objects.create(name="301", rows=2, cols=4)
    a = make_pc(1)
    data = room_fields(rows="2", cols="4", aisle_after="")
    data.update({"seat-0-0": str(a.id), "seat-0-1": str(a.id)})
    response = admin_client.post(f"/rooms/{room.id}/edit/", data)
    assert response.status_code == 200
    assert "두 자리" in response.content.decode()
    a.refresh_from_db()
    assert a.room is None


def test_non_ascii_digit_seat_rejected(admin_client):
    room = Room.objects.create(name="301", rows=2, cols=4)
    a = make_pc(1)
    data = room_fields(rows="2", cols="4", aisle_after="")
    data.update({"seat-0-0": "\u00b2", "seat-0-1": str(a.id)})
    response = admin_client.post(f"/rooms/{room.id}/edit/", data)
    assert response.status_code == 200
    assert "잘못된 PC 선택입니다." in response.content.decode()
    a.refresh_from_db()
    assert a.room is None


def test_shrinking_room_unassigns_out_of_range_pc(admin_client):
    room = Room.objects.create(name="301", rows=2, cols=4)
    a = make_pc(1)
    a.room, a.row, a.col = room, 0, 3
    a.save()
    data = room_fields(rows="2", cols="3", aisle_after="")
    data["seat-0-3"] = str(a.id)
    admin_client.post(f"/rooms/{room.id}/edit/", data)
    a.refresh_from_db()
    assert a.room is None


def test_delete_room_unassigns_pcs(admin_client):
    room = Room.objects.create(name="301", rows=2, cols=4)
    a = make_pc(1)
    a.room, a.row, a.col = room, 0, 0
    a.save()
    response = admin_client.post(f"/rooms/{room.id}/delete/")
    assert response.url == "/rooms/manage/"
    a.refresh_from_db()
    assert (a.room, a.row, a.col) == (None, None, None)
    assert not Room.objects.exists()


def test_issue_pin(admin_client):
    response = admin_client.post("/pins/", {"minutes": "60", "multi_use": "on"})
    pin = RegistrationPin.objects.get()
    assert pin.multi_use is True
    assert pin.pin in response.content.decode()


def test_revoke_pin(admin_client):
    pin = RegistrationPin.issue(user=None, multi_use=True, minutes=10)
    admin_client.post(f"/pins/{pin.id}/revoke/")
    pin.refresh_from_db()
    assert pin.revoked is True
    assert pin.pin not in admin_client.get("/pins/").content.decode()
