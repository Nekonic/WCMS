import time

import pyotp
import segno
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from drf_spectacular.utils import extend_schema
from rest_framework import serializers as drf_serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import EnrollmentToken, TOTPDevice
from accounts.serializers import (
    AdminCreatedSerializer,
    AdminCreateSerializer,
    AdminSerializer,
    CodeSerializer,
    EnrollCompleteSerializer,
    EnrollInfoSerializer,
    EnrollLinkSerializer,
    LoginResultSerializer,
    LoginSerializer,
    MeSerializer,
    admin_payload,
    me_payload,
)
from audit.services import record
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


enroll_attempts = FailureLimiter("enroll", limit=10, window=900)
INVALID_TOKEN = "링크가 만료됐거나 이미 사용됐습니다. 관리자에게 새 링크를 받으세요."


def usable_token(token: str) -> EnrollmentToken:
    entry = EnrollmentToken.find_usable(token)
    if entry is None:
        raise ApiError("invalid_token", INVALID_TOKEN, 404)
    return entry


@method_decorator([never_cache, csrf_protect], name="dispatch")
class EnrollView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses={200: EnrollInfoSerializer, **error_responses(404)})
    def get(self, request, token: str):
        entry = usable_token(token)
        uri = pyotp.TOTP(entry.totp_secret).provisioning_uri(name=entry.user.get_username(), issuer_name="WCMS")
        return Response(
            {
                "username": entry.user.get_username(),
                "needs_password": entry.needs_password,
                "secret": entry.totp_secret,
                "otp_uri": uri,
                "qr_svg": segno.make(uri, error="m").svg_inline(scale=5),
            }
        )

    @extend_schema(request=EnrollCompleteSerializer, responses={204: None, **error_responses(400, 404, 429)})
    def post(self, request, token: str):
        entry = usable_token(token)
        if enroll_attempts.blocked(entry.token_hash):
            raise ApiError("too_many_attempts", TOO_MANY, 429)
        serializer = EnrollCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        password = serializer.validated_data.get("password")
        if entry.needs_password:
            if not password:
                raise drf_serializers.ValidationError({"password": ["비밀번호를 입력하세요."]})
            try:
                validate_password(password, entry.user)
            except DjangoValidationError as exc:
                raise drf_serializers.ValidationError({"password": list(exc.messages)})
        if not entry.complete(password=password, code=serializer.validated_data["code"]):
            enroll_attempts.record(entry.token_hash)
            raise ApiError("invalid_code", "인증 코드가 올바르지 않습니다.")
        record(entry.user, "admin.enrolled", f"user:{entry.user.id}", purpose=entry.purpose)
        return Response(status=204)


def staff_users():
    return get_user_model().objects.filter(is_staff=True).select_related("totp")


def enroll_link(entry: EnrollmentToken, token: str) -> dict:
    return {"enroll_url": f"/enroll/{token}", "expires_at": entry.expires_at}


class AdminListView(APIView):
    @extend_schema(responses={200: AdminSerializer(many=True)})
    def get(self, request):
        return Response([admin_payload(user, request.user) for user in staff_users().order_by("username")])

    @extend_schema(request=AdminCreateSerializer, responses={201: AdminCreatedSerializer, **error_responses(400)})
    def post(self, request):
        serializer = AdminCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = get_user_model().objects.create_user(username=serializer.validated_data["username"], is_staff=True)
        entry, token = EnrollmentToken.issue(user=user, purpose=EnrollmentToken.NEW, created_by=request.user)
        record(request.user, "admin.create", f"user:{user.id}", username=user.get_username())
        return Response({"admin": admin_payload(user, request.user), **enroll_link(entry, token)}, status=201)


class AdminResetView(APIView):
    @extend_schema(request=None, responses={200: EnrollLinkSerializer, **error_responses(404)})
    def post(self, request, pk: int):
        user = get_object_or_404(staff_users(), pk=pk)
        purpose = EnrollmentToken.RESET if user.has_usable_password() else EnrollmentToken.NEW
        entry, token = EnrollmentToken.issue(user=user, purpose=purpose, created_by=request.user)
        record(request.user, "admin.reset", f"user:{user.id}", purpose=purpose)
        return Response(enroll_link(entry, token))


class AdminDetailView(APIView):
    @extend_schema(responses={204: None, **error_responses(400, 404)})
    def delete(self, request, pk: int):
        user = get_object_or_404(staff_users(), pk=pk)
        if user.id == request.user.id:
            raise ApiError("cannot_delete_self", "자기 계정은 삭제할 수 없습니다.")
        record(request.user, "admin.delete", f"user:{user.id}", username=user.get_username())
        user.delete()
        end_live_sessions(pk)
        return Response(status=204)
