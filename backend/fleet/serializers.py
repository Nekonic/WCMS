from rest_framework import serializers

from .models import ClientDynamicInfo, ClientSpecs


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
