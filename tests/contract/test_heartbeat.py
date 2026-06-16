"""계약: POST /api/client/heartbeat (상태 업데이트)."""


def test_full_heartbeat_by_machine_id(http, registered_pc):
    _, machine_id = registered_pc
    resp = http.post("/api/client/heartbeat", json={
        "machine_id": machine_id,
        "full_update": True,
        "cpu_usage": 12.5,
        "ram_usage_percent": 40.0,
        "ram_used": 6.0,
        "disk_usage": 55.0,
        "current_user": "tester",
        "uptime": 3600,
        "processes": [],
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert body["full_update"] is True


def test_light_heartbeat_sets_full_update_false(http, registered_pc):
    _, machine_id = registered_pc
    resp = http.post("/api/client/heartbeat", json={
        "machine_id": machine_id,
        "full_update": False,
        "cpu_usage": 5.0,
        "ram_usage_percent": 30.0,
    })
    assert resp.status_code == 200
    assert resp.json()["full_update"] is False


def test_heartbeat_by_pc_id(http, registered_pc):
    pc_id, _ = registered_pc
    resp = http.post("/api/client/heartbeat", json={
        "pc_id": pc_id, "cpu_usage": 1.0, "ram_usage_percent": 1.0})
    assert resp.status_code == 200


def test_heartbeat_accepts_system_info_wrapper(http, registered_pc):
    _, machine_id = registered_pc
    resp = http.post("/api/client/heartbeat", json={
        "machine_id": machine_id,
        "system_info": {"cpu_usage": 9.0, "ram_usage_percent": 22.0},
    })
    assert resp.status_code == 200


def test_heartbeat_empty_body_returns_400(http):
    assert http.post("/api/client/heartbeat", json={}).status_code == 400


def test_heartbeat_missing_identifier_returns_400(http):
    resp = http.post("/api/client/heartbeat", json={"cpu_usage": 1.0})
    assert resp.status_code == 400


def test_heartbeat_unknown_machine_returns_404(http):
    resp = http.post("/api/client/heartbeat", json={
        "machine_id": "NOPE-404", "cpu_usage": 1.0})
    assert resp.status_code == 404


def test_heartbeat_reports_ip_change(http, registered_pc):
    _, machine_id = registered_pc
    http.post("/api/client/heartbeat", json={
        "machine_id": machine_id, "ip_address": "10.0.0.5",
        "cpu_usage": 1.0, "ram_usage_percent": 1.0})
    resp = http.post("/api/client/heartbeat", json={
        "machine_id": machine_id, "ip_address": "10.0.0.9",
        "cpu_usage": 1.0, "ram_usage_percent": 1.0})
    assert resp.status_code == 200
    assert resp.json()["ip_changed"] is True
