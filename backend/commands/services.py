"""명령 발행 계층.

전달 정책 기본값을 타입별로 부여한다(설계 4.4): 시간 민감 명령은 drop_if_offline,
그 외는 queue + TTL.

발행 후 클라이언트 온라인 여부에 따라 즉시 게이트웨이 push 를 시도한다(설계 §3/§4.4).
- 온라인: gateway_push 호출 -> 커맨드는 PENDING 유지(게이트웨이가 수신 확인 시 SENT 로
  전환됨 — /internal/telemetry/command-ack/ 경로).
- 오프라인 + DROP_IF_OFFLINE: 게이트웨이 push 없이 EXPIRED 로 즉시 폐기.
- 오프라인 + QUEUE: PENDING 유지(게이트웨이 재연결 시 드레인).
"""
import logging
from datetime import timedelta
from typing import Optional

import requests
from django.conf import settings
from django.utils import timezone

from .models import Command

logger = logging.getLogger(__name__)

# 시간 민감(늦게 도착하면 안 되는) 명령.
_DROP_TYPES = {"shutdown", "restart", "reboot", "message", "kill_process", "execute"}
QUEUE_TTL = timedelta(hours=24)

# 게이트웨이 HTTP 요청 타임아웃(초).
_GATEWAY_TIMEOUT = 3.0


def default_delivery_mode(command_type: str) -> str:
    """명령 타입에 따른 기본 전달 모드를 반환한다."""
    if command_type in _DROP_TYPES:
        return Command.DeliveryMode.DROP_IF_OFFLINE
    return Command.DeliveryMode.QUEUE


def gateway_push(command: Command) -> bool:
    """명령을 Rust 게이트웨이로 즉시 push 한다.

    POST {WCMS_GATEWAY_URL}/internal/push/{client_id}
    Authorization: Bearer <WCMS_INTERNAL_TOKEN>

    게이트웨이 반환값:
    - 200 {"delivered": true}  -> 클라이언트 연결 중, 전달 성공 -> True 반환.
    - 404 {"delivered": false} -> 클라이언트 미연결 -> False 반환.

    네트워크 장애/타임아웃 등 RequestException 은 경고 로그만 남기고 False 반환
    (게이트웨이 다운이 API 호출 실패로 이어져서는 안 된다).
    """
    url = f"{settings.WCMS_GATEWAY_URL}/internal/push/{command.client_id}"
    headers = {"Authorization": f"Bearer {settings.WCMS_INTERNAL_TOKEN}"}
    payload = {
        "id": str(command.id),
        "command_type": command.command_type,
        "parameters": command.parameters,
        "timeout_seconds": command.timeout_seconds,
        "priority": command.priority,
        "delivery_mode": command.delivery_mode,
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=_GATEWAY_TIMEOUT)
        if resp.status_code == 200:
            data = resp.json()
            return bool(data.get("delivered", False))
        return False
    except requests.RequestException as exc:
        logger.warning(
            "게이트웨이 push 실패 (command_id=%s client_id=%s): %s",
            command.id, command.client_id, exc,
        )
        return False


def issue_command(
    *,
    client,
    command_type: str,
    issuer=None,
    parameters: Optional[dict] = None,
    priority: int = 5,
    timeout_seconds: int = 300,
    delivery_mode: Optional[str] = None,
) -> Command:
    """명령을 발행하고 전달 정책을 즉시 적용한다.

    1. Command(status=PENDING) 행을 생성한다.
    2. 클라이언트 온라인 여부에 따라 전달 정책을 적용한다:
       - 온라인                   : gateway_push 호출. 상태는 PENDING 유지.
       - 오프라인 + DROP_IF_OFFLINE: 즉시 EXPIRED 로 폐기(게이트웨이 push 없음).
       - 오프라인 + QUEUE          : PENDING 유지(재연결 시 게이트웨이가 드레인).
    3. 생성된 Command 를 반환한다(호출자 시그니처 불변).
    """
    mode = delivery_mode or default_delivery_mode(command_type)
    expires_at = (timezone.now() + QUEUE_TTL
                  if mode == Command.DeliveryMode.QUEUE else None)

    cmd = Command.objects.create(
        client=client,
        issuer=issuer,
        command_type=command_type,
        parameters=parameters or {},
        priority=priority,
        timeout_seconds=timeout_seconds,
        delivery_mode=mode,
        expires_at=expires_at,
        status=Command.Status.PENDING,
    )

    if client.is_online:
        # 온라인: 게이트웨이로 즉시 push. 실패해도 예외를 올리지 않는다.
        gateway_push(cmd)
    elif mode == Command.DeliveryMode.DROP_IF_OFFLINE:
        # 오프라인 + 시간 민감 명령: 폐기.
        cmd.status = Command.Status.EXPIRED
        cmd.save(update_fields=["status"])

    return cmd
