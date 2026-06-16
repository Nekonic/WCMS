"""클라이언트 로그 수집 모델 (신규, 설계 9장).

클라이언트가 구조화 로그(JSON)를 배치로 업로드하고, critical 은 실시간 알림.
80대 규모라 Postgres 테이블 + 보존기간(client_logs 90일)으로 충분.
"""
from django.db import models


class ClientLog(models.Model):
    class Level(models.TextChoices):
        DEBUG = "debug", "DEBUG"
        INFO = "info", "INFO"
        WARNING = "warning", "WARNING"
        ERROR = "error", "ERROR"
        CRITICAL = "critical", "CRITICAL"

    client = models.ForeignKey(
        "fleet.Client", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="logs",
    )
    level = models.CharField(max_length=16, choices=Level.choices, default=Level.INFO)
    message = models.TextField()
    detail = models.JSONField(null=True, blank=True)
    source = models.CharField(max_length=128, blank=True, default="")
    client_ts = models.DateTimeField(null=True, blank=True, help_text="클라이언트 측 발생 시각")
    created_at = models.DateTimeField(auto_now_add=True, help_text="서버 수신 시각")

    class Meta:
        indexes = [
            models.Index(fields=["client", "-created_at"]),
            models.Index(fields=["level", "-created_at"]),
        ]

    def __str__(self):
        return f"[{self.level}] {self.message[:50]}"
