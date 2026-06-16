"""계약: 클라이언트 버전 조회/등록 (GET/POST /api/client/version).

주의(현재 Flask 한계): GET 은 `ORDER BY released_at DESC` 인데 released_at 이 초 단위라
같은 초에 등록된 버전들 사이의 "최신" 선택이 비결정적이다. 재작성에서는 id/semver 등
결정론적 기준으로 수정해야 한다. 아래 round-trip 테스트는 초 경계를 넘겨 이를 회피한다.
"""
import time


def test_get_version_returns_expected_shape(http):
    resp = http.get("/api/client/version")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    for key in ("version", "download_url", "changelog", "released_at"):
        assert key in body
    assert isinstance(body["version"], str) and body["version"]


def test_post_version_with_bearer_token_accepted(http, update_token):
    resp = http.post(
        "/api/client/version",
        headers={"Authorization": f"Bearer {update_token}"},
        json={"version": "9.9.9", "download_url": "https://example.invalid/x.exe", "changelog": "c"},
    )
    assert resp.status_code == 200


def test_registered_version_becomes_latest(http, update_token):
    # 초 경계를 넘겨 released_at 이 시드/이전 버전보다 확실히 늦도록 한다.
    time.sleep(1.1)
    resp = http.post(
        "/api/client/version",
        headers={"Authorization": f"Bearer {update_token}"},
        json={"version": "12.0.0", "download_url": "https://example.invalid/v12.exe", "changelog": "c"},
    )
    assert resp.status_code == 200
    got = http.get("/api/client/version").json()
    assert got["version"] == "12.0.0"


def test_post_version_with_admin_session(admin):
    resp = admin.post("/api/client/version",
                      json={"version": "9.9.10", "download_url": "https://example.invalid/y.exe"})
    assert resp.status_code == 200


def test_post_version_without_auth_returns_401(http):
    resp = http.post("/api/client/version",
                     json={"version": "1.2.3", "download_url": "https://example.invalid/z.exe"})
    assert resp.status_code == 401


def test_post_version_with_wrong_bearer_returns_403(http):
    resp = http.post(
        "/api/client/version",
        headers={"Authorization": "Bearer wrong-token"},
        json={"version": "1.2.3", "download_url": "https://example.invalid/z.exe"},
    )
    assert resp.status_code == 403


def test_post_version_missing_fields_returns_400(http, update_token):
    resp = http.post(
        "/api/client/version",
        headers={"Authorization": f"Bearer {update_token}"},
        json={"version": "1.2.3"},
    )
    assert resp.status_code == 400
