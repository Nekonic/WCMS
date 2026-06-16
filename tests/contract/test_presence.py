"""계약: 온라인/오프라인 신호 (offline, shutdown) 및 5초 재연결 무시 가드."""


def _is_online(admin, pc_id):
    body = admin.get(f"/api/pc/{pc_id}").json()
    pc = body.get("data", body)
    return bool(pc["is_online"])


def test_offline_marks_pc_offline(http, registered_pc, admin):
    pc_id, machine_id = registered_pc
    http.get(f"/api/client/commands?machine_id={machine_id}&timeout=0")  # 온라인 확립
    resp = http.post("/api/client/offline", json={"machine_id": machine_id})
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
    assert _is_online(admin, pc_id) is False


def test_offline_missing_machine_id_returns_400(http):
    assert http.post("/api/client/offline", json={}).status_code == 400


def test_offline_unknown_machine_returns_404(http):
    assert http.post("/api/client/offline", json={"machine_id": "NOPE"}).status_code == 404


def test_shutdown_signal_marks_offline(http, registered_pc, admin):
    pc_id, machine_id = registered_pc
    http.get(f"/api/client/commands?machine_id={machine_id}&timeout=0")
    resp = http.post("/api/client/shutdown", json={"machine_id": machine_id})
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
    assert _is_online(admin, pc_id) is False


def test_shutdown_missing_machine_id_returns_400(http):
    assert http.post("/api/client/shutdown", json={}).status_code == 400


def test_shutdown_then_immediate_poll_does_not_flip_online(http, registered_pc, admin):
    """5초 재연결 무시 가드: shutdown 직후 폴링이 PC 를 online 으로 되돌리면 안 된다."""
    pc_id, machine_id = registered_pc
    http.get(f"/api/client/commands?machine_id={machine_id}&timeout=0")  # 온라인
    assert http.post("/api/client/shutdown", json={"machine_id": machine_id}).status_code == 200

    poll = http.get(f"/api/client/commands?machine_id={machine_id}&timeout=0")
    assert poll.status_code == 200
    assert poll.json()["data"]["has_command"] is False
    assert _is_online(admin, pc_id) is False  # 가드 작동: 여전히 offline
