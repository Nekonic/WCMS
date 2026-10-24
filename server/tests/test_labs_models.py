from datetime import timedelta

import pytest
from django.utils import timezone

from labs.models import PC, RegistrationPin, Room

pytestmark = pytest.mark.django_db


def make_pc(guid: str = "guid-1", hostname: str = "LAB-01") -> tuple[PC, str]:
    return PC.register(hostname=hostname, machine_guid=guid, specs={}, version="2026.1")


def test_pin_is_six_digits():
    pin = RegistrationPin.issue(user=None, multi_use=False, minutes=10)
    assert len(pin.pin) == 6
    assert pin.pin.isdigit()


def test_single_use_pin_works_once():
    pin = RegistrationPin.issue(user=None, multi_use=False, minutes=10)
    assert RegistrationPin.consume(pin.pin) is True
    assert RegistrationPin.consume(pin.pin) is False


def test_multi_use_pin_works_many_times():
    pin = RegistrationPin.issue(user=None, multi_use=True, minutes=10)
    assert all(RegistrationPin.consume(pin.pin) for _ in range(5))


def test_expired_pin_rejected():
    pin = RegistrationPin.issue(user=None, multi_use=True, minutes=10)
    pin.expires_at = timezone.now() - timedelta(seconds=1)
    pin.save()
    assert RegistrationPin.consume(pin.pin) is False


def test_revoked_pin_rejected():
    pin = RegistrationPin.issue(user=None, multi_use=True, minutes=10)
    pin.revoked = True
    pin.save()
    assert RegistrationPin.consume(pin.pin) is False


def test_unknown_pin_rejected():
    assert RegistrationPin.consume("123456") is False


def test_register_token_resolves_and_is_stored_hashed():
    pc, token = make_pc()
    assert PC.from_token(token) == pc
    assert pc.token_hash != token
    assert pc.token_hash == PC.hash_token(token)


def test_reregister_keeps_seat_and_rotates_token():
    room = Room.objects.create(name="301", rows=5, cols=8)
    pc, old_token = make_pc()
    pc.room, pc.row, pc.col = room, 1, 4
    pc.save()

    again, new_token = make_pc(hostname="LAB-01-NEW")

    assert again.pk == pc.pk
    assert again.room == room
    assert again.hostname == "LAB-01-NEW"
    assert new_token != old_token
    assert PC.from_token(old_token) is None
    assert PC.from_token(new_token) == pc


def test_label_uses_seat_number():
    room = Room.objects.create(name="301", rows=5, cols=8)
    pc, _ = make_pc()
    assert pc.label == "LAB-01"
    pc.room, pc.row, pc.col = room, 1, 4
    pc.save()
    assert pc.label == "301-13"


def test_is_online_requires_recent_last_seen():
    pc, _ = make_pc()
    pc.online = True
    pc.last_seen = timezone.now()
    assert pc.is_online is True
    pc.last_seen = timezone.now() - timedelta(seconds=31)
    assert pc.is_online is False
    pc.online = False
    pc.last_seen = timezone.now()
    assert pc.is_online is False
