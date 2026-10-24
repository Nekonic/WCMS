from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.generics import ListAPIView
from rest_framework.pagination import CursorPagination

from audit.models import AuditLog
from audit.serializers import AuditLogSerializer
from wcms.api import error_responses


class NewestFirst(CursorPagination):
    page_size = 50
    ordering = "-id"


@extend_schema_view(
    get=extend_schema(responses={200: AuditLogSerializer(many=True), **error_responses(404)}),
)
class AuditLogList(ListAPIView):
    queryset = AuditLog.objects.select_related("actor")
    serializer_class = AuditLogSerializer
    pagination_class = NewestFirst
