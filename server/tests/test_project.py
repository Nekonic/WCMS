import io
import os
import subprocess
import sys

import pytest
from django.conf import settings
from django.test import RequestFactory
from rest_framework.exceptions import ParseError

from wcms.api import SafeJSONParser, csrf_failure


def test_version_comes_from_version_file():
    assert settings.WCMS_VERSION == "2026.1"


def test_time_zone_is_utc():
    assert settings.TIME_ZONE == "UTC"


def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.content == b"ok"


def test_unknown_api_path_is_json_404(api):
    response = api.get("/api/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"] == "not_found"


def test_bare_api_path_is_json_404(api):
    response = api.get("/api")
    assert response.status_code == 404
    assert response.json()["error"] == "not_found"


@pytest.mark.django_db
def test_unhandled_error_is_json_500(api, monkeypatch):
    from live.views import PublicRoomList

    def boom(self, request):
        raise RuntimeError("secret internals")

    monkeypatch.setattr(PublicRoomList, "get", boom)
    api.raise_request_exception = False
    response = api.get("/api/public/rooms")
    assert response.status_code == 500
    assert response["Content-Type"] == "application/json"
    assert response.json()["error"] == "server_error"
    assert b"secret internals" not in response.content


def test_csrf_failure_is_json():
    response = csrf_failure(RequestFactory().post("/api/x"), reason="no token")
    assert response.status_code == 403
    assert b'"csrf_failed"' in response.content


def test_safe_json_parser_rejects_deep_nesting():
    stream = io.BytesIO(b"[" * 100_000 + b"]" * 100_000)
    with pytest.raises(ParseError):
        SafeJSONParser().parse(stream)


def test_production_requires_secret_key():
    env = {**os.environ, "WCMS_DEBUG": "0", "DJANGO_SETTINGS_MODULE": "wcms.settings"}
    env.pop("WCMS_SECRET_KEY", None)
    result = subprocess.run(
        [sys.executable, "-c", "import django; django.setup()"],
        env=env,
        cwd=settings.BASE_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "WCMS_SECRET_KEY" in result.stderr
