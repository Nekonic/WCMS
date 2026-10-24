import time
import uuid

from django.core.cache import cache

BOOT_ID = uuid.uuid4().hex
TTL = 24 * 3600
OFFLINE = {"online": False, "status": {}}


def _key(pc_id: int) -> str:
    return f"pcstate:{pc_id}"


def _current(raw: dict | None) -> dict | None:
    if not raw or raw.get("boot") != BOOT_ID:
        return None
    return raw


def _public(raw: dict | None) -> dict:
    raw = _current(raw)
    if raw is None or not raw.get("online"):
        return dict(OFFLINE)
    return {"online": True, "status": raw.get("status", {})}


def get_state(pc_id: int) -> dict:
    return _public(cache.get(_key(pc_id)))


def get_states(pc_ids: list[int]) -> dict[int, dict]:
    found = cache.get_many([_key(pc_id) for pc_id in pc_ids])
    return {pc_id: _public(found.get(_key(pc_id))) for pc_id in pc_ids}


def mark_connected(pc_id: int, channel: str) -> None:
    cache.set(
        _key(pc_id),
        {"boot": BOOT_ID, "online": True, "connection": channel, "status": {}, "since": time.time()},
        TTL,
    )


def mark_disconnected(pc_id: int, channel: str) -> bool:
    raw = _current(cache.get(_key(pc_id)))
    if raw is None or raw.get("connection") != channel:
        return False
    cache.set(_key(pc_id), {**raw, "online": False, "connection": "", "status": {}}, TTL)
    return True


def save_status(pc_id: int, channel: str, status: dict) -> bool:
    raw = _current(cache.get(_key(pc_id)))
    if raw is None or raw.get("connection") != channel:
        return False
    cache.set(_key(pc_id), {**raw, "status": status, "updated": time.time()}, TTL)
    return True
