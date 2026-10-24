from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import record
from labs.models import PC, RegistrationPin, Room
from labs.serializers import PCSerializer, PinCreateSerializer, PinSerializer, RoomSerializer, SeatsSerializer
from wcms.api import error_responses
from wcms.groups import pc_group


def room_changed(room_id: int) -> None:
    """좌석이나 실습실 정보가 바뀌었을 때 부른다. 실시간 알림은 live 앱이 연결한다."""


def unseat(queryset) -> None:
    queryset.update(room=None, row=None, col=None)


class RoomList(generics.ListCreateAPIView):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer

    def perform_create(self, serializer) -> None:
        room = serializer.save()
        record(self.request.user, "room.create", f"room:{room.id}", name=room.name)


class RoomDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer

    def perform_update(self, serializer) -> None:
        with transaction.atomic():
            room = serializer.save()
            unseat(PC.objects.filter(room=room, row__gte=room.rows) | PC.objects.filter(room=room, col__gte=room.cols))
        record(self.request.user, "room.update", f"room:{room.id}", **serializer.validated_data)
        room_changed(room.id)

    def perform_destroy(self, instance: Room) -> None:
        room_id = instance.id
        with transaction.atomic():
            unseat(PC.objects.filter(room=instance))
            instance.delete()
        record(self.request.user, "room.delete", f"room:{room_id}")
        room_changed(room_id)


def seats_payload(room: Room) -> dict:
    pcs = PC.objects.filter(room=room, row__isnull=False, col__isnull=False).order_by("row", "col")
    return {"seats": [{"row": pc.row, "col": pc.col, "pc": pc.id} for pc in pcs]}


class RoomSeats(APIView):
    @extend_schema(responses={200: SeatsSerializer})
    def get(self, request, pk: int):
        return Response(seats_payload(get_object_or_404(Room, pk=pk)))

    @extend_schema(request=SeatsSerializer, responses={200: SeatsSerializer, **error_responses(400)})
    def put(self, request, pk: int):
        room = get_object_or_404(Room, pk=pk)
        serializer = SeatsSerializer(data=request.data, context={"room": room})
        serializer.is_valid(raise_exception=True)
        seats = serializer.validated_data["seats"]
        moved_from = set(
            PC.objects.filter(id__in=[s["pc"].id for s in seats], room__isnull=False)
            .exclude(room=room)
            .values_list("room_id", flat=True)
        )
        with transaction.atomic():
            unseat(PC.objects.filter(room=room))
            unseat(PC.objects.filter(id__in=[s["pc"].id for s in seats]))
            for entry in seats:
                PC.objects.filter(pk=entry["pc"].id).update(room=room, row=entry["row"], col=entry["col"])
        record(request.user, "room.seats", f"room:{room.id}", count=len(seats))
        for room_id in {room.id, *moved_from}:
            room_changed(room_id)
        return Response(seats_payload(room))


class PCList(generics.ListAPIView):
    queryset = PC.objects.select_related("room")
    serializer_class = PCSerializer


class PCDetail(generics.DestroyAPIView):
    queryset = PC.objects.select_related("room")
    serializer_class = PCSerializer

    def perform_destroy(self, instance: PC) -> None:
        pc_id, room_id = instance.id, instance.room_id
        record(self.request.user, "pc.delete", f"pc:{pc_id}", hostname=instance.hostname)
        instance.delete()
        async_to_sync(get_channel_layer().group_send)(pc_group(pc_id), {"type": "pc.revoked"})
        if room_id is not None:
            room_changed(room_id)


class PinList(APIView):
    @extend_schema(responses={200: PinSerializer(many=True)})
    def get(self, request):
        return Response(PinSerializer(RegistrationPin.usable().order_by("-created_at"), many=True).data)

    @extend_schema(request=PinCreateSerializer, responses={201: PinSerializer, **error_responses(400)})
    def post(self, request):
        serializer = PinCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pin = RegistrationPin.issue(user=request.user, **serializer.validated_data)
        record(request.user, "pin.issue", f"pin:{pin.id}", multi_use=pin.multi_use)
        return Response(PinSerializer(pin).data, status=201)


class PinDetail(APIView):
    @extend_schema(responses={204: None, **error_responses(404)})
    def delete(self, request, pk: int):
        pin = get_object_or_404(RegistrationPin, pk=pk)
        pin.revoked = True
        pin.save(update_fields=["revoked"])
        record(request.user, "pin.revoke", f"pin:{pin.id}")
        return Response(status=204)
