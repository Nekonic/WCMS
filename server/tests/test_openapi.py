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
