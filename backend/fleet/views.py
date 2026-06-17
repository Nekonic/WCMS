"""PC(Client) / 실습실(Room) / 좌석(Seat) / 버전(ClientVersion) 관리 API.

클라이언트 생성은 enrollment 경로로만 이뤄지므로 Client API 는 목록/상세/삭제만 제공.
Room 과 ClientVersion 은 완전한 CRUD(ModelViewSet) 을 제공한다.
"""
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Client, ClientVersion, Room, Seat
from .serializers import (
    ClientDetailSerializer,
    ClientListSerializer,
    ClientVersionSerializer,
    RoomSerializer,
    SeatClientSerializer,
    SeatLayoutUpdateSerializer,
)

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


class RoomViewSet(viewsets.ModelViewSet):
    """실습실 CRUD API.

    GET    /api/rooms/        목록
    POST   /api/rooms/        생성
    GET    /api/rooms/<pk>/   상세
    PUT    /api/rooms/<pk>/   전체 수정
    PATCH  /api/rooms/<pk>/   부분 수정
    DELETE /api/rooms/<pk>/   삭제
    """
    queryset = Room.objects.all().order_by("name")
    serializer_class = RoomSerializer


class SeatLayoutView(APIView):
    """좌석 레이아웃 조회 및 일괄 배치 API.

    GET  /api/rooms/<room_name>/layout/
        -> {room, rows, cols, seats: [{row, col, client: {id, hostname, is_online} | null}]}
    POST /api/rooms/<room_name>/layout/
        body: {assignments: [{row, col, client_id|null}]}
        -> 동일 형식 응답 (upsert 후 전체 레이아웃 반환)
    """

    def _get_room(self, room_name: str) -> Room:
        return get_object_or_404(Room, name=room_name)

    def _layout_response(self, room: Room) -> dict:
        """실습실의 전체 좌석 레이아웃을 딕셔너리로 반환한다."""
        seats_qs = (
            Seat.objects.filter(room=room)
            .select_related("client")
            .order_by("row", "col")
        )
        seats = []
        for seat in seats_qs:
            client_data = None
            if seat.client_id is not None:
                client_data = SeatClientSerializer(seat.client).data
            seats.append({"row": seat.row, "col": seat.col, "client": client_data})
        return {"room": room.name, "rows": room.rows, "cols": room.cols, "seats": seats}

    def get(self, request, room_name: str):
        room = self._get_room(room_name)
        return Response(self._layout_response(room))

    @transaction.atomic
    def post(self, request, room_name: str):
        room = self._get_room(room_name)
        ser = SeatLayoutUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        for item in ser.validated_data["assignments"]:
            row = item["row"]
            col = item["col"]
            client_id = item.get("client_id")
            client = Client.objects.get(pk=client_id) if client_id else None
            Seat.objects.update_or_create(
                room=room, row=row, col=col,
                defaults={"client": client},
            )

        return Response(self._layout_response(room), status=status.HTTP_200_OK)


class ClientVersionViewSet(mixins.ListModelMixin, mixins.CreateModelMixin,
                           mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """클라이언트 버전 레지스트리 API.

    GET    /api/versions/      목록 (최신순)
    POST   /api/versions/      등록
    DELETE /api/versions/<pk>/ 삭제
    """
    queryset = ClientVersion.objects.all()
    serializer_class = ClientVersionSerializer
