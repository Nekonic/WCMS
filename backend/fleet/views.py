"""PC(Client) 조회 API. 클라이언트 생성은 enrollment 경로로만 이뤄지므로
이 API 는 목록/상세/삭제만 제공한다.
"""
from rest_framework import mixins, viewsets

from .models import Client
from .serializers import ClientDetailSerializer, ClientListSerializer

_TRUE = {"1", "true", "yes", "on"}


class ClientViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                    mixins.DestroyModelMixin, viewsets.GenericViewSet):
    queryset = Client.objects.select_related("room", "specs", "dynamic")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ClientDetailSerializer
        return ClientListSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        if room := params.get("room"):
            qs = qs.filter(room__name=room)
        if status_ := params.get("status"):
            qs = qs.filter(status=status_)
        if (online := params.get("online")) is not None:
            qs = qs.filter(is_online=online.lower() in _TRUE)
        return qs.order_by("hostname")
