import pytest
from django.utils import timezone

from labs.live import pc_payload
from labs.models import PC, Room

pytestmark = pytest.mark.django_db

ADMIN_ONLY = {"hostname", "user", "session", "foreground", "cpu", "version"}


def online_pc(session: str) -> PC:
    room = Room.objects.create(name="301", rows=5, cols=8)
    pc, _ = PC.register(hostname="LAB-01", machine_guid="g1", specs={}, version="2026.1")
    pc.room, pc.row, pc.col = room, 0, 0
    pc.online = True
    pc.last_seen = timezone.now()
    pc.status = {"user": "Student", "session": session, "cpu": 10}
    pc.save()
    return pc


def test_public_payload_hides_details():
    data = pc_payload(online_pc("active"), admin=False)
    assert data["label"] == "301-01"
    assert data["state"] == "in_use"
    assert data["state_label"] == "사용 중"
    assert not ADMIN_ONLY & data.keys()


def test_public_locked_counts_as_available():
    assert pc_payload(online_pc("locked"), admin=False)["state"] == "available"


def test_admin_payload_has_details_and_session_state():
    data = pc_payload(online_pc("locked"), admin=True)
    assert data["state"] == "locked"
    assert data["user"] == "Student"
    assert ADMIN_ONLY <= data.keys()


def test_offline_state():
    pc = online_pc("active")
    pc.online = False
    assert pc_payload(pc, admin=True)["state"] == "offline"
    assert pc_payload(pc, admin=False)["state_label"] == "오프라인"


def test_unplaced_pc_public_label_hides_hostname():
    pc, _ = PC.register(hostname="LAB-99", machine_guid="g9", specs={}, version="2026.1")
    pc.online = True
    pc.last_seen = timezone.now()
    pc.status = {"session": "active"}
    pc.save()
    public = pc_payload(pc, admin=False)
    assert public["label"] == ""
    assert "LAB-99" not in [v for v in public.values() if isinstance(v, str)]
    assert pc_payload(pc, admin=True)["label"] == "LAB-99"
