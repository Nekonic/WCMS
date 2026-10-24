import time
from datetime import timedelta
from io import StringIO

import pyotp
import pytest
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.utils import timezone

from accounts.models import EnrollmentToken, TOTPDevice
from accounts.totp import matching_step

pytestmark = pytest.mark.django_db
User = get_user_model()


def test_matching_step_accepts_current_code():
    secret = pyotp.random_base32()
    assert matching_step(secret, pyotp.TOTP(secret).now()) is not None


@pytest.mark.parametrize("code", ["", "12345", "1234567", "abcdef", "²²²²²²", "１２３４５６"])
def test_matching_step_rejects_malformed(code):
    assert matching_step(pyotp.random_base32(), code) is None


def test_device_code_cannot_be_reused(admin_user):
    device = TOTPDevice.objects.create(user=admin_user, secret=pyotp.random_base32())
    code = pyotp.TOTP(device.secret).now()
    assert device.verify(code) is True
    assert device.verify(code) is False


def test_issue_invalidates_previous_token(admin_user):
    _, first = EnrollmentToken.issue(user=admin_user, purpose="reset", created_by=None)
    _, second = EnrollmentToken.issue(user=admin_user, purpose="reset", created_by=None)
    assert EnrollmentToken.find_usable(first) is None
    assert EnrollmentToken.find_usable(second) is not None


def test_expired_and_used_tokens_unusable(admin_user):
    entry, token = EnrollmentToken.issue(user=admin_user, purpose="reset", created_by=None)
    entry.expires_at = timezone.now() - timedelta(seconds=1)
    entry.save()
    assert EnrollmentToken.find_usable(token) is None
    entry, token = EnrollmentToken.issue(user=admin_user, purpose="reset", created_by=None)
    assert entry.complete(password=None, code=pyotp.TOTP(entry.totp_secret).now()) is True
    assert EnrollmentToken.find_usable(token) is None


def test_complete_new_sets_password_and_device():
    user = User.objects.create_user("newbie", is_staff=True)
    entry, _ = EnrollmentToken.issue(user=user, purpose="new", created_by=None)
    assert entry.needs_password is True
    code = pyotp.TOTP(entry.totp_secret).now()
    assert entry.complete(password="a-long-new-password-7", code=code) is True
    user.refresh_from_db()
    assert user.check_password("a-long-new-password-7")
    assert user.totp.verify(code) is False


def test_complete_wrong_code_changes_nothing():
    user = User.objects.create_user("newbie", is_staff=True)
    entry, _ = EnrollmentToken.issue(user=user, purpose="new", created_by=None)
    assert entry.complete(password="a-long-new-password-7", code="000000") is False
    user.refresh_from_db()
    assert not user.has_usable_password()
    assert not TOTPDevice.objects.filter(user=user).exists()


def test_reset_replaces_device_keeps_password(admin_user):
    TOTPDevice.objects.create(user=admin_user, secret="OLDSECRETOLDSECRET")
    entry, _ = EnrollmentToken.issue(user=admin_user, purpose="reset", created_by=None)
    assert entry.needs_password is False
    assert entry.complete(password=None, code=pyotp.TOTP(entry.totp_secret).at(time.time())) is True
    admin_user.refresh_from_db()
    assert admin_user.totp.secret == entry.totp_secret
    assert admin_user.check_password("correct-horse-battery-9")


def test_createadmin_prints_enroll_link():
    out = StringIO()
    call_command("createadmin", "boss", stdout=out)
    user = User.objects.get(username="boss")
    assert user.is_staff and not user.has_usable_password()
    line = out.getvalue().strip()
    assert line.startswith("/enroll/")
    assert EnrollmentToken.find_usable(line.removeprefix("/enroll/")).user == user


def test_createadmin_rejects_existing_username(admin_user):
    with pytest.raises(CommandError):
        call_command("createadmin", "admin", stdout=StringIO())
