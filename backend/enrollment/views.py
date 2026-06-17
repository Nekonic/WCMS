"""등록 토큰 관리 API 및 클라이언트 등록(enrollment) 엔드포인트.

관리자 토큰 API:
    GET    /api/tokens/      유효 토큰 목록 (expires_at > now AND is_expired=False)
    POST   /api/tokens/      토큰 생성 (6자리 숫자, 고유)
    DELETE /api/tokens/<pk>/ 토큰 삭제

클라이언트 enrollment:
    POST   /api/client/enroll/  PIN + CSR 로 클라이언트 등록 및 인증서 발급
"""
import random
import string

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from fleet.models import Client

from .ca import sign_client_csr
from .models import EnrollmentToken
from .serializers import EnrollmentTokenCreateSerializer, EnrollmentTokenSerializer

_TOKEN_DIGITS = string.digits
_TOKEN_LENGTH = 6
_MAX_ATTEMPTS = 20


def _generate_unique_token() -> str:
    """유일한 6자리 숫자 토큰을 생성한다. 충돌 시 최대 20회 재시도."""
    for _ in range(_MAX_ATTEMPTS):
        candidate = "".join(random.choices(_TOKEN_DIGITS, k=_TOKEN_LENGTH))
        if not EnrollmentToken.objects.filter(token=candidate).exists():
            return candidate
    raise RuntimeError("6자리 토큰 생성 실패: 공간 부족")


class EnrollmentTokenListCreateView(APIView):
    """토큰 목록 조회 및 생성."""

    def get(self, request):
        now = timezone.now()
        qs = EnrollmentToken.objects.filter(
            expires_at__gt=now,
            is_expired=False,
        ).order_by("-created_at")
        return Response(EnrollmentTokenSerializer(qs, many=True).data)

    def post(self, request):
        ser = EnrollmentTokenCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        expires_in: int = ser.validated_data["expires_in"]
        usage_type: str = ser.validated_data["usage_type"]
        now = timezone.now()
        expires_at = now + timezone.timedelta(seconds=expires_in)

        token = _generate_unique_token()
        obj = EnrollmentToken.objects.create(
            token=token,
            usage_type=usage_type,
            expires_in=expires_in,
            expires_at=expires_at,
            created_by=request.user.username,
        )
        return Response(EnrollmentTokenSerializer(obj).data, status=status.HTTP_201_CREATED)


class EnrollmentTokenDeleteView(APIView):
    """토큰 개별 삭제."""

    def delete(self, request, pk: int):
        try:
            obj = EnrollmentToken.objects.get(pk=pk)
        except EnrollmentToken.DoesNotExist:
            return Response({"detail": "찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ClientEnrollView(APIView):
    """클라이언트(PC) enrollment 엔드포인트.

    POST /api/client/enroll/

    PC 가 PIN + CSR 을 제출하면 서버가 CA 로 서명한 클라이언트 인증서를 발급한다.
    인증은 PIN 기반이며 Django 세션/CSRF 와 무관하다(설계 4.2).

    Request JSON:
        pin         (str, required)  — EnrollmentToken.token 값
        csr_pem     (str, required)  — PEM 인코딩된 CSR
        hostname    (str, optional)  — PC 호스트명
        mac_address (str, optional)  — MAC 주소

    Response 201:
        client_id       — 발급된 클라이언트 UUID
        certificate_pem — 서버가 서명한 클라이언트 인증서 (PEM)
        ca_certificate_pem — 서버 CA 인증서 (PEM)

    Errors:
        400 — 필수 필드 누락 또는 CSR 파싱 실패
        403 — 토큰 미존재, 만료, 또는 1회용 토큰 재사용
    """

    authentication_classes: list = []
    permission_classes = [AllowAny]

    def post(self, request) -> Response:
        """PIN + CSR 을 검증하고 클라이언트 인증서를 발급한다."""
        pin: str | None = request.data.get("pin")
        csr_pem: str | None = request.data.get("csr_pem")
        hostname: str = request.data.get("hostname") or ""
        mac_address: str = request.data.get("mac_address") or ""

        # 필수 필드 검증
        if not pin:
            return Response(
                {"detail": "pin 필드가 필요합니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not csr_pem:
            return Response(
                {"detail": "csr_pem 필드가 필요합니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # CSR 파싱 (토큰 검증 전에 먼저 확인해 빠른 실패를 유도)
        try:
            csr = x509.load_pem_x509_csr(
                csr_pem.encode() if isinstance(csr_pem, str) else csr_pem
            )
        except (ValueError, Exception):
            return Response(
                {"detail": "CSR 파싱에 실패했습니다. PEM 형식을 확인하세요."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 토큰 조회 및 유효성 검증
        now = timezone.now()
        try:
            token = EnrollmentToken.objects.get(token=pin)
        except EnrollmentToken.DoesNotExist:
            return Response(
                {"detail": "유효하지 않은 PIN 입니다."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if token.is_expired or token.expires_at <= now:
            return Response(
                {"detail": "만료된 PIN 입니다."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if (
            token.usage_type == EnrollmentToken.UsageType.SINGLE
            and token.used_count > 0
        ):
            return Response(
                {"detail": "이미 사용된 1회용 PIN 입니다."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # 트랜잭션 내에서 Client 생성 + 인증서 발급 + 토큰 사용 처리
        with transaction.atomic():
            client = Client.objects.create(
                status=Client.Status.ENROLLED,
                hostname=hostname,
                mac_address=mac_address,
                enrolled_with_token=token,
                is_verified=True,
            )

            cert = sign_client_csr(csr, str(client.id))
            cert_pem: str = cert.public_bytes(
                serialization.Encoding.PEM
            ).decode()
            client.certificate_pem = cert_pem
            client.save(update_fields=["certificate_pem"])

            token.used_count += 1
            if token.usage_type == EnrollmentToken.UsageType.SINGLE:
                token.is_expired = True
            token.save(update_fields=["used_count", "is_expired"])

        # CA 인증서를 응답에 포함해 클라이언트가 체인 검증에 사용하도록 한다
        from .ca import get_ca
        from cryptography.hazmat.primitives import serialization as _ser

        ca_cert, _ = get_ca()
        ca_cert_pem: str = ca_cert.public_bytes(_ser.Encoding.PEM).decode()

        return Response(
            {
                "client_id": str(client.id),
                "certificate_pem": cert_pem,
                "ca_certificate_pem": ca_cert_pem,
            },
            status=status.HTTP_201_CREATED,
        )
