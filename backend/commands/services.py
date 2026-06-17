"""명령 발행 계층.

전달 정책 기본값을 타입별로 부여한다(설계 4.4): 시간 민감 명령은 drop_if_offline,
그 외는 queue + TTL. 발행은 Command 행(status=pending) 생성까지만 담당하며, 실제
게이트웨이 push 는 Phase 2(Rust)에서 처리한다.
"""
from datetime import timedelta

from django.utils import timezone

from .models import Command

# 시간 민감(늦게 도착하면 안 되는) 명령.
_DROP_TYPES = {"shutdown", "restart", "reboot", "message", "kill_process", "execute"}
QUEUE_TTL = timedelta(hours=24)


def default_delivery_mode(command_type):
    if command_type in _DROP_TYPES:
        return Command.DeliveryMode.DROP_IF_OFFLINE
    return Command.DeliveryMode.QUEUE


def issue_command(*, client, command_type, issuer=None, parameters=None,
                  priority=5, timeout_seconds=300, delivery_mode=None):
    mode = delivery_mode or default_delivery_mode(command_type)
    expires_at = (timezone.now() + QUEUE_TTL
                  if mode == Command.DeliveryMode.QUEUE else None)
    return Command.objects.create(
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
