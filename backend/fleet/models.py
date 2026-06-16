"""실습실 PC 신원/관리 모델.

레거시 pc_info(machine_id 기반)를 Client 로 흡수한다. 신원은 하드웨어가 아니라
server 가 발급한 UUID 와 공개키 인증서(PKC)로 정의된다(설계 4.2). 정적/동적
텔레메트리는 OneToOne 으로 분리한다.
"""
import uuid

from django.db import models
from django.utils import timezone


class Room(models.Model):
    """실습실 + 좌석 그리드 크기 (레거시 seat_layout)."""
    name = models.CharField(max_length=64, unique=True)
    rows = models.PositiveIntegerField(default=6)
    cols = models.PositiveIntegerField(default=8)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Client(models.Model):
    """관리 대상 PC = 영속 신원 + 관리 메타데이터 (레거시 pc_info 흡수)."""

    class Status(models.TextChoices):
        ENROLLED = "enrolled", "등록됨"
        REVOKED = "revoked", "취소됨"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ENROLLED)

    # PKC: enrollment 시 server 가 발급한 클라이언트 인증서(PEM). 레거시 이관분은 null.
    certificate_pem = models.TextField(null=True, blank=True)
    enrolled_with_token = models.ForeignKey(
        "enrollment.EnrollmentToken", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="clients",
    )
    # 레거시 이관/전환용 기존 machine_id(첫 MAC 기반). 신규 클라이언트는 사용 안 함.
    legacy_machine_id = models.CharField(max_length=64, null=True, blank=True, unique=True)

    # 하드웨어 메타데이터 (신원 아님)
    hostname = models.CharField(max_length=255)
    mac_address = models.CharField(max_length=32, blank=True, default="")

    # 관리/배치 상태
    room = models.ForeignKey(
        Room, null=True, blank=True, on_delete=models.SET_NULL, related_name="clients",
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)

    enrolled_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["is_online", "last_seen"]),
            models.Index(fields=["room"]),
        ]

    def __str__(self):
        return f"{self.hostname} ({self.id})"


class ClientSpecs(models.Model):
    """정적 하드웨어 스펙 (레거시 pc_specs)."""
    client = models.OneToOneField(Client, on_delete=models.CASCADE, related_name="specs")
    cpu_model = models.CharField(max_length=255)
    cpu_cores = models.PositiveIntegerField()
    cpu_threads = models.PositiveIntegerField()
    ram_total = models.FloatField(help_text="GB")
    disk_info = models.JSONField(default=dict)
    os_edition = models.CharField(max_length=255)
    os_version = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"specs<{self.client_id}>"


class ClientDynamicInfo(models.Model):
    """최신 동적 상태 (레거시 pc_dynamic_info, PC 당 1행)."""
    client = models.OneToOneField(Client, on_delete=models.CASCADE, related_name="dynamic")
    cpu_usage = models.FloatField()
    ram_used = models.FloatField(help_text="GB")
    ram_usage_percent = models.FloatField()
    disk_usage = models.JSONField(null=True, blank=True)
    current_user = models.CharField(max_length=255, null=True, blank=True)
    uptime = models.PositiveIntegerField(help_text="초")
    processes = models.JSONField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"dynamic<{self.client_id}>"


class Seat(models.Model):
    """좌석 그리드 셀 -> Client 배치 (레거시 seat_map)."""
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="seats")
    row = models.PositiveIntegerField()
    col = models.PositiveIntegerField()
    client = models.ForeignKey(
        Client, null=True, blank=True, on_delete=models.SET_NULL, related_name="seats",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["room", "row", "col"], name="uniq_seat_cell"),
        ]
        indexes = [models.Index(fields=["room"]), models.Index(fields=["client"])]

    def __str__(self):
        return f"{self.room.name}[{self.row},{self.col}]"


class NetworkEvent(models.Model):
    """오프라인/온라인 이력 (레거시 network_events)."""
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="network_events")
    offline_at = models.DateTimeField()
    online_at = models.DateTimeField(null=True, blank=True)
    duration_sec = models.PositiveIntegerField(null=True, blank=True)
    reason = models.CharField(max_length=32, default="unknown")

    class Meta:
        indexes = [models.Index(fields=["client", "-offline_at"])]

    def __str__(self):
        return f"netevent<{self.client_id}> {self.reason}"


class ClientVersion(models.Model):
    """클라이언트 버전 레지스트리 (레거시 client_versions).

    레거시는 released_at(초 단위) 정렬로 같은-초 등록 시 '최신'이 비결정적이었다.
    여기서는 (-released_at, -id) 정렬로 결정론적으로 최신을 선택한다.
    """
    version = models.CharField(max_length=64)
    download_url = models.CharField(max_length=512, null=True, blank=True)
    changelog = models.TextField(blank=True, default="")
    released_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-released_at", "-id"]
        indexes = [models.Index(fields=["-released_at", "-id"])]

    def __str__(self):
        return self.version
