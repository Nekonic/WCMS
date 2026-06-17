"""클라이언트 로그 조회 API.

GET /api/logs/   필터: client(UUID), level(str), since(ISO datetime -> created_at__gte)
"""
from django.utils.dateparse import parse_datetime
from rest_framework import generics
from rest_framework.exceptions import ValidationError

from .models import ClientLog
from .serializers import ClientLogSerializer


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
