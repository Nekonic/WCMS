import json
from pathlib import Path

import pytest
from django.core.cache import cache

from agent import state
from agent.protocol import bearer_token, clean_status

EXAMPLES = Path(__file__).resolve().parents[2] / "protocol" / "examples"


def example(name: str) -> dict:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def test_status_example_survives_cleaning_unchanged():
    message = example("status.json")
    expected = {k: v for k, v in message.items() if k != "type"}
    assert clean_status(message) == expected


@pytest.mark.parametrize("value", [float("inf"), float("nan"), -1, True, "12", 101])
def test_bad_cpu_dropped(value):
    assert "cpu" not in clean_status({"cpu": value})


def test_strings_only_and_truncated():
    cleaned = clean_status(
        {"user": "u" * 100, "session": "weird", "foreground": {"process": {"x": 1}, "title": "t" * 500}}
    )
    assert len(cleaned["user"]) == 64
    assert cleaned["session"] == "none"
    assert cleaned["foreground"] == {"process": "", "title": "t" * 256}


def test_non_string_user_dropped():
    assert "user" not in clean_status({"user": 5})


def test_bearer_token():
    assert bearer_token({"headers": [(b"authorization", b"Bearer abc")]}) == "abc"
    assert bearer_token({"headers": [(b"authorization", b"Basic abc")]}) is None
    assert bearer_token({"headers": []}) is None


def test_state_lifecycle():
    assert state.get_state(1) == {"online": False, "status": {}}
    state.mark_connected(1, "chan-a")
    assert state.get_state(1)["online"] is True
    assert state.save_status(1, "chan-b", {"cpu": 1}) is state.Refresh.IGNORED
    assert state.save_status(1, "chan-a", {"cpu": 1}) is state.Refresh.SAVED
    assert state.get_state(1)["status"] == {"cpu": 1}
    assert state.mark_disconnected(1, "chan-b") is False
    assert state.mark_disconnected(1, "chan-a") is True
    assert state.get_state(1) == {"online": False, "status": {}}


def test_state_from_previous_boot_is_offline(monkeypatch):
    state.mark_connected(2, "chan")
    monkeypatch.setattr(state, "BOOT_ID", "another-boot")
    assert state.get_state(2)["online"] is False


def test_get_states():
    state.mark_connected(3, "c")
    states = state.get_states([3, 4])
    assert states[3]["online"] is True and states[4]["online"] is False


@pytest.mark.parametrize("key", ["cpu", "mem_used", "mem_total", "disk_used", "disk_total"])
def test_huge_int_dropped_without_raising(key):
    assert key not in clean_status(json.loads('{"%s": 1%s}' % (key, "0" * 400)))
    assert key not in clean_status({key: 10**400})


def test_save_status_revives_missing_or_stale_key(monkeypatch):
    # 캐시에서 밀려났거나 Redis가 재시작되었거나 다른 부팅의 값이면 이 연결로 다시 온라인이 된다
    assert state.save_status(5, "chan", {"cpu": 1}) is state.Refresh.REVIVED
    assert state.get_state(5) == {"online": True, "status": {"cpu": 1}}
    monkeypatch.setattr(state, "BOOT_ID", "another-boot")
    assert state.save_status(5, "chan", {"cpu": 2}) is state.Refresh.REVIVED
    assert state.get_state(5) == {"online": True, "status": {"cpu": 2}}
    assert state.mark_disconnected(5, "chan") is True


def test_other_connection_is_never_overwritten():
    state.mark_connected(6, "new")
    assert state.save_status(6, "old", {"cpu": 1}) is state.Refresh.IGNORED
    assert state.touch(6, "old") is state.Refresh.IGNORED
    assert state.get_state(6) == {"online": True, "status": {}}
    assert state.mark_disconnected(6, "new") is True
    assert state.touch(6, "old") is state.Refresh.IGNORED
    assert state.get_state(6)["online"] is False


def test_touch_keeps_status_and_refreshes_ttl(monkeypatch):
    state.mark_connected(7, "chan")
    state.save_status(7, "chan", {"cpu": 1})
    timeouts = []
    original = cache.set

    def recording_set(key, value, timeout):
        timeouts.append(timeout)
        original(key, value, timeout)

    monkeypatch.setattr(cache, "set", recording_set)
    assert state.touch(7, "chan") is state.Refresh.SAVED
    assert timeouts == [state.TTL]
    assert state.get_state(7) == {"online": True, "status": {"cpu": 1}}


def test_touch_revives_missing_key():
    assert state.touch(8, "chan") is state.Refresh.REVIVED
    assert state.get_state(8) == {"online": True, "status": {}}
