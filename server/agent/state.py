import enum
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


class Refresh(enum.Enum):
    IGNORED = "ignored"  # 다른 연결이 이 PC를 쥐고 있다 (교체되었거나 이미 끊김)
    SAVED = "saved"  # 이 연결의 상태를 갱신했다. 온라인 여부는 그대로
    REVIVED = "revived"  # 값이 사라져 있어 (TTL, 캐시 축출, Redis 재시작) 이 연결로 다시 온라인이 되었다


def _connected(channel: str, status: dict) -> dict:
    return {"boot": BOOT_ID, "online": True, "connection": channel, "status": status, "since": time.time()}


def mark_connected(pc_id: int, channel: str) -> None:
    cache.set(_key(pc_id), _connected(channel, {}), TTL)


def mark_disconnected(pc_id: int, channel: str) -> bool:
    raw = _current(cache.get(_key(pc_id)))
    if raw is None or raw.get("connection") != channel:
        return False
    cache.set(_key(pc_id), {**raw, "online": False, "connection": "", "status": {}}, TTL)
    return True


def _refresh(pc_id: int, channel: str, status: dict | None) -> Refresh:
    """살아 있는 연결이 보낸 메시지로 TTL을 갱신한다. status가 있으면 함께 저장한다."""
    raw = _current(cache.get(_key(pc_id)))
    if raw is None:
        cache.set(_key(pc_id), _connected(channel, status or {}), TTL)
        return Refresh.REVIVED
    if raw.get("connection") != channel:
        return Refresh.IGNORED
    if status is not None:
        raw = {**raw, "status": status, "updated": time.time()}
    cache.set(_key(pc_id), raw, TTL)
    return Refresh.SAVED


def save_status(pc_id: int, channel: str, status: dict) -> Refresh:
    return _refresh(pc_id, channel, status)


def touch(pc_id: int, channel: str) -> Refresh:
    return _refresh(pc_id, channel, None)
