from asgiref.sync import async_to_sync, sync_to_async
from channels.layers import get_channel_layer

from agent import state
from labs.models import PC
from live.snapshots import live_pc, public_seat
from wcms.groups import pc_watch_group, room_group, room_public_group


def _load(pc_id: int) -> tuple[PC | None, dict]:
    pc = PC.objects.select_related("room").filter(pk=pc_id).first()
    return pc, state.get_state(pc_id)


async def publish_pc(pc_id: int, *, online_changed: bool) -> None:
    pc, st = await sync_to_async(_load)(pc_id)
    if pc is None:
        return
    layer = get_channel_layer()
    payload = await sync_to_async(live_pc)(pc, st)
    await layer.group_send(pc_watch_group(pc.id), {"type": "live.pc", "topic": f"pc:{pc.id}", "pc": payload})
    if not pc.seated:
        return
    await layer.group_send(room_group(pc.room_id), {"type": "live.pc", "topic": f"room:{pc.room_id}", "pc": payload})
    if online_changed:
        seat = await sync_to_async(public_seat)(pc, st)
        await layer.group_send(
            room_public_group(pc.room_id), {"type": "live.seat", "topic": f"room:{pc.room_id}:public", "seat": seat}
        )


def room_changed(room_id: int) -> None:
    send = async_to_sync(get_channel_layer().group_send)
    send(room_group(room_id), {"type": "live.room_changed", "topic": f"room:{room_id}"})
    send(room_public_group(room_id), {"type": "live.room_changed", "topic": f"room:{room_id}:public"})
