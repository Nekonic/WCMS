from rest_framework import serializers

from .models import Client, ClientDynamicInfo, ClientSpecs, ClientVersion, Room


class ClientSpecsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientSpecs
        fields = ["cpu_model", "cpu_cores", "cpu_threads", "ram_total",
                  "disk_info", "os_edition", "os_version"]


class ClientDynamicSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientDynamicInfo
        fields = ["cpu_usage", "ram_used", "ram_usage_percent", "disk_usage",
                  "current_user", "uptime", "processes", "updated_at"]


class ClientListSerializer(serializers.Serializer):
    """PC 목록용 요약 필드."""
    id = serializers.UUIDField(read_only=True)
    hostname = serializers.CharField(read_only=True)
    room = serializers.SerializerMethodField()
    status = serializers.CharField(read_only=True)
    is_online = serializers.BooleanField(read_only=True)
    is_verified = serializers.BooleanField(read_only=True)
    last_seen = serializers.DateTimeField(read_only=True)
    ip_address = serializers.IPAddressField(read_only=True)
    mac_address = serializers.CharField(read_only=True)

    def get_room(self, obj):
        return obj.room.name if obj.room_id else None


class ClientDetailSerializer(ClientListSerializer):
    """PC 상세: 정적 스펙 + 동적 상태 포함."""
    enrolled_at = serializers.DateTimeField(read_only=True)
    specs = serializers.SerializerMethodField()
    dynamic = serializers.SerializerMethodField()

    def get_specs(self, obj):
        try:
            return ClientSpecsSerializer(obj.specs).data
        except ClientSpecs.DoesNotExist:
            return None

    def get_dynamic(self, obj):
        try:
            return ClientDynamicSerializer(obj.dynamic).data
        except ClientDynamicInfo.DoesNotExist:
            return None


# ---------------------------------------------------------------------------
# Room / Seat 직렬화
# ---------------------------------------------------------------------------

class RoomSerializer(serializers.ModelSerializer):
    """실습실 CRUD 직렬화."""
    class Meta:
        model = Room
        fields = ["id", "name", "rows", "cols", "description", "is_active",
                  "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class SeatClientSerializer(serializers.Serializer):
    """좌석 레이아웃 응답에 포함되는 간략 클라이언트 정보."""
    id = serializers.UUIDField(read_only=True)
    hostname = serializers.CharField(read_only=True)
    is_online = serializers.BooleanField(read_only=True)


class SeatAssignmentSerializer(serializers.Serializer):
    """좌석 배치 요청 항목."""
    row = serializers.IntegerField(min_value=0)
    col = serializers.IntegerField(min_value=0)
    client_id = serializers.UUIDField(allow_null=True, required=False, default=None)

    def validate_client_id(self, value):
        """client_id 가 주어졌을 때 실제 Client 존재 여부를 확인한다."""
        if value is not None and not Client.objects.filter(pk=value).exists():
            raise serializers.ValidationError("존재하지 않는 클라이언트 ID 입니다.")
        return value


class SeatLayoutUpdateSerializer(serializers.Serializer):
    """좌석 레이아웃 일괄 업데이트 요청 본문."""
    assignments = SeatAssignmentSerializer(many=True)


# ---------------------------------------------------------------------------
# ClientVersion 직렬화
# ---------------------------------------------------------------------------

class ClientVersionSerializer(serializers.ModelSerializer):
    """클라이언트 버전 레지스트리 직렬화."""
    class Meta:
        model = ClientVersion
        fields = ["id", "version", "download_url", "changelog", "released_at"]
        read_only_fields = ["id", "released_at"]
