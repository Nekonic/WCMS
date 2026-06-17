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
