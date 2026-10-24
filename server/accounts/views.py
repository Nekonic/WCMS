import time

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import TOTPDevice
from accounts.serializers import CodeSerializer, LoginResultSerializer, LoginSerializer, MeSerializer, me_payload
from wcms.api import ApiError, error_responses, is_admin
from wcms.groups import user_group
from wcms.limits import FailureLimiter
from wcms.net import client_ip

PENDING_KEY = "auth_pending"
BACKEND = "django.contrib.auth.backends.ModelBackend"
TOO_MANY = "잠시 후 다시 시도하세요."

login_pair = FailureLimiter("login-pair", limit=5, window=900)
login_ip = FailureLimiter("login-ip", limit=20, window=900)
login_user = FailureLimiter("login-user", limit=50, window=900)
otp_user = FailureLimiter("otp-user", limit=5, window=900)


def end_live_sessions(user_id: int) -> None:
    async_to_sync(get_channel_layer().group_send)(user_group(user_id), {"type": "session.end"})


@method_decorator(ensure_csrf_cookie, name="dispatch")
class MeView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses={200: MeSerializer})
    def get(self, request):
        return Response(me_payload(request.user if is_admin(request.user) else None))


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=LoginSerializer, responses={200: LoginResultSerializer, **error_responses(400, 403, 429)})
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        username = serializer.validated_data["username"]
        name_key = username.lower()
        ip = client_ip(request)
        pair_key = f"{ip}|{name_key}"
        if login_pair.blocked(pair_key) or login_ip.blocked(ip) or login_user.blocked(name_key):
            raise ApiError("too_many_attempts", TOO_MANY, 429)

        user = authenticate(request._request, username=username, password=serializer.validated_data["password"])
        if user is None or not user.is_staff:
            login_pair.record(pair_key)
            login_ip.record(ip)
            login_user.record(name_key)
            raise ApiError("invalid_credentials", "아이디 또는 비밀번호가 올바르지 않습니다.")
        if not TOTPDevice.objects.filter(user=user).exists():
            raise ApiError("totp_not_enrolled", "인증 앱 등록이 필요합니다. 관리자에게 등록 링크를 받으세요.", 403)
        if otp_user.blocked(str(user.pk)):
            raise ApiError("too_many_attempts", TOO_MANY, 429)

        login_pair.reset(pair_key)
        request.session[PENDING_KEY] = {"user": user.pk, "until": time.time() + settings.WCMS_PENDING_LOGIN_SECONDS}
        return Response({"next": "otp"})


@method_decorator(csrf_protect, name="dispatch")
class OtpView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=CodeSerializer, responses={200: MeSerializer, **error_responses(400, 401, 429)})
    def post(self, request):
        serializer = CodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pending = request.session.get(PENDING_KEY) or {}
        user = None
        if pending.get("until", 0) > time.time():
            user = get_user_model().objects.filter(pk=pending.get("user"), is_active=True, is_staff=True).first()
        if user is None:
            request.session.pop(PENDING_KEY, None)
            raise ApiError("no_pending_login", "처음부터 다시 로그인하세요.", 401)

        ident = str(user.pk)
        if otp_user.blocked(ident):
            request.session.pop(PENDING_KEY, None)
            raise ApiError("too_many_attempts", TOO_MANY, 429)
        device = TOTPDevice.objects.filter(user=user).first()
        if device is None or not device.verify(serializer.validated_data["code"]):
            otp_user.record(ident)
            if otp_user.blocked(ident):
                request.session.pop(PENDING_KEY, None)
            raise ApiError("invalid_code", "인증 코드가 올바르지 않습니다.")

        request.session.pop(PENDING_KEY, None)
        otp_user.reset(ident)
        login(request._request, user, backend=BACKEND)
        return Response(me_payload(user))


class LogoutView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=None, responses={204: None})
    def post(self, request):
        user_id = request.user.pk if request.user.is_authenticated else None
        logout(request._request)
        if user_id is not None:
            end_live_sessions(user_id)
        return Response(status=204)
