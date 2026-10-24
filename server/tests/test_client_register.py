import json

import pytest

from labs.models import PC, RegistrationPin

pytestmark = pytest.mark.django_db


def payload(pin: str, **override) -> dict:
    data = {
        "pin": pin,
        "hostname": "LAB-01",
        "machine_guid": "guid-1",
        "specs": {"cpu": "Intel Core i5-12400"},
        "version": "2026.1",
    }
    data.update(override)
    return data


def post(client, body):
    data = body if isinstance(body, str) else json.dumps(body)
    return client.post("/client/register", data=data, content_type="application/json")


def new_pin() -> str:
    return RegistrationPin.issue(user=None, multi_use=False, minutes=10).pin


def test_register_success(client):
    response = post(client, payload(new_pin()))
    assert response.status_code == 201
    body = response.json()
    pc = PC.from_token(body["token"])
    assert pc.id == body["pc_id"]
    assert pc.specs == {"cpu": "Intel Core i5-12400"}
    assert pc.client_version == "2026.1"


def test_invalid_pin(client):
    response = post(client, payload("999999"))
    assert response.status_code == 403
    assert response.json() == {"error": "invalid_pin"}


def test_bad_json(client):
    response = post(client, "{not json")
    assert response.status_code == 400
    assert response.json() == {"error": "bad_json"}


def test_non_object_json(client):
    response = post(client, "[1, 2]")
    assert response.status_code == 400
    assert response.json() == {"error": "bad_json"}


def test_missing_hostname(client):
    response = post(client, payload(new_pin(), hostname=None))
    assert response.status_code == 400
    assert response.json() == {"error": "bad_fields"}


def test_too_long_hostname(client):
    response = post(client, payload(new_pin(), hostname="x" * 65))
    assert response.status_code == 400


def test_specs_too_large(client):
    response = post(client, payload(new_pin(), specs={"x": "a" * 20000}))
    assert response.status_code == 400
    assert response.json() == {"error": "specs_too_large"}


def test_lockout_after_ten_failures(client):
    for _ in range(10):
        post(client, payload("000000"))
    response = post(client, payload(new_pin()))
    assert response.status_code == 429
    assert response.json() == {"error": "too_many_attempts"}


def test_get_not_allowed(client):
    assert client.get("/client/register").status_code == 405
