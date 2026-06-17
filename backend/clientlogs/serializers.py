"""클라이언트 로그 직렬화."""
from rest_framework import serializers

from .models import ClientLog


class ClientLogSerializer(serializers.ModelSerializer):
    """로그 조회 응답용 직렬화."""
    class Meta:
        model = ClientLog
        fields = ["id", "client", "level", "message", "detail",
                  "source", "client_ts", "created_at"]
        read_only_fields = fields


class LogEntrySerializer(serializers.Serializer):
    """클라이언트가 배치 업로드할 단일 로그 항목."""

    LEVEL_CHOICES = [c[0] for c in ClientLog.Level.choices]

    level = serializers.ChoiceField(choices=LEVEL_CHOICES)
    message = serializers.CharField()
    detail = serializers.JSONField(required=False, allow_null=True, default=None)
    source = serializers.CharField(required=False, allow_blank=True, default="")
    client_ts = serializers.DateTimeField(required=False, allow_null=True, default=None)


class LogBatchSerializer(serializers.Serializer):
    """POST /api/client/logs/ 요청 본문 — logs 배열을 감싼 봉투(envelope)."""

    logs = serializers.ListField(
        child=LogEntrySerializer(),
        allow_empty=False,
        min_length=1,
    )
