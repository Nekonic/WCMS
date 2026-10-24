import json

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from labs.models import PC, RegistrationPin
from wcms.api import ApiError
from wcms.groups import pc_group
from wcms.limits import FailureLimiter
from wcms.net import client_ip

MAX_SPECS_BYTES = 16384
pin_failures = FailureLimiter("register-ip", limit=10, window=600)


class PinField(serializers.RegexField):
    """JSON 문자열, ASCII 숫자 6자리. 숫자 타입, 유니코드 숫자, 공백은 거절한다."""

    def __init__(self, **kwargs):
        super().__init__(r"\A[0-9]{6}\Z", trim_whitespace=False, **kwargs)

    def to_internal_value(self, data):
        if not isinstance(data, str):
            self.fail("invalid")
        return super().to_internal_value(data)


class RegisterSerializer(serializers.Serializer):
    pin = PinField()
    hostname = serializers.CharField(max_length=64)
    machine_guid = serializers.CharField(max_length=64)
    specs = serializers.JSONField(required=False, default=dict)
    version = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")

    def validate_specs(self, value) -> dict:
        if not isinstance(value, dict):
            raise serializers.ValidationError("객체여야 합니다.")
        try:
            encoded = json.dumps(value, ensure_ascii=False).encode("utf-8")
        except UnicodeEncodeError:
            raise serializers.ValidationError("UTF-8로 표현할 수 없는 문자열이 있습니다.")
        if len(encoded) > MAX_SPECS_BYTES:
            raise serializers.ValidationError("너무 큽니다.")
        return value


@extend_schema(exclude=True)
class RegisterView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]

    def post(self, request):
        ip = client_ip(request)
        if pin_failures.blocked(ip):
            raise ApiError("too_many_attempts", "잠시 후 다시 시도하세요.", 429)
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if not RegistrationPin.consume(data["pin"]):
            pin_failures.record(ip)
            raise ApiError("invalid_pin", "PIN이 올바르지 않거나 만료되었습니다.", 403)
        existed = PC.objects.filter(machine_guid=data["machine_guid"]).exists()
        pc, token = PC.register(
            hostname=data["hostname"], machine_guid=data["machine_guid"], specs=data["specs"], version=data["version"]
        )
        if existed:
            async_to_sync(get_channel_layer().group_send)(pc_group(pc.id), {"type": "pc.revoked"})
        return Response({"pc_id": pc.id, "token": token}, status=201)
