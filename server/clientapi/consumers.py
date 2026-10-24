from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.utils import timezone

from clientapi.protocol import bearer_token, clean_status, pc_group
from labs.live import broadcast_pc
from labs.models import PC

CLOSE_SUPERSEDED = 4409


@database_sync_to_async
def _pc_id_for_token(token: str) -> int | None:
    pc = PC.from_token(token)
    return pc.id if pc else None


@database_sync_to_async
def _mark_connected(pc_id: int, channel: str) -> None:
    PC.objects.filter(pk=pc_id).update(online=True, connection=channel, last_seen=timezone.now())


@database_sync_to_async
def _mark_disconnected(pc_id: int, channel: str) -> bool:
    return PC.objects.filter(pk=pc_id, connection=channel).update(online=False, connection="") > 0


@database_sync_to_async
def _save_hello(pc_id: int, version: str) -> None:
    PC.objects.filter(pk=pc_id).update(client_version=version[:20], last_seen=timezone.now())


@database_sync_to_async
def _save_status(pc_id: int, status: dict) -> None:
    PC.objects.filter(pk=pc_id).update(status=status, last_seen=timezone.now())


class ClientConsumer(AsyncJsonWebsocketConsumer):
    pc_id: int | None = None

    async def connect(self) -> None:
        token = bearer_token(self.scope)
        pc_id = await _pc_id_for_token(token) if token else None
        if pc_id is None:
            await self.close()
            return
        self.pc_id = pc_id
        group = pc_group(pc_id)
        await self.channel_layer.group_send(group, {"type": "pc.superseded"})
        await self.channel_layer.group_add(group, self.channel_name)
        await _mark_connected(pc_id, self.channel_name)
        await self.accept()
        await broadcast_pc(pc_id)

    async def disconnect(self, code: int) -> None:
        if self.pc_id is None:
            return
        await self.channel_layer.group_discard(pc_group(self.pc_id), self.channel_name)
        if await _mark_disconnected(self.pc_id, self.channel_name):
            await broadcast_pc(self.pc_id)

    async def receive(self, text_data=None, bytes_data=None, **kwargs) -> None:
        try:
            if text_data is None:
                raise ValueError("non-text frame")
            content = await self.decode_json(text_data)
        except ValueError:
            await self.send_json({"type": "error", "error": "bad_json"})
            return
        await self.receive_json(content)

    async def receive_json(self, content, **kwargs) -> None:
        kind = content.get("type") if isinstance(content, dict) else None
        if kind == "status":
            await _save_status(self.pc_id, clean_status(content))
            await broadcast_pc(self.pc_id)
        elif kind == "hello":
            version = content.get("version")
            if isinstance(version, str):
                await _save_hello(self.pc_id, version)
        elif kind == "ping":
            await self.send_json({"type": "pong"})
        else:
            await self.send_json({"type": "error", "error": "unknown_type"})

    async def pc_superseded(self, event: dict) -> None:
        await self.close(code=CLOSE_SUPERSEDED)
