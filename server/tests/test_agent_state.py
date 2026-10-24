import json
from pathlib import Path

import pytest

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
    assert state.save_status(1, "chan-b", {"cpu": 1}) is False
    assert state.save_status(1, "chan-a", {"cpu": 1}) is True
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
