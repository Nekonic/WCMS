import asyncio
import time
from collections import defaultdict

from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from agent import protocol, state
from labs.models import PC
from live.publish import publish_pc
from wcms.groups import pc_group
from wcms.net import is_internal_scope

# ASGI 서버는 프로세스 하나로 고정이므로 PC별 상태 변경은 이 잠금으로 순서를 지킨다.
_locks: defaultdict[int, asyncio.Lock] = defaultdict(asyncio.Lock)


@database_sync_to_async
def _pc_id_for_token(token: str) -> int | None:
    pc = PC.from_token(token)
    return pc.id if pc else None


@database_sync_to_async
def _save_version(pc_id: int, version: str) -> None:
    PC.objects.filter(pk=pc_id).update(client_version=version[:20])


def _error(code: str) -> dict:
    return {"type": "error", "error": code}


class AgentConsumer(AsyncJsonWebsocketConsumer):
    pc_id: int | None = None
    hello_done = False
    last_status: float | None = None

    async def connect(self) -> None:
        token = protocol.bearer_token(self.scope)
        pc_id = await _pc_id_for_token(token) if token and is_internal_scope(self.scope) else None
        if pc_id is None:
            await self.close()
            return
        self.pc_id = pc_id
        group = pc_group(pc_id)
        await self.channel_layer.group_send(group, {"type": "pc.superseded"})
        await self.channel_layer.group_add(group, self.channel_name)
        async with _locks[pc_id]:
            await sync_to_async(state.mark_connected)(pc_id, self.channel_name)
        await self.accept()
        await publish_pc(pc_id, online_changed=True)

    async def disconnect(self, code: int) -> None:
        if self.pc_id is None:
            return
        await self.channel_layer.group_discard(pc_group(self.pc_id), self.channel_name)
        async with _locks[self.pc_id]:
            changed = await sync_to_async(state.mark_disconnected)(self.pc_id, self.channel_name)
        if changed:
            await publish_pc(self.pc_id, online_changed=True)

    async def receive(self, text_data=None, bytes_data=None) -> None:
        if text_data is None:
            await self.send_json(_error("binary_not_supported"))
            return
        try:
            message = await self.decode_json(text_data)
        except (ValueError, RecursionError):
            await self.send_json(_error("bad_json"))
            return
        if not isinstance(message, dict):
            await self.send_json(_error("bad_json"))
            return
        await self.handle(message)

    async def handle(self, message: dict) -> None:
        kind = message.get("type")
        if not self.hello_done:
            if kind != "hello":
                await self.close(code=protocol.CLOSE_HELLO_REQUIRED)
                return
            if message.get("proto") != protocol.PROTO_VERSION:
                await self.close(code=protocol.CLOSE_UNSUPPORTED_PROTO)
                return
            self.hello_done = True
            version = message.get("version")
            if isinstance(version, str):
                await _save_version(self.pc_id, version)
            return
        if kind == "status":
            now = time.monotonic()
            if self.last_status is not None and now - self.last_status < protocol.STATUS_MIN_INTERVAL:
                return
            self.last_status = now
            async with _locks[self.pc_id]:
                saved = await sync_to_async(state.save_status)(
                    self.pc_id, self.channel_name, protocol.clean_status(message)
                )
            if saved:
                await publish_pc(self.pc_id, online_changed=False)
        elif kind == "ping":
            await self.send_json({"type": "pong"})
        else:
            await self.send_json(_error("unknown_type"))

    async def pc_superseded(self, event: dict) -> None:
        await self.close(code=protocol.CLOSE_SUPERSEDED)

    async def pc_revoked(self, event: dict) -> None:
        await self.close(code=protocol.CLOSE_REVOKED)
