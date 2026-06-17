"""등록 토큰 직렬화."""
from rest_framework import serializers

from .models import EnrollmentToken


class EnrollmentTokenSerializer(serializers.ModelSerializer):
    """토큰 응답용 직렬화 (읽기 전용 필드 포함)."""
    class Meta:
        model = EnrollmentToken
        fields = ["id", "token", "usage_type", "expires_at", "created_by",
                  "is_expired", "used_count", "created_at"]
        read_only_fields = fields


class EnrollmentTokenCreateSerializer(serializers.Serializer):
    """토큰 생성 요청 본문."""
    usage_type = serializers.ChoiceField(choices=EnrollmentToken.UsageType.choices)
    expires_in = serializers.IntegerField(min_value=60, max_value=86400)
