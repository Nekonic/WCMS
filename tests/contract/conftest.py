"""
계약(Characterization) 테스트 하니스.

현재 Flask 서버를 실제 HTTP 서버로 띄우고 requests로 클라이언트<->서버 와이어
계약을 검증한다. 목적은 재작성(Django/Rust) 전에 현재 동작을 실행 가능한 스펙으로
고정하는 것 - 이 테스트가 곧 새 구현이 통과해야 할 인수 스펙이 된다.

재작성 후에는 환경변수 WCMS_CONTRACT_BASE_URL 을 지정하면 Flask 부트스트랩을
건너뛰고 동일한 테스트가 새 구현(다른 언어/스택)을 검증한다. 테스트 본문은 순수
HTTP/JSON 이므로 그대로 재사용된다. 백엔드 의존적인 setup(로그인/토큰/명령 발행)만
이 파일의 픽스처에 격리한다.
"""
import os
import tempfile
import threading
import time
import uuid
from pathlib import Path

import pytest
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = PROJECT_ROOT / "server" / "migrations" / "schema.sql"

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin"
UPDATE_TOKEN = "contract-test-update-token"


class Client:
    """base_url 을 붙여주는 얇은 requests 래퍼. 쿠키는 세션에 유지된다."""

    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()

    def request(self, method, path, **kw):
        kw.setdefault("timeout", 15)
        kw.setdefault("allow_redirects", False)
        return self.session.request(method, self.base_url + path, **kw)

    def get(self, path, **kw):
        return self.request("GET", path, **kw)

    def post(self, path, **kw):
        return self.request("POST", path, **kw)

    def delete(self, path, **kw):
        return self.request("DELETE", path, **kw)

    def close(self):
        self.session.close()


def _start_flask_server():
    """현재 Flask 앱을 임시 파일 DB 로 띄우고 (base_url, shutdown) 반환."""
    import bcrypt

    tmpdir = tempfile.mkdtemp(prefix="wcms-contract-")
    db_path = os.path.join(tmpdir, "contract.sqlite3")

    # 모듈 import 전에 환경 고정 (app.py 는 import 시 create_app 을 실행한다)
    os.environ["WCMS_ENV"] = "development"
    os.environ["WCMS_DB_PATH"] = db_path
    os.environ.setdefault("WCMS_SECRET_KEY", "contract-test-secret")
    os.environ["UPDATE_TOKEN"] = UPDATE_TOKEN
    os.environ["WCMS_LOG_FILE"] = os.path.join(tmpdir, "server.log")

    # server 디렉토리는 tests/conftest.py 가 sys.path 에 추가한다.
    from app import create_app
    from utils.database import get_db, init_db_manager

    app = create_app("development")
    # Config.UPDATE_TOKEN 은 config.py import 시점에 고정되므로(다른 테스트가 먼저
    # import 했을 수 있음) app.config 에 명시적으로 덮어써 import 순서 의존성을 제거한다.
    app.config["UPDATE_TOKEN"] = UPDATE_TOKEN

    with app.app_context():
        init_db_manager(db_path)
        db = get_db()
        db.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        pw = bcrypt.hashpw(ADMIN_PASSWORD.encode(), bcrypt.gensalt()).decode()
        db.execute(
            "INSERT INTO admins (username, password_hash, email, is_active) VALUES (?, ?, ?, ?)",
            (ADMIN_USERNAME, pw, "admin@wcms.local", 1),
        )
        db.execute(
            "INSERT INTO client_versions (version, download_url, changelog) VALUES (?, ?, ?)",
            ("0.7.0", "https://example.invalid/WCMS-Client.exe", "seed"),
        )
        db.commit()

    from werkzeug.serving import make_server

    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    _wait_until_up(base)
    return base, server.shutdown


def _wait_until_up(base, timeout=20):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            requests.get(base + "/api/client/version", timeout=1)
            return
        except requests.RequestException as exc:
            last = exc
            time.sleep(0.1)
    raise RuntimeError(f"계약 테스트 서버가 기동되지 않음: {last}")


@pytest.fixture(scope="session")
def base_url():
    external = os.environ.get("WCMS_CONTRACT_BASE_URL")
    if external:
        # 재작성 구현(Django/Rust 등)을 직접 대상으로 검증
        yield external.rstrip("/")
        return
    base, shutdown = _start_flask_server()
    yield base
    shutdown()


@pytest.fixture
def http(base_url):
    """인증 없는 클라이언트 (Windows 클라이언트 역할)."""
    c = Client(base_url)
    yield c
    c.close()


@pytest.fixture(scope="session")
def admin(base_url):
    """로그인된 관리자 클라이언트 (setup 전용).

    세션 스코프 - 로그인은 1회만 (/login 은 5/min rate limit).
    """
    c = Client(base_url)
    resp = c.post("/login", data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD})
    assert resp.status_code in (302, 303), f"관리자 로그인 실패: {resp.status_code} {resp.text[:200]}"
    yield c
    c.close()


@pytest.fixture
def update_token():
    """클라이언트 버전 업로드용 토큰 (POST /api/client/version)."""
    return UPDATE_TOKEN


@pytest.fixture
def make_pin(admin):
    """등록 PIN 생성 콜백. usage_type: 'single' | 'multi'."""
    def _make(usage_type="single", expires_in=600):
        resp = admin.post(
            "/api/admin/registration-token",
            json={"usage_type": usage_type, "expires_in": expires_in},
        )
        assert resp.status_code == 200, f"토큰 생성 실패: {resp.status_code} {resp.text[:200]}"
        return resp.json()["token"]
    return _make


@pytest.fixture
def issue_command(admin):
    """관리자가 PC 에 명령 발행. (pc_id, type, data, **kw) -> response."""
    def _issue(pc_id, command_type, data=None, **kw):
        body = {"type": command_type}
        if data is not None:
            body["data"] = data
        body.update(kw)
        return admin.post(f"/api/pc/{pc_id}/command", json=body)
    return _issue


@pytest.fixture
def new_machine_id():
    """충돌 없는 machine_id 생성."""
    def _gen(prefix="CT"):
        return f"{prefix}-{uuid.uuid4().hex[:12]}"
    return _gen


@pytest.fixture
def registered_pc(http, make_pin, new_machine_id):
    """단일 사용 PIN 으로 PC 1대 등록 -> (pc_id, machine_id)."""
    pin = make_pin("single")
    machine_id = new_machine_id()
    resp = http.post(
        "/api/client/register",
        json={
            "machine_id": machine_id,
            "pin": pin,
            "hostname": "contract-pc",
            "mac_address": "AA:BB:CC:DD:EE:01",
            "cpu_cores": 4,
            "ram_total": 16.0,
        },
    )
    assert resp.status_code == 200, f"PC 등록 실패: {resp.status_code} {resp.text[:200]}"
    return resp.json()["pc_id"], machine_id
