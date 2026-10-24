from pathlib import Path

import yaml
from django.core.management import call_command

SERVER_DIR = Path(__file__).resolve().parents[1]


def generate(tmp_path) -> str:
    target = tmp_path / "openapi.yaml"
    call_command("spectacular", "--file", str(target), "--validate", "--fail-on-warn")
    return target.read_text(encoding="utf-8")


def test_schema_is_committed_and_current(tmp_path):
    assert (SERVER_DIR / "openapi.yaml").read_text(encoding="utf-8") == generate(tmp_path)


def test_schema_contents(tmp_path):
    schema = yaml.safe_load(generate(tmp_path))
    components = schema["components"]["schemas"]
    for name in ("LivePC", "PublicSeat", "PublicRoom", "Error", "Me"):
        assert name in components
    assert "/client/register" not in schema["paths"]
    assert "/api/public/rooms/{id}" in schema["paths"]
    assert set(components["PublicSeat"]["properties"]) == {"row", "col", "label", "online"}


def test_schema_accuracy(tmp_path):
    schema = yaml.safe_load(generate(tmp_path))
    components = schema["components"]["schemas"]
    paths = schema["paths"]
    assert {"rows", "cols", "aisle_after", "sort_order"} <= set(components["Room"]["required"])
    assert {"room", "row", "col", "client_version", "specs"} <= set(components["PC"]["required"])
    assert "fields" not in components["Error"]["required"]
    assert "400" in paths["/api/rooms"]["post"]["responses"]
    assert {"401", "403"} <= set(paths["/api/rooms"]["get"]["responses"])
    assert "403" in paths["/api/auth/logout"]["post"]["responses"]
    assert "401" not in paths["/api/public/rooms"]["get"]["responses"]
