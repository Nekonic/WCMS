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


def post_raw(api, text: str):
    # APIClient의 JSON 렌더러는 짝 없는 서로게이트를 인코딩하지 못하므로 이스케이프된 JSON을 직접 보낸다
    return api.post("/client/register", text, content_type="application/json")


@pytest.mark.parametrize(
    "override",
    [
        {"hostname": "LAB\ud800"},
        {"machine_guid": "g\udc00"},
        {"version": "\ud800"},
        {"specs": {"cpu": "i5\ud800"}},
        {"specs": {"disks": [{"model": ["x", "\udfff"]}]}},
        {"specs": {"key\ud800": 1}},
    ],
)
def test_unencodable_strings_rejected(api, override):
    response = post_raw(api, json.dumps(body(new_pin(), **override)))
    assert response.status_code == 400
    assert response.json()["error"] == "invalid"
    assert not PC.objects.exists()


def test_specs_size_is_measured_in_utf8_bytes(api):
    # 한글 한 글자는 UTF-8로 3바이트, ASCII 이스케이프로는 6자. 기준은 바이트다
    fits = {"x": "한" * 5400}
    assert post(api, body(new_pin(), specs=fits)).status_code == 201
    too_big = {"x": "한" * 5500}
    assert post(api, body(new_pin(), specs=too_big, machine_guid="other")).status_code == 400


def test_non_ascii_specs_render_in_pc_list(api, admin_api):
    specs = {"cpu": "인텔 코어 i5", "os": "Windows 11 교육용"}
    assert post(api, body(new_pin(), hostname="실습실-01", specs=specs)).status_code == 201
    response = admin_api.get("/api/pcs")
    assert response.status_code == 200
    row = response.json()[0]
    assert row["specs"] == specs and row["hostname"] == "실습실-01"
