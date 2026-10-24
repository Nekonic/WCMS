from agent import state
from labs.models import PC, Room
from live.serializers import LivePCSerializer, PublicSeatSerializer

NUMBERS = ("cpu", "mem_used", "mem_total", "disk_used", "disk_total")


def live_pc(pc: PC, st: dict) -> dict:
    status = st.get("status", {}) if st.get("online") else {}
    data = {
        "id": pc.id,
        "hostname": pc.hostname,
        "label": pc.label,
        "room": pc.room_id,
        "row": pc.row,
        "col": pc.col,
        "version": pc.client_version,
        "online": bool(st.get("online")),
        "session": status.get("session", "none"),
        "user": status.get("user", ""),
        "foreground": status.get("foreground"),
        **{key: status.get(key) for key in NUMBERS},
    }
    return LivePCSerializer(data).data


def public_seat(pc: PC, st: dict) -> dict:
    return PublicSeatSerializer({"row": pc.row, "col": pc.col, "label": pc.label, "online": bool(st.get("online"))}).data


def _seated_in(room_id: int) -> list[PC]:
    return list(
        PC.objects.select_related("room")
        .filter(room_id=room_id, row__isnull=False, col__isnull=False)
        .order_by("row", "col")
    )


def room_snapshot(room_id: int) -> list[dict] | None:
    if not Room.objects.filter(pk=room_id).exists():
        return None
    pcs = _seated_in(room_id)
    states = state.get_states([pc.id for pc in pcs])
    return [live_pc(pc, states[pc.id]) for pc in pcs]


def public_room_snapshot(room_id: int) -> list[dict] | None:
    if not Room.objects.filter(pk=room_id).exists():
        return None
    pcs = _seated_in(room_id)
    states = state.get_states([pc.id for pc in pcs])
    return [public_seat(pc, states[pc.id]) for pc in pcs]


def pc_snapshot(pc_id: int) -> dict | None:
    pc = PC.objects.select_related("room").filter(pk=pc_id).first()
    if pc is None:
        return None
    return live_pc(pc, state.get_state(pc.id))
