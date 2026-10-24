from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers


class UserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()


class MeSerializer(serializers.Serializer):
    authenticated = serializers.BooleanField()
    user = UserSerializer(allow_null=True)


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=128, trim_whitespace=False)


class LoginResultSerializer(serializers.Serializer):
    next = serializers.ChoiceField(choices=["otp"])


class CodeSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=10)


def me_payload(user) -> dict:
    if user is None:
        return {"authenticated": False, "user": None}
    return {"authenticated": True, "user": {"id": user.id, "username": user.get_username()}}


class EnrollInfoSerializer(serializers.Serializer):
    username = serializers.CharField()
    needs_password = serializers.BooleanField()
    secret = serializers.CharField()
    otp_uri = serializers.CharField()
    qr_svg = serializers.CharField()


class EnrollCompleteSerializer(serializers.Serializer):
    password = serializers.CharField(max_length=128, required=False, trim_whitespace=False)
    code = serializers.CharField(max_length=10)


class AdminSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    totp_enrolled = serializers.BooleanField()
    is_self = serializers.BooleanField()


class AdminCreateSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, validators=[get_user_model().username_validator])

    def validate_username(self, value: str) -> str:
        # create_user()가 저장할 때와 같은 NFKC 정규화를 먼저 해야 전각 "ａｄｍｉｎ" 같은 중복을 잡는다
        # 정규화로 글자가 늘거나(ﷺ) 허용하지 않는 글자가 생길 수 있으므로(½ → 1⁄2) 규칙을 다시 확인한다
        value = get_user_model().normalize_username(value)
        if len(value) > 150:
            raise serializers.ValidationError("150자 이하로 입력하세요.")
        try:
            get_user_model().username_validator(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        if get_user_model().objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("이미 있는 아이디입니다.")
        return value


class EnrollLinkSerializer(serializers.Serializer):
    enroll_url = serializers.CharField()
    expires_at = serializers.DateTimeField()


class AdminCreatedSerializer(EnrollLinkSerializer):
    admin = AdminSerializer()


def admin_payload(user, current) -> dict:
    return {
        "id": user.id,
        "username": user.get_username(),
        "totp_enrolled": hasattr(user, "totp"),
        "is_self": user.id == current.id,
    }
