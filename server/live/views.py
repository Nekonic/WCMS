from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from labs.models import Room
from live.serializers import LivePCSerializer, PublicRoomDetailSerializer, PublicRoomSerializer
from live.snapshots import pc_snapshot, public_room_snapshot, room_snapshot
from wcms.api import ApiError, error_responses

ROOM_FIELDS = ("id", "name", "rows", "cols", "aisle_after")


def public_room(room: Room) -> dict:
    return {field: getattr(room, field) for field in ROOM_FIELDS}


class PublicRoomList(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses={200: PublicRoomSerializer(many=True)})
    def get(self, request):
        return Response([public_room(room) for room in Room.objects.all()])


class PublicRoomDetail(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses={200: PublicRoomDetailSerializer, **error_responses(404)})
    def get(self, request, pk: int):
        room = get_object_or_404(Room, pk=pk)
        return Response({"room": public_room(room), "seats": public_room_snapshot(room.id)})


class RoomLivePCs(APIView):
    @extend_schema(responses={200: LivePCSerializer(many=True), **error_responses(404)})
    def get(self, request, pk: int):
        pcs = room_snapshot(pk)
        if pcs is None:
            raise ApiError("not_found", "없는 실습실입니다.", 404)
        return Response(pcs)


class PCLive(APIView):
    @extend_schema(responses={200: LivePCSerializer, **error_responses(404)})
    def get(self, request, pk: int):
        pc = pc_snapshot(pk)
        if pc is None:
            raise ApiError("not_found", "없는 PC입니다.", 404)
        return Response(pc)
