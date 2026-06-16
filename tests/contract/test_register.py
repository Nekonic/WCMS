"""계약: POST /api/client/register (PC 등록 + PIN 인증)."""


def test_register_success_returns_pc_id(http, make_pin, new_machine_id):
    pin = make_pin("single")
    resp = http.post("/api/client/register", json={
        "machine_id": new_machine_id(),
        "pin": pin,
        "hostname": "pc1",
        "mac_address": "AA:BB:CC:00:00:01",
        "cpu_cores": 4,
        "ram_total": 16.0,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert isinstance(body["pc_id"], int)


def test_register_missing_machine_id_returns_400(http, make_pin):
    pin = make_pin("single")
    resp = http.post("/api/client/register", json={"pin": pin})
    assert resp.status_code == 400


def test_register_missing_pin_returns_400(http, new_machine_id):
    resp = http.post("/api/client/register", json={"machine_id": new_machine_id()})
    assert resp.status_code == 400


def test_register_invalid_pin_returns_403(http, new_machine_id):
    resp = http.post("/api/client/register", json={
        "machine_id": new_machine_id(),
        "pin": "999999",
    })
    assert resp.status_code == 403


def test_register_single_use_pin_rejects_second_pc(http, make_pin, new_machine_id):
    pin = make_pin("single")
    first = http.post("/api/client/register", json={
        "machine_id": new_machine_id(), "pin": pin})
    assert first.status_code == 200
    second = http.post("/api/client/register", json={
        "machine_id": new_machine_id(), "pin": pin})
    assert second.status_code == 403


def test_register_multi_use_pin_allows_multiple_pcs(http, make_pin, new_machine_id):
    pin = make_pin("multi")
    for _ in range(3):
        resp = http.post("/api/client/register", json={
            "machine_id": new_machine_id(), "pin": pin})
        assert resp.status_code == 200
