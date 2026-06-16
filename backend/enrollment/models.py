"""등록(enrollment) 토큰 모델 (레거시 pc_registration_tokens).

최초 enrollment 시 PIN(단기·일회/재사용) 인증용. 인증 통과 후 server 가
Client 와 인증서를 발급한다(설계 4.2).
"""
from django.db import models


class EnrollmentToken(models.Model):
    class UsageType(models.TextChoices):
        SINGLE = "single", "1회용"
        MULTI = "multi", "재사용"

    token = models.CharField(max_length=16, unique=True)
    usage_type = models.CharField(
        max_length=8, choices=UsageType.choices, default=UsageType.SINGLE,
    )
    expires_in = models.PositiveIntegerField(default=600, help_text="초")
    is_expired = models.BooleanField(default=False)
    used_count = models.PositiveIntegerField(default=0)
    created_by = models.CharField(max_length=150)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(fields=["token"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self):
        return f"{self.token} ({self.usage_type})"
