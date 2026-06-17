"""게이트웨이-Django 내부 API 뷰 (설계 §3).

모든 엔드포인트는 Rust 게이트웨이 전용이며 세션/사용자 인증 없이
공유 베어러 토큰(WCMS_INTERNAL_TOKEN)으로 보호된다.

엔드포인트 목록:
    POST /internal/presence/
    POST /internal/telemetry/heartbeat/
    POST /internal/telemetry/command-result/
    POST /internal/telemetry/command-ack/
    GET  /internal/clients/<uuid:client_id>/pending-commands/
"""
from __future__ import annotations

from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from commands.models import Command
from fleet.models import Client, ClientDynamicInfo, NetworkEvent

from .auth import InternalTokenAuthentication, IsGateway
from .serializers import (
    CommandAckSerializer,
    CommandResultSerializer,
    HeartbeatSerializer,
    PendingCommandSerializer,
    PresenceSerializer,
)

# 모든 내부 뷰에서 공통으로 사용하는 인증/권한 클래스
_AUTH = [InternalTokenAuthentication]
_PERM = [IsGateway]


def _get_client_or_404(client_id) -> tuple[Client, Response | None]:
    """UUID 로 Client 를 조회한다. 미존재 시 (None, 404 Response) 를 반환한다."""
    try:
        return Client.objects.get(pk=client_id), None
    except Client.DoesNotExist:
        return None, Response(  # type: ignore[return-value]
            {"detail": "클라이언트를 찾을 수 없습니다."},
            status=status.HTTP_404_NOT_FOUND,
        )


class PresenceView(APIView):
    """PC 연결/해제 이벤트를 수신해 온라인 상태와 네트워크 이벤트를 갱신한다.

    POST /internal/presence/

    connect  : Client.is_online=True, last_seen 갱신.
               열린 NetworkEvent(online_at is null)가 있으면 닫는다.
    disconnect: Client.is_online=False.
               열린 NetworkEvent 가 없으면 새로 생성한다.
    """

    authentication_classes = _AUTH
    permission_classes = _PERM

    def post(self, request) -> Response:
        """프레즌스 이벤트를 처리한다."""
        ser = PresenceSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        client, err = _get_client_or_404(data["client_id"])
        if err:
            return err

        at = data["at"] or timezone.now()
        event: str = data["event"]

        if event == "connect":
            self._handle_connect(client, at)
        else:
            self._handle_disconnect(client, at)

        return Response(status=status.HTTP_204_NO_CONTENT)

    @staticmethod
    def _handle_connect(client: Client, at) -> None:
        """연결 이벤트: 온라인 상태 갱신 + 열린 NetworkEvent 닫기."""
        client.is_online = True
        client.last_seen = at
        client.save(update_fields=["is_online", "last_seen", "updated_at"])

        # 열린 NetworkEvent(online_at is null) 가 있으면 닫는다.
        open_event = (
            NetworkEvent.objects.filter(client=client, online_at__isnull=True)
            .order_by("-offline_at")
            .first()
        )
        if open_event:
            open_event.online_at = at
            delta = at - open_event.offline_at
            open_event.duration_sec = max(0, int(delta.total_seconds()))
            open_event.save(update_fields=["online_at", "duration_sec"])

    @staticmethod
    def _handle_disconnect(client: Client, at) -> None:
        """해제 이벤트: 오프라인 상태 갱신 + 열린 NetworkEvent 없으면 생성."""
        client.is_online = False
        client.last_seen = at
        client.save(update_fields=["is_online", "last_seen", "updated_at"])

        # 이미 열린 이벤트가 없을 때만 새로 생성한다.
        has_open = NetworkEvent.objects.filter(
            client=client, online_at__isnull=True
        ).exists()
        if not has_open:
            NetworkEvent.objects.create(
                client=client,
                offline_at=at,
                reason="disconnect",
            )


