import logging
import re

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth import get_user_model

from live.snapshots import pc_snapshot, public_room_snapshot, room_snapshot
from wcms.api import is_admin
from wcms.groups import pc_watch_group, room_group, room_public_group, user_group

logger = logging.getLogger(__name__)
# 발행 쪽 키(f"room:{id}")와 문자열이 같은 정규형만 받는다: ASCII 숫자, 앞자리 0 없음, 끝 줄바꿈 없음
TOPIC = re.compile(r"\A(room|pc):(0|[1-9][0-9]{0,9})(:public)?\Z")
CLOSE_SESSION_ENDED = 4401


@database_sync_to_async
def _still_admin(user_id: int) -> bool:
    return get_user_model().objects.filter(pk=user_id, is_active=True, is_staff=True).exists()


@database_sync_to_async
def _snapshot(kind: str, ident: int, public: bool):
    if kind == "pc":
        return "pc", pc_snapshot(ident)
    if public:
        return "seats", public_room_snapshot(ident)
    return "pcs", room_snapshot(ident)


def _group(kind: str, ident: int, public: bool) -> str:
    if kind == "pc":
        return pc_watch_group(ident)
    return room_public_group(ident) if public else room_group(ident)


class LiveConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self) -> None:
        self.user = self.scope.get("user")
        self.admin = is_admin(self.user)
        self.topics: dict[str, str] = {}
        await self.accept()
        if self.admin:
            await self.channel_layer.group_add(user_group(self.user.pk), self.channel_name)

    async def disconnect(self, code: int) -> None:
        for group in self.topics.values():
            await self.channel_layer.group_discard(group, self.channel_name)
        if self.admin:
            await self.channel_layer.group_discard(user_group(self.user.pk), self.channel_name)

    async def receive(self, text_data=None, bytes_data=None) -> None:
        try:
            message = await self.decode_json(text_data) if text_data is not None else None
        except (ValueError, RecursionError):
            message = None
        if not isinstance(message, dict):
            await self.send_json({"type": "error", "error": "bad_json"})
            return
        try:
            await self.handle(message)
        except Exception:
            # 예외가 디스패치 루프를 죽이면 disconnect()가 호출되지 않아 그룹 구독이 남는다
            logger.exception("live websocket handler failed")
            await self.close(code=1011)

    async def handle(self, message: dict) -> None:
        kind = message.get("type")
        if kind == "subscribe":
            await self.subscribe(message.get("topic"))
        elif kind == "unsubscribe":
            await self.unsubscribe(message.get("topic"))
        elif kind == "ping":
            await self.refresh_groups()
            await self.send_json({"type": "pong"})
        else:
            await self.send_json({"type": "error", "error": "unknown_type"})

    async def subscribe(self, topic) -> None:
        match = TOPIC.match(topic) if isinstance(topic, str) else None
        if match is None or (match.group(1) == "pc" and match.group(3)):
            await self.send_json({"type": "error", "error": "bad_topic"})
            return
        kind, ident, public = match.group(1), int(match.group(2)), bool(match.group(3))
        if not public and not (self.admin and await _still_admin(self.user.pk)):
            await self.send_json({"type": "error", "error": "forbidden_topic", "topic": topic})
            return
        # 스냅샷과 이후 변경 사이에 빈틈이 없도록 그룹에 먼저 들어간다.
        # 스냅샷을 만드는 동안 도착한 이벤트는 스냅샷 뒤에 전달된다(이벤트는 전체 상태를 담는다).
        new = topic not in self.topics
        if new:
            group = _group(kind, ident, public)
            await self.channel_layer.group_add(group, self.channel_name)
            self.topics[topic] = group
        key, snapshot = await _snapshot(kind, ident, public)
        if snapshot is None:
            group = self.topics.pop(topic, None)
            if group is not None:
                await self.channel_layer.group_discard(group, self.channel_name)
            await self.send_json({"type": "error", "error": "not_found", "topic": topic})
            return
        await self.send_json({"type": "snapshot", "topic": topic, key: snapshot})

    async def refresh_groups(self) -> None:
        """그룹 구독은 채널 레이어에서 만료된다(24시간, Redis 재시작). ping마다 다시 넣어 연결이 조용히 끊기지 않게 한다."""
        for group in self.topics.values():
            await self.channel_layer.group_add(group, self.channel_name)
        if self.admin:
            await self.channel_layer.group_add(user_group(self.user.pk), self.channel_name)

    async def unsubscribe(self, topic) -> None:
        group = self.topics.pop(topic, None) if isinstance(topic, str) else None
        if group is not None:
            await self.channel_layer.group_discard(group, self.channel_name)

    async def live_pc(self, event: dict) -> None:
        if event["topic"] in self.topics:
            await self.send_json({"type": "pc", "topic": event["topic"], "pc": event["pc"]})

    async def live_seat(self, event: dict) -> None:
        if event["topic"] in self.topics:
            await self.send_json({"type": "seat", "topic": event["topic"], "seat": event["seat"]})

    async def live_room_changed(self, event: dict) -> None:
        if event["topic"] in self.topics:
            await self.send_json({"type": "room_changed", "topic": event["topic"]})

    async def session_end(self, event: dict) -> None:
        await self.close(code=CLOSE_SESSION_ENDED)
