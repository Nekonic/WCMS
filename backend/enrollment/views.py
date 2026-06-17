"""등록 토큰 관리 API.

GET    /api/tokens/      유효 토큰 목록 (expires_at > now AND is_expired=False)
POST   /api/tokens/      토큰 생성 (6자리 숫자, 고유)
DELETE /api/tokens/<pk>/ 토큰 삭제
"""
import random
import string

from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

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