class HeartbeatView(APIView):
    """PC 하트비트 텔레메트리를 수신해 동적 정보를 갱신한다.

    POST /internal/telemetry/heartbeat/

    full=True : cpu_usage + ram_usage_percent + 제공된 선택 필드 전체 저장.
    full=False: cpu_usage + ram_usage_percent 만 저장(라이트 업데이트).
    ip_address 가 제공되면 Client.ip_address 도 갱신한다.
    """

    authentication_classes = _AUTH
    permission_classes = _PERM

    def post(self, request) -> Response:
        """하트비트 데이터를 처리한다."""
        ser = HeartbeatSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        client, err = _get_client_or_404(data["client_id"])
        if err:
            return err

        now = timezone.now()

        # Client 메타데이터 갱신
        client_update_fields = ["is_online", "last_seen", "updated_at"]
        client.is_online = True
        client.last_seen = now
        if data["ip_address"] is not None:
            client.ip_address = data["ip_address"]
            client_update_fields.append("ip_address")
        client.save(update_fields=client_update_fields)

        # ClientDynamicInfo 갱신
        dynamic_fields: dict = {
            "cpu_usage": data["cpu_usage"],
            "ram_usage_percent": data["ram_usage_percent"],
        }

        if data["full"]:
            # 선택 필드 중 제공된 값만 저장한다. None 이어도 명시적으로 null 저장.
            if data["ram_used"] is not None:
                dynamic_fields["ram_used"] = data["ram_used"]
            if data["disk_usage"] is not None:
                dynamic_fields["disk_usage"] = data["disk_usage"]
            if data["current_user"] is not None:
                dynamic_fields["current_user"] = data["current_user"]
            if data["uptime"] is not None:
                dynamic_fields["uptime"] = data["uptime"]
            if data["processes"] is not None:
                dynamic_fields["processes"] = data["processes"]

        # ClientDynamicInfo 는 라이트 업데이트 시 필수 필드(ram_used, uptime)에
        # 기본값이 없으므로 update_or_create 시 defaults 에는 제공된 필드만 넣는다.
        # 신규 생성(create) 시 누락 필드에는 ORM 기본값이 없어 0 으로 채운다.
        create_defaults = {
            "cpu_usage": dynamic_fields.get("cpu_usage", 0.0),
            "ram_usage_percent": dynamic_fields.get("ram_usage_percent", 0.0),
            "ram_used": dynamic_fields.get("ram_used", 0.0),
            "uptime": dynamic_fields.get("uptime", 0),
        }
        create_defaults.update(dynamic_fields)

        ClientDynamicInfo.objects.update_or_create(
            client=client,
            defaults=dynamic_fields,
            create_defaults=create_defaults,
        )

        return Response(status=status.HTTP_204_NO_CONTENT)


class CommandResultView(APIView):
    """명령 실행 결과를 수신해 Command 상태를 갱신한다.

    POST /internal/telemetry/command-result/

    status 값:
        completed -> Command.Status.COMPLETED
        error     -> Command.Status.ERROR
        timeout   -> Command.Status.TIMEOUT
    """

    authentication_classes = _AUTH
    permission_classes = _PERM

    _STATUS_MAP: dict[str, Command.Status] = {
        "completed": Command.Status.COMPLETED,
        "error": Command.Status.ERROR,
        "timeout": Command.Status.TIMEOUT,
    }

    def post(self, request) -> Response:
        """명령 결과를 처리한다."""
        ser = CommandResultSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        try:
            command = Command.objects.get(pk=data["command_id"])
        except Command.DoesNotExist:
            return Response(
                {"detail": "명령을 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND
            )

        new_status = self._STATUS_MAP[data["status"]]
        command.status = new_status
        command.completed_at = timezone.now()

        # output 은 result 필드에 저장한다.
        if data["output"] is not None:
            command.result = data["output"]
        if data["error_message"] is not None:
            command.error_message = data["error_message"]

        command.save(update_fields=["status", "completed_at", "result", "error_message"])

        return Response(status=status.HTTP_204_NO_CONTENT)


class CommandAckView(APIView):
    """게이트웨이가 명령을 클라이언트에 전달했음을 확인(ACK)한다.

    POST /internal/telemetry/command-ack/

    PENDING 상태의 명령만 SENT 로 전환한다. 이미 다른 상태이면 그대로 둔다.
    """

    authentication_classes = _AUTH
    permission_classes = _PERM

    def post(self, request) -> Response:
        """명령 ACK 를 처리한다."""
        ser = CommandAckSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        try:
            command = Command.objects.get(pk=data["command_id"])
        except Command.DoesNotExist:
            return Response(
                {"detail": "명령을 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND
            )

        if command.status == Command.Status.PENDING:
            command.status = Command.Status.SENT
            command.sent_at = timezone.now()
            command.save(update_fields=["status", "sent_at"])

        return Response(status=status.HTTP_204_NO_CONTENT)


class PendingCommandsView(APIView):
    """재연결한 클라이언트에게 전달 대기 중인 명령 목록을 반환한다.

    GET /internal/clients/<uuid:client_id>/pending-commands/

    조건: status=PENDING AND delivery_mode=QUEUE AND (expires_at is null OR expires_at > now)
    정렬: priority ASC, created_at ASC (우선순위 낮은 숫자 = 높은 우선순위)
    """

    authentication_classes = _AUTH
    permission_classes = _PERM

    def get(self, request, client_id) -> Response:
        """대기 중인 큐 명령 목록을 반환한다."""
        client, err = _get_client_or_404(client_id)
        if err:
            return err

        now = timezone.now()
        commands = Command.objects.filter(
            client=client,
            status=Command.Status.PENDING,
            delivery_mode=Command.DeliveryMode.QUEUE,
        ).filter(
            models_expires_at_null_or_future(now)
        ).order_by("priority", "created_at")

        ser = PendingCommandSerializer(commands, many=True)
        return Response(ser.data, status=status.HTTP_200_OK)


def models_expires_at_null_or_future(now):
    """expires_at is null OR expires_at > now Q 객체를 반환하는 헬퍼."""
    from django.db.models import Q
    return Q(expires_at__isnull=True) | Q(expires_at__gt=now)
