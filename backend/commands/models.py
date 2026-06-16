"""명령 큐 모델 (레거시 commands).

신규: delivery_mode(drop/queue) + expires_at(TTL) + ack 생명주기(설계 4.4),
issuer(감사) 추가. 전달 정책 기본값은 발행 계층에서 명령 타입별로 설정한다.
"""
from django.conf import settings
from django.db import models


class Command(models.Model):
    class DeliveryMode(models.TextChoices):
        DROP_IF_OFFLINE = "drop_if_offline", "오프라인 시 폐기"
        QUEUE = "queue", "큐잉(재연결 시 전달)"

    class Status(models.TextChoices):
        PENDING = "pending", "대기"
        SENT = "sent", "전달됨"
        EXECUTING = "executing", "실행 중"
        COMPLETED = "completed", "완료"
        ERROR = "error", "에러"
        TIMEOUT = "timeout", "타임아웃"
        EXPIRED = "expired", "만료"

    client = models.ForeignKey(
        "fleet.Client", on_delete=models.CASCADE, related_name="commands",
    )
    issuer = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="issued_commands",
    )
    command_type = models.CharField(max_length=64)
    parameters = models.JSONField(default=dict, blank=True)
    priority = models.PositiveIntegerField(default=5)

    delivery_mode = models.CharField(
        max_length=16, choices=DeliveryMode.choices, default=DeliveryMode.QUEUE,
    )
    expires_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    result = models.TextField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    timeout_seconds = models.PositiveIntegerField(default=300)

    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["client", "status"]),
            models.Index(fields=["status", "priority", "created_at"]),
            models.Index(fields=["issuer", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.command_type}<{self.client_id}> {self.status}"
