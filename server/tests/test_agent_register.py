import json
from pathlib import Path

import pytest
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.test import override_settings

from labs.models import PC, RegistrationPin
from wcms.groups import pc_group

pytestmark = pytest.mark.django_db
EXAMPLES = Path(__file__).resolve().parents[2] / "protocol" / "examples"


def body(pin: str, **override) -> dict:
    data = json.loads((EXAMPLES / "register_request.json").read_text(encoding="utf-8"))
    data["pin"] = pin
    data.update(override)
    return data


def new_pin() -> str:
    return RegistrationPin.issue(user=None, multi_use=True, minutes=10).pin


def post(api, data, **extra):
    return api.post("/client/register", data, format="json", **extra)


def test_register_example_succeeds(api):
    response = post(api, body(new_pin()))
    assert response.status_code == 201
    data = response.json()
    expected_keys = json.loads((EXAMPLES / "register_response.json").read_text()).keys()
    assert data.keys() == expected_keys
    assert PC.from_token(data["token"]).id == data["pc_id"]


def test_invalid_pin(api):
    response = post(api, body("999999"))
    assert response.status_code == 403
    assert response.json()["error"] == "invalid_pin"


@pytest.mark.parametrize(
    "override", [{"pin": "12ab56"}, {"hostname": ""}, {"hostname": "x" * 65}, {"specs": [1]}, {"specs": {"x": "a" * 20000}}]
)
def test_invalid_fields(api, override):
    response = post(api, body(**{"pin": new_pin(), **override}))
    assert response.status_code == 400
    assert response.json()["error"] == "invalid"


def test_lockout_after_ten_wrong_pins(api):
    for _ in range(10):
        post(api, body("000000"))
    response = post(api, body(new_pin()))
    assert response.status_code == 429


def test_reregister_revokes_old_connection(api):
    first = post(api, body(new_pin())).json()
    layer = get_channel_layer()
    channel = async_to_sync(layer.new_channel)()
    async_to_sync(layer.group_add)(pc_group(first["pc_id"]), channel)
    second = post(api, body(new_pin())).json()
    assert second["pc_id"] == first["pc_id"]
    assert async_to_sync(layer.receive)(channel) == {"type": "pc.revoked"}


def test_requires_internal_path_when_enabled(api):
    with override_settings(WCMS_REQUIRE_INTERNAL=True):
        assert post(api, body(new_pin())).status_code == 404
        assert post(api, body(new_pin()), HTTP_X_WCMS_VIA="internal").status_code == 201


def test_get_not_allowed(api):
    assert api.get("/client/register").status_code == 405


@pytest.mark.parametrize("pin", [123456, "١٢٣٤٥٦", "123456\n", " 123456", "123456 ", None, ["123456"]])
def test_malformed_pin_is_400(api, pin):
    response = post(api, body(pin))
    assert response.status_code == 400
    assert response.json()["error"] == "invalid"


def test_malformed_pins_do_not_count_toward_lockout(api):
    for _ in range(10):
        assert post(api, body(123456)).status_code == 400
        assert post(api, body("١٢٣٤٥٦")).status_code == 400
    assert post(api, body(new_pin())).status_code == 201
