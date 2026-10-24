from django.contrib.auth import get_user_model
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
