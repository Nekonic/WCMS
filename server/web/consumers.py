from channels.generic.websocket import AsyncJsonWebsocketConsumer

from accounts.permissions import is_admin
from labs.live import LIVE_GROUP


class LiveConsumer(AsyncJsonWebsocketConsumer):
    admin = False

    async def connect(self) -> None:
        self.admin = is_admin(self.scope.get("user"))
        await self.channel_layer.group_add(LIVE_GROUP, self.channel_name)
        await self.accept()

    async def disconnect(self, code: int) -> None:
        await self.channel_layer.group_discard(LIVE_GROUP, self.channel_name)

    async def pc_update(self, event: dict) -> None:
        await self.send_json({"type": "pc", "pc": event["admin"] if self.admin else event["public"]})
