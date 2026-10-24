from datetime import timedelta

import pytest
from django.db import IntegrityError
from django.utils import timezone

from labs.models import PC, RegistrationPin, Room

pytestmark = pytest.mark.django_db


def make_pc(guid="guid-1", hostname="LAB-01") -> tuple[PC, str]:
    return PC.register(hostname=hostname, machine_guid=guid, specs={"cpu": "i5"}, version="2026.1")


def test_pin_format_and_single_use():
    pin = RegistrationPin.issue(user=None, multi_use=False, minutes=10)
    assert len(pin.pin) == 6 and pin.pin.isdigit()
    assert RegistrationPin.consume(pin.pin) is True
    assert RegistrationPin.consume(pin.pin) is False


def test_multi_use_pin():
    pin = RegistrationPin.issue(user=None, multi_use=True, minutes=10)
    assert all(RegistrationPin.consume(pin.pin) for _ in range(3))


def test_expired_revoked_unknown_pins():
    expired = RegistrationPin.issue(user=None, multi_use=True, minutes=10)
    expired.expires_at = timezone.now() - timedelta(seconds=1)
    expired.save()
    revoked = RegistrationPin.issue(user=None, multi_use=True, minutes=10)
    revoked.revoked = True
    revoked.save()
    assert RegistrationPin.consume(expired.pin) is False
    assert RegistrationPin.consume(revoked.pin) is False
    assert RegistrationPin.consume("999999") is False


def test_usable_queryset_excludes_spent_single_use():
    spent = RegistrationPin.issue(user=None, multi_use=False, minutes=10)
    RegistrationPin.consume(spent.pin)
    live = RegistrationPin.issue(user=None, multi_use=False, minutes=10)
    assert list(RegistrationPin.usable()) == [live]


def test_token_is_hashed_and_resolves():
    pc, token = make_pc()
    assert pc.token_hash == PC.hash_token(token) != token
    assert PC.from_token(token) == pc
    assert PC.from_token("wrong") is None


def test_reregister_keeps_seat_and_rotates_token():
    room = Room.objects.create(name="301", rows=5, cols=8)
    pc, old = make_pc()
    pc.room, pc.row, pc.col = room, 1, 4
    pc.save()
    again, new = make_pc(hostname="LAB-01-NEW")
    assert again.pk == pc.pk and again.room == room and again.hostname == "LAB-01-NEW"
    assert PC.from_token(old) is None and PC.from_token(new) == pc


def test_label_and_seated():
    room = Room.objects.create(name="301", rows=5, cols=8)
    pc, _ = make_pc()
    assert pc.seated is False and pc.label == "LAB-01"
    pc.room, pc.row, pc.col = room, 1, 4
    pc.save()
    assert pc.seated is True and pc.label == "301-13"


def test_seat_is_unique():
    room = Room.objects.create(name="301", rows=5, cols=8)
    a, _ = make_pc("g1", "A")
    b, _ = make_pc("g2", "B")
    a.room, a.row, a.col = room, 0, 0
    a.save()
    b.room, b.row, b.col = room, 0, 0
    with pytest.raises(IntegrityError):
        b.save()
