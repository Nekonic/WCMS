"""계약: GET /api/client/commands (및 레거시 별칭 /command) 명령 long-poll.

핵심 와이어 형식과 엣지케이스를 고정한다. timeout=0 으로 폴링하면 한 번 확인 후
즉시 반환하므로 결정론적으로 검증 가능하다.
"""


def test_poll_no_command_returns_has_command_false(http, registered_pc):
    _, machine_id = registered_pc
    resp = http.get(f"/api/client/commands?machine_id={machine_id}&timeout=0")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["has_command"] is False
    assert data["command"] is None


def test_poll_returns_pending_command_with_wire_shape(http, registered_pc, issue_command):
    pc_id, machine_id = registered_pc
    issued = issue_command(pc_id, "shutdown", data={"delay": 0})
    assert issued.status_code == 200

    resp = http.get(f"/api/client/commands?machine_id={machine_id}&timeout=0")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["has_command"] is True
    cmd = data["command"]
    assert cmd["type"] == "shutdown"
    assert cmd["parameters"] == {"delay": 0}
    # 클라이언트가 의존하는 필드들이 존재해야 한다.
    for key in ("id", "type", "parameters", "timeout", "priority", "created_at"):
        assert key in cmd


def test_legacy_command_alias_behaves_same(http, registered_pc, issue_command):
    pc_id, machine_id = registered_pc
    assert issue_command(pc_id, "shutdown", data={"delay": 0}).status_code == 200

    resp = http.get(f"/api/client/command?machine_id={machine_id}&timeout=0")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["has_command"] is True
    assert data["command"]["type"] == "shutdown"


def test_poll_missing_machine_id_returns_400(http):
    resp = http.get("/api/client/commands?timeout=0")
    assert resp.status_code == 400


def test_poll_unknown_machine_returns_404(http):
    resp = http.get("/api/client/commands?machine_id=DOES-NOT-EXIST&timeout=0")
    assert resp.status_code == 404
