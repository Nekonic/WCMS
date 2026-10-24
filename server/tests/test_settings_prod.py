import os
import subprocess
import sys
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parent.parent
PROD = {
    "WCMS_DEBUG": "0",
    "WCMS_SECRET_KEY": "x" * 50,
    "WCMS_REDIS_URL": "redis://localhost:6379/0",
    "WCMS_ALLOWED_HOSTS": "wcms.example",
    "WCMS_CSRF_TRUSTED_ORIGINS": "https://wcms.example",
}


def load_settings(env: dict[str, str]) -> subprocess.CompletedProcess:
    base = {key: value for key, value in os.environ.items() if not key.startswith("WCMS_")}
    return subprocess.run(
        [sys.executable, "-c", "import wcms.settings"],
        cwd=SERVER_DIR,
        env={**base, **env},
        capture_output=True,
        text=True,
    )


def test_complete_production_settings_load():
    assert load_settings(PROD).returncode == 0


def test_missing_production_settings_are_named():
    env = {key: value for key, value in PROD.items() if key not in {"WCMS_REDIS_URL", "WCMS_ALLOWED_HOSTS"}}
    result = load_settings(env)
    assert result.returncode != 0
    assert "ImproperlyConfigured" in result.stderr
    assert "WCMS_REDIS_URL" in result.stderr
    assert "WCMS_ALLOWED_HOSTS" in result.stderr


def test_debug_needs_nothing():
    assert load_settings({}).returncode == 0


def test_empty_secret_key_is_rejected_like_the_dev_key():
    for secret in ("", "dev-only-insecure-key"):
        result = load_settings({**PROD, "WCMS_SECRET_KEY": secret})
        assert result.returncode != 0
        assert "WCMS_SECRET_KEY" in result.stderr
