"""계약: 설치 스크립트 제공 (/install/*)."""


def test_install_cmd_renders(http):
    resp = http.get("/install/install.cmd")
    assert resp.status_code == 200
    assert resp.text.strip()
    assert "WCMS" in resp.text


def test_install_ps1_renders(http):
    resp = http.get("/install/install.ps1")
    assert resp.status_code == 200
    assert resp.text.strip()
    assert "WCMS" in resp.text


def test_install_version_redirects_to_client_version(http):
    resp = http.get("/install/version")
    assert resp.status_code in (301, 302, 307, 308)
    assert resp.headers["Location"].endswith("/api/client/version")


def test_install_cmd_rejects_invalid_server_scheme(http):
    resp = http.get("/install/install.cmd?server=ftp://evil.example")
    assert resp.status_code == 400
