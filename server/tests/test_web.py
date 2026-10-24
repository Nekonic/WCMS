import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from labs.models import PC, Room

pytestmark = pytest.mark.django_db


@pytest.fixture
def room_with_pc():
    room = Room.objects.create(name="301", rows=2, cols=4, aisle_after=2)
    pc, _ = PC.register(hostname="LAB-HOST-01", machine_guid="g1", specs={}, version="2026.1")
    pc.room, pc.row, pc.col = room, 0, 1
    pc.online = True
    pc.last_seen = timezone.now()
    pc.status = {
        "user": "StudentName",
        "session": "active",
        "foreground": {"process": "chrome.exe", "title": "<script>alert(1)</script>"},
    }
    pc.save()
    return room, pc


@pytest.fixture
def admin_client(client):
    user = get_user_model().objects.create_user("admin", password="pw-123456", is_staff=True)
    client.force_login(user)
    return client


def test_home_redirects_to_first_room(client, room_with_pc):
    room, _ = room_with_pc
    assert client.get("/").url == f"/rooms/{room.id}/"


def test_home_without_rooms(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "등록된 실습실이 없습니다" in response.content.decode()


def test_anonymous_sees_state_only(client, room_with_pc):
    room, _ = room_with_pc
    html = client.get(f"/rooms/{room.id}/").content.decode()
    assert "301-02" in html
    assert "사용 중" in html
    assert "StudentName" not in html
    assert "chrome.exe" not in html
    assert "LAB-HOST-01" not in html


def test_admin_sees_details_escaped(admin_client, room_with_pc):
    room, _ = room_with_pc
    html = admin_client.get(f"/rooms/{room.id}/").content.decode()
    assert "StudentName" in html
    assert "chrome.exe" in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<script>alert(1)</script>" not in html


def test_aisle_and_empty_seats_rendered(client, room_with_pc):
    room, _ = room_with_pc
    html = client.get(f"/rooms/{room.id}/").content.decode()
    assert html.count('class="aisle"') == 2
    assert html.count("st-empty") == 7


def test_unknown_room_404(client):
    assert client.get("/rooms/999/").status_code == 404
