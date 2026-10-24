import hashlib
import secrets
from datetime import datetime, timedelta

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone


class Room(models.Model):
    name = models.CharField(max_length=50, unique=True)
    rows = models.PositiveSmallIntegerField(default=5)
    cols = models.PositiveSmallIntegerField(default=8)
    aisle_after = models.PositiveSmallIntegerField(null=True, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self) -> str:
        return self.name


class PC(models.Model):
    hostname = models.CharField(max_length=64)
    machine_guid = models.CharField(max_length=64, unique=True)
    token_hash = models.CharField(max_length=64, unique=True)
    client_version = models.CharField(max_length=20, blank=True)
    specs = models.JSONField(default=dict)
    status = models.JSONField(default=dict)
    room = models.ForeignKey(
        Room, null=True, blank=True, on_delete=models.SET_NULL, related_name="pcs"
    )
    row = models.PositiveSmallIntegerField(null=True, blank=True)
    col = models.PositiveSmallIntegerField(null=True, blank=True)
    online = models.BooleanField(default=False)
    connection = models.CharField(max_length=128, blank=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["hostname"]
        constraints = [
            models.UniqueConstraint(fields=["room", "row", "col"], name="unique_seat"),
        ]

    def __str__(self) -> str:
        return self.label

    @staticmethod
    def hash_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    @classmethod
    def register(
        cls, *, hostname: str, machine_guid: str, specs: dict, version: str
    ) -> tuple["PC", str]:
        token = secrets.token_urlsafe(32)
        pc, _ = cls.objects.update_or_create(
            machine_guid=machine_guid,
            defaults={
                "hostname": hostname,
                "specs": specs,
                "client_version": version,
                "token_hash": cls.hash_token(token),
            },
        )
        return pc, token

    @classmethod
    def from_token(cls, token: str) -> "PC | None":
        return cls.objects.select_related("room").filter(token_hash=cls.hash_token(token)).first()

    @property
    def label(self) -> str:
        if self.room is not None and self.row is not None and self.col is not None:
            return f"{self.room.name}-{self.row * self.room.cols + self.col + 1:02d}"
        return self.hostname

    @property
    def is_online(self) -> bool:
        if not self.online or self.last_seen is None:
            return False
        return timezone.now() - self.last_seen < timedelta(seconds=settings.WCMS_CLIENT_STALE_SECONDS)


class RegistrationPin(models.Model):
    pin = models.CharField(max_length=6, unique=True)
    multi_use = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    used_count = models.PositiveIntegerField(default=0)
    revoked = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)

    @classmethod
    def issue(cls, *, user, multi_use: bool, minutes: int) -> "RegistrationPin":
        for _ in range(20):
            pin = f"{secrets.randbelow(10**6):06d}"
            if not cls.objects.filter(pin=pin).exists():
                return cls.objects.create(
                    pin=pin,
                    multi_use=multi_use,
                    expires_at=timezone.now() + timedelta(minutes=minutes),
                    created_by=user,
                )
        raise RuntimeError("PIN을 만들지 못했습니다.")

    def is_usable(self, now: datetime | None = None) -> bool:
        now = now or timezone.now()
        if self.revoked or now >= self.expires_at:
            return False
        return self.multi_use or self.used_count == 0

    @classmethod
    def consume(cls, pin: str) -> bool:
        with transaction.atomic():
            obj = cls.objects.select_for_update().filter(pin=pin).first()
            if obj is None or not obj.is_usable():
                return False
            obj.used_count += 1
            obj.save(update_fields=["used_count"])
            return True
