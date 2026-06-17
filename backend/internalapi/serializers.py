"""게이트웨이 내부 API 요청/응답 직렬화기."""
from __future__ import annotations

from rest_framework import serializers

from commands.models import Command


# ---------------------------------------------------------------------------
# 프레즌스
# ---------------------------------------------------------------------------

class PresenceSerializer(serializers.Serializer):
    """POST /internal/presence/ 요청 바디."""

    client_id = serializers.UUIDField()
    event = serializers.ChoiceField(choices=["connect", "disconnect"])
    at = serializers.DateTimeField(required=False, default=None, allow_null=True)


# ---------------------------------------------------------------------------
# 텔레메트리: 하트비트
# ---------------------------------------------------------------------------

class HeartbeatSerializer(serializers.Serializer):
    """POST /internal/telemetry/heartbeat/ 요청 바디."""

    client_id = serializers.UUIDField()
    full = serializers.BooleanField(default=False)

    # 라이트/풀 공통 필수 필드
    cpu_usage = serializers.FloatField()
    ram_usage_percent = serializers.FloatField()

    # 풀 업데이트 전용 선택 필드
    ram_used = serializers.FloatField(required=False, allow_null=True, default=None)
    disk_usage = serializers.JSONField(required=False, allow_null=True, default=None)
    current_user = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, default=None
    )
    uptime = serializers.IntegerField(required=False, allow_null=True, default=None)
    processes = serializers.ListField(
        child=serializers.JSONField(), required=False, allow_null=True, default=None
    )
    ip_address = serializers.IPAddressField(required=False, allow_null=True, default=None)


# ---------------------------------------------------------------------------
# 텔레메트리: 명령 결과
# ---------------------------------------------------------------------------

class CommandResultSerializer(serializers.Serializer):
    """POST /internal/telemetry/command-result/ 요청 바디."""

    command_id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=["completed", "error", "timeout"])
    output = serializers.CharField(required=False, allow_null=True, allow_blank=True, default=None)
    error_message = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, default=None
    )
    exit_code = serializers.IntegerField(required=False, allow_null=True, default=None)


# ---------------------------------------------------------------------------
# 텔레메트리: 명령 ACK
# ---------------------------------------------------------------------------

class CommandAckSerializer(serializers.Serializer):
    """POST /internal/telemetry/command-ack/ 요청 바디."""

    command_id = serializers.IntegerField()


# ---------------------------------------------------------------------------
# 응답: 대기 중 명령 목록
# ---------------------------------------------------------------------------

class PendingCommandSerializer(serializers.ModelSerializer):
    """GET /internal/clients/<uuid>/pending-commands/ 응답 항목."""

    class Meta:
        model = Command
        fields = [
            "id",
            "command_type",
            "parameters",
            "priority",
            "timeout_seconds",
            "created_at",
        ]
