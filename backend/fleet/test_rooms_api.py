"""실습실(Room) CRUD + 좌석 레이아웃 API 검증."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from fleet.models import Client, Room, Seat

User = get_user_model()
PW = "contract-pw-123!"


@pytest.fixture
def auth_api(db):
    User.objects.create_user("admin", password=PW)
    api = APIClient()
    assert api.login(username="admin", password=PW)
    return api


# ---------------------------------------------------------------------------
# Room CRUD
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_rooms_list_requires_auth():
    assert APIClient().get("/api/rooms/").status_code in (401, 403)


@pytest.mark.django_db
def test_rooms_list_empty(auth_api):
    resp = auth_api.get("/api/rooms/")
    assert resp.status_code == 200
    assert resp.data == []


@pytest.mark.django_db
def test_rooms_create(auth_api):
    payload = {"name": "1실습실", "rows": 6, "cols": 8, "description": "1층", "is_active": True}
    resp = auth_api.post("/api/rooms/", payload, format="json")
    assert resp.status_code == 201
    assert resp.data["name"] == "1실습실"
    assert Room.objects.filter(name="1실습실").exists()


@pytest.mark.django_db
def test_rooms_retrieve(auth_api):
    room = Room.objects.create(name="2실습실", rows=5, cols=10)
    resp = auth_api.get(f"/api/rooms/{room.pk}/")
    assert resp.status_code == 200
    assert resp.data["name"] == "2실습실"
    assert resp.data["cols"] == 10


@pytest.mark.django_db
def test_rooms_update(auth_api):
    room = Room.objects.create(name="3실습실", rows=4, cols=6)
    resp = auth_api.patch(f"/api/rooms/{room.pk}/", {"rows": 8}, format="json")
    assert resp.status_code == 200
    room.refresh_from_db()
    assert room.rows == 8


@pytest.mark.django_db
def test_rooms_delete(auth_api):
    room = Room.objects.create(name="4실습실")
    resp = auth_api.delete(f"/api/rooms/{room.pk}/")
    assert resp.status_code == 204
    assert not Room.objects.filter(pk=room.pk).exists()


# ---------------------------------------------------------------------------
# Seat Layout
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_layout_get_empty(auth_api):
    room = Room.objects.create(name="A실", rows=3, cols=4)
    resp = auth_api.get("/api/rooms/A실/layout/")
    assert resp.status_code == 200
    assert resp.data["room"] == "A실"
    assert resp.data["rows"] == 3
    assert resp.data["cols"] == 4
    assert resp.data["seats"] == []


@pytest.mark.django_db
def test_layout_post_assigns_client(auth_api):
    room = Room.objects.create(name="B실", rows=3, cols=4)
    client = Client.objects.create(hostname="PC-1")
    payload = {"assignments": [{"row": 0, "col": 0, "client_id": str(client.id)}]}
    resp = auth_api.post("/api/rooms/B실/layout/", payload, format="json")
    assert resp.status_code == 200
    seats = resp.data["seats"]
    assert len(seats) == 1
    assert seats[0]["client"]["hostname"] == "PC-1"
    assert Seat.objects.filter(room=room, row=0, col=0, client=client).exists()


@pytest.mark.django_db
def test_layout_post_clears_client(auth_api):
    room = Room.objects.create(name="C실")
    client = Client.objects.create(hostname="PC-2")
    Seat.objects.create(room=room, row=1, col=1, client=client)
    payload = {"assignments": [{"row": 1, "col": 1, "client_id": None}]}
    resp = auth_api.post("/api/rooms/C실/layout/", payload, format="json")
    assert resp.status_code == 200
    seat = Seat.objects.get(room=room, row=1, col=1)
    assert seat.client is None


@pytest.mark.django_db
def test_layout_post_invalid_client_id_returns_400(auth_api):
    Room.objects.create(name="D실")
    import uuid
    payload = {"assignments": [{"row": 0, "col": 0, "client_id": str(uuid.uuid4())}]}
    resp = auth_api.post("/api/rooms/D실/layout/", payload, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_layout_unknown_room_returns_404(auth_api):
    resp = auth_api.get("/api/rooms/없는실/layout/")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# ClientVersion CRUD
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_versions_requires_auth():
    assert APIClient().get("/api/versions/").status_code in (401, 403)


@pytest.mark.django_db
def test_versions_list(auth_api):
    resp = auth_api.get("/api/versions/")
    assert resp.status_code == 200
    assert isinstance(resp.data, list)


@pytest.mark.django_db
def test_versions_create(auth_api):
    payload = {"version": "1.2.3", "download_url": "https://example.com/v1.2.3", "changelog": "fix"}
    resp = auth_api.post("/api/versions/", payload, format="json")
    assert resp.status_code == 201
    assert resp.data["version"] == "1.2.3"
    assert resp.data["id"] is not None


@pytest.mark.django_db
def test_versions_delete(auth_api):
    from fleet.models import ClientVersion
    ver = ClientVersion.objects.create(version="0.9.0")
    resp = auth_api.delete(f"/api/versions/{ver.pk}/")
    assert resp.status_code == 204
    assert not ClientVersion.objects.filter(pk=ver.pk).exists()
