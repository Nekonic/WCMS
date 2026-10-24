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
