from django.conf import settings


def test_version_comes_from_version_file():
    assert settings.WCMS_VERSION == "2026.1"


def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.content == b"ok"
