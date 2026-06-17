"""명령 발행/조회 API.

발행은 issuer=request.user 로 감사 기록을 남기고 delivery_mode 기본값을 타입별로
부여한다(commands.services). 게이트웨이 push 는 Phase 2.
"""
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from fleet.models import Client

from .models import Command
from .serializers import CommandCreateSerializer, CommandSerializer
from .services import issue_command


class ClientCommandsView(APIView):
    """GET: PC 명령 이력 / POST: 명령 발행."""

    def get(self, request, pc_id):
        client = get_object_or_404(Client, pk=pc_id)
        qs = client.commands.select_related("issuer").order_by("-created_at")
        return Response(CommandSerializer(qs, many=True).data)

    def post(self, request, pc_id):
        client = get_object_or_404(Client, pk=pc_id)
        ser = CommandCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        cmd = issue_command(client=client, issuer=request.user, **ser.validated_data)
        return Response(CommandSerializer(cmd).data, status=status.HTTP_201_CREATED)


class BulkCommandView(APIView):
    """여러 PC 에 동일 명령 발행."""

    def post(self, request):
        pc_ids = request.data.get("pc_ids")
        if not isinstance(pc_ids, list) or not pc_ids:
            return Response({"detail": "pc_ids(리스트)가 필요합니다"},
                            status=status.HTTP_400_BAD_REQUEST)
        ser = CommandCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        clients = Client.objects.filter(pk__in=pc_ids)
        created = [issue_command(client=c, issuer=request.user, **ser.validated_data)
                   for c in clients]
        return Response(
            {"created": len(created), "commands": CommandSerializer(created, many=True).data},
            status=status.HTTP_201_CREATED,
        )


class CommandListView(generics.ListAPIView):
    """명령 감사 목록 (status / client 필터)."""
    serializer_class = CommandSerializer

    def get_queryset(self):
        qs = Command.objects.select_related("issuer", "client").order_by("-created_at")
        params = self.request.query_params
        if status_ := params.get("status"):
            qs = qs.filter(status=status_)
        if client_id := params.get("client"):
            qs = qs.filter(client_id=client_id)
        return qs
