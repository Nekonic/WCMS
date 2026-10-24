from rest_framework.generics import ListAPIView
from rest_framework.pagination import CursorPagination

from audit.models import AuditLog
from audit.serializers import AuditLogSerializer


class NewestFirst(CursorPagination):
    page_size = 50
    ordering = "-id"


class AuditLogList(ListAPIView):
    queryset = AuditLog.objects.select_related("actor")
    serializer_class = AuditLogSerializer
    pagination_class = NewestFirst
