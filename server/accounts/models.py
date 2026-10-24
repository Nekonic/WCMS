import hashlib
import secrets
from datetime import timedelta

import pyotp
from django.conf import settings
from django.db import models, transaction
from django.utils import timezone

from accounts.totp import matching_step


class TOTPDevice(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="totp")
    secret = models.CharField(max_length=64)
    last_used_step = models.BigIntegerField(default=0)

    def verify(self, code: str) -> bool:
        step = matching_step(self.secret, code)
        if step is None:
            return False
        updated = TOTPDevice.objects.filter(pk=self.pk, last_used_step__lt=step).update(last_used_step=step)
        if updated:
            self.last_used_step = step
        return updated == 1


class EnrollmentToken(models.Model):
    NEW = "new"
    RESET = "reset"
    PURPOSES = [(NEW, "새 계정"), (RESET, "인증 앱 재설정")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="enrollments")
    token_hash = models.CharField(max_length=64, unique=True)
    purpose = models.CharField(max_length=8, choices=PURPOSES)
    totp_secret = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    @staticmethod
    def hash_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    @classmethod
    def issue(cls, *, user, purpose: str, created_by) -> tuple["EnrollmentToken", str]:
        now = timezone.now()
        cls.objects.filter(user=user, used_at__isnull=True, expires_at__gt=now).update(expires_at=now)
        token = secrets.token_urlsafe(32)
        entry = cls.objects.create(
            user=user,
            token_hash=cls.hash_token(token),
            purpose=purpose,
            totp_secret=pyotp.random_base32(),
            expires_at=now + timedelta(hours=settings.WCMS_ENROLL_HOURS),
            created_by=created_by if created_by is not None and created_by.is_authenticated else None,
        )
        return entry, token

    @classmethod
    def find_usable(cls, token: str) -> "EnrollmentToken | None":
        return (
            cls.objects.select_related("user")
            .filter(token_hash=cls.hash_token(token), used_at__isnull=True, expires_at__gt=timezone.now())
            .first()
        )

    @property
    def needs_password(self) -> bool:
        return self.purpose == self.NEW

    def complete(self, *, password: str | None, code: str) -> bool:
        step = matching_step(self.totp_secret, code)
        if step is None:
            return False
        with transaction.atomic():
            now = timezone.now()
            claimed = EnrollmentToken.objects.filter(
                pk=self.pk, used_at__isnull=True, expires_at__gt=now
            ).update(used_at=now)
            if claimed != 1:
                return False
            if self.needs_password:
                self.user.set_password(password)
                self.user.save(update_fields=["password"])
            TOTPDevice.objects.update_or_create(
                user=self.user, defaults={"secret": self.totp_secret, "last_used_step": step}
            )
            self.used_at = now
        return True
