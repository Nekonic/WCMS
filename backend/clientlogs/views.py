"""클라이언트 로그 조회 및 배치 업로드 API.

GET  /api/logs/          필터: client(UUID), level(str), since(ISO datetime -> created_at__gte)
POST /api/client/logs/   클라이언트 인증서 인증 후 로그 배치 업로드 (설계 4.3)
"""
from django.utils.dateparse import parse_datetime
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from fleet.auth import ClientCertAuthentication, IsEnrolledClient

from .models import ClientLog
from .serializers import ClientLogSerializer, LogBatchSerializer


class ClientLogListView(generics.ListAPIView):
    """클라이언트 로그 목록 (최신순). 필터: client, level, since."""
    serializer_class = ClientLogSerializer

    def get_queryset(self):
        qs = ClientLog.objects.select_related("client").order_by("-created_at")
        params = self.request.query_params
        if client_id := params.get("client"):
            qs = qs.filter(client_id=client_id)
        if level := params.get("level"):
            qs = qs.filter(level=level)
        if since_str := params.get("since"):
            since_dt = parse_datetime(since_str)
            if since_dt is None:
                raise ValidationError({"since": "올바르지 않은 ISO datetime 형식입니다."})
            qs = qs.filter(created_at__gte=since_dt)
        return qs


class LogBatchUploadView(APIView):
    """클라이언트 로그 배치 업로드 (설계 4.3).

    POST /api/client/logs/

    클라이언트 인증서(mTLS 포워딩 헤더)로 인증된 PC 가 구조화 로그를 배치로
    업로드한다. request.user 는 ClientCertAuthentication 이 주입한 Client 이다.

    Request JSON:
        {
            "logs": [
                {
                    "level":     str (debug/info/warning/error/critical, required),
                    "message":   str (required),
                    "detail":    object|null (optional),
                    "source":    str (optional),
                    "client_ts": ISO 8601 datetime (optional)
                },
                ...
            ]
        }

    Response 201:
        {"created": N}

    Errors:
        400 — 본문 형식 오류 또는 logs 배열이 비어 있음
        401 — 인증서 헤더 없음
        403 — 인증서가 있지만 유효하지 않거나 ENROLLED 상태 아님
    """

    authentication_classes = [ClientCertAuthentication]
    permission_classes = [IsEnrolledClient]

    def post(self, request) -> Response:
        """로그 배열을 검증하고 Client 에 연결해 일괄 저장한다."""
        ser = LogBatchSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        client = request.user
        entries: list[dict] = ser.validated_data["logs"]

        objs = [
            ClientLog(
                client=client,
                level=entry["level"],
                message=entry["message"],
                detail=entry.get("detail"),
                source=entry.get("source", ""),
                client_ts=entry.get("client_ts"),
            )
            for entry in entries
        ]
        ClientLog.objects.bulk_create(objs)

        return Response({"created": len(objs)}, status=status.HTTP_201_CREATED)
