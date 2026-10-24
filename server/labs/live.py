from channels.db import database_sync_to_async
from channels.layers import get_channel_layer

from labs.models import PC

LIVE_GROUP = "live"

STATE_LABELS = {
    "offline": "오프라인",
    "in_use": "사용 중",
    "available": "비어 있음",
    "active": "사용 중",
    "locked": "잠금",
    "no_user": "로그인 없음",
}


def _state(pc: PC, admin: bool) -> str:
    if not pc.is_online:
        return "offline"
    session = pc.status.get("session", "none")
    if admin:
        return {"active": "active", "locked": "locked"}.get(session, "no_user")
    return "in_use" if session == "active" else "available"


def pc_payload(pc: PC, *, admin: bool) -> dict:
    state = _state(pc, admin)
    data = {
        "id": pc.id,
        "label": pc.label,
        "room_id": pc.room_id,
        "row": pc.row,
        "col": pc.col,
        "state": state,
        "state_label": STATE_LABELS[state],
    }
    if admin:
        status = pc.status
        data.update(
            {
                "hostname": pc.hostname,
                "version": pc.client_version,
                "user": status.get("user", ""),
                "session": status.get("session", "none"),
                "foreground": status.get("foreground"),
                "cpu": status.get("cpu"),
                "mem_used": status.get("mem_used"),
                "mem_total": status.get("mem_total"),
                "disk_used": status.get("disk_used"),
                "disk_total": status.get("disk_total"),
            }
        )
    return data


@database_sync_to_async
def _load(pc_id: int) -> PC:
    return PC.objects.select_related("room").get(pk=pc_id)


async def broadcast_pc(pc_id: int) -> None:
    pc = await _load(pc_id)
    await get_channel_layer().group_send(
        LIVE_GROUP,
        {
            "type": "pc.update",
            "public": pc_payload(pc, admin=False),
            "admin": pc_payload(pc, admin=True),
        },
    )
