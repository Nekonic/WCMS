"""계약: POST /api/client/commands/<id>/result (명령 결과 제출).

응답의 final_status 는 클라이언트가 보낸 status 를 그대로 echo 한다 (생략 시 'completed').
서버 내부적으로는 success/completed -> complete, error/failed -> error,
timeout -> timeout, 그 외 -> error 로 DB 상태를 매핑한다 (server/models/command.py).
실제 흐름(발행 -> 폴링 수신 -> 결과 제출)을 따른다.
"""
import pytest


def _deliver(http, issue_command, registered_pc, command_type="execute", data=None):
    """명령을 발행하고 폴링으로 수신(executing)한 뒤 command_id 반환."""
    pc_id, machine_id = registered_pc
    assert issue_command(pc_id, command_type, data=data or {}).status_code == 200
    poll = http.get(f"/api/client/commands?machine_id={machine_id}&timeout=0")
    assert poll.status_code == 200
    return poll.json()["data"]["command"]["id"]


@pytest.mark.parametrize(
    "status", ["completed", "success", "error", "failed", "timeout", "weird-status"]
)
def test_result_accepts_status_and_echoes_it(http, issue_command, registered_pc, status):
    cid = _deliver(http, issue_command, registered_pc)
    resp = http.post(f"/api/client/commands/{cid}/result",
                     json={"status": status, "output": "x"})
    assert resp.status_code == 200
    assert resp.json()["data"]["final_status"] == status


def test_result_defaults_to_completed_when_status_omitted(http, issue_command, registered_pc):
    cid = _deliver(http, issue_command, registered_pc)
    resp = http.post(f"/api/client/commands/{cid}/result", json={"output": "x"})
    assert resp.status_code == 200
    assert resp.json()["data"]["final_status"] == "completed"


def test_result_finalizes_command_so_it_is_not_redelivered(http, issue_command, registered_pc):
    pc_id, machine_id = registered_pc
    assert issue_command(pc_id, "execute", data={}).status_code == 200
    poll = http.get(f"/api/client/commands?machine_id={machine_id}&timeout=0")
    cid = poll.json()["data"]["command"]["id"]
    http.post(f"/api/client/commands/{cid}/result", json={"status": "completed"})
    # 결과 제출 후 동일 명령은 더 이상 전달되지 않는다 (pending 아님).
    again = http.get(f"/api/client/commands?machine_id={machine_id}&timeout=0")
    assert again.json()["data"]["has_command"] is False


def test_result_for_unknown_command_returns_404(http):
    resp = http.post("/api/client/commands/999999/result", json={"status": "completed"})
    assert resp.status_code == 404
