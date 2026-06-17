"""POST /api/client/logs/ — 클라이언트 인증서 인증 + 배치 업로드 통합 테스트 (설계 4.2, 4.3).

헬퍼: tmp_path 기반 CA/클라이언트 인증서를 인-프로세스로 생성하고,
WCMS_CA_CERT_PATH / WCMS_CA_KEY_PATH 를 해당 경로로 override 한 뒤
APIClient(HTTP_X_SSL_CLIENT_CERT=pem) 으로 요청을 보낸다.

Throttle 테스트: override_settings 로 "login" 범위를 1/min 으로 낮춰 반복 호출 시 429 를 확인.
"""
from __future__ import annotations

import datetime
from pathlib import Path
from urllib.parse import quote

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID
from django.test import override_settings
from rest_framework.test import APIClient

from clientlogs.models import ClientLog
from fleet.models import Client


# ---------------------------------------------------------------------------
# 인-프로세스 PKI 헬퍼
# ---------------------------------------------------------------------------

def _make_ca(tmp_path: Path) -> tuple[x509.Certificate, ec.EllipticCurvePrivateKey]:
    """자체 서명 테스트용 CA 키쌍·인증서를 생성하고 tmp_path 에 저장한다."""
    key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Test CA")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )
    cert_path = tmp_path / "ca.crt"
    key_path = tmp_path / "ca.key"
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
    )
    return cert, key


def _sign_client_cert(
    ca_cert: x509.Certificate,
    ca_key: ec.EllipticCurvePrivateKey,
    client_id: str,
) -> str:
    """CA 로 서명한 클라이언트 인증서 PEM 을 반환한다. Subject CN = client_id."""
    client_key = ec.generate_private_key(ec.SECP256R1())
    now = datetime.datetime.now(datetime.timezone.utc)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, client_id)])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(client_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(ca_key, hashes.SHA256())
    )
    return cert.public_bytes(serialization.Encoding.PEM).decode()


# ---------------------------------------------------------------------------
# 픽스처
# ---------------------------------------------------------------------------

@pytest.fixture()
def pki(tmp_path):
    """테스트 CA 를 생성하고 Django settings 를 tmp_path 의 CA 파일로 override 한다."""
    ca_cert, ca_key = _make_ca(tmp_path)
    with override_settings(
        WCMS_CA_CERT_PATH=str(tmp_path / "ca.crt"),
        WCMS_CA_KEY_PATH=str(tmp_path / "ca.key"),
    ):
        yield ca_cert, ca_key


@pytest.fixture()
def enrolled_client(db):
    """ENROLLED 상태의 Client 인스턴스를 생성한다."""
    return Client.objects.create(hostname="test-pc", status=Client.Status.ENROLLED)


# ---------------------------------------------------------------------------
# 정상 케이스
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_log_batch_upload_valid(pki, enrolled_client):
    """유효한 클라이언트 인증서 + 정상 배치 -> 201 + DB 행 생성."""
    ca_cert, ca_key = pki
    client_pem = _sign_client_cert(ca_cert, ca_key, str(enrolled_client.id))

    api = APIClient(HTTP_X_SSL_CLIENT_CERT=client_pem)
    payload = {
        "logs": [
            {"level": "info", "message": "부팅 완료"},
            {"level": "warning", "message": "디스크 90%", "source": "monitor.py"},
            {"level": "error", "message": "네트워크 오류", "detail": {"code": 503}},
        ]
    }
    resp = api.post("/api/client/logs/", data=payload, format="json")

    assert resp.status_code == 201
    assert resp.data["created"] == 3
    assert ClientLog.objects.filter(client=enrolled_client).count() == 3


@pytest.mark.django_db
def test_log_batch_creates_rows_for_correct_client(pki, db):
    """배치 업로드가 인증서의 클라이언트에만 로그를 생성하는지 확인한다."""
    ca_cert, ca_key = pki
    client_a = Client.objects.create(hostname="PC-A", status=Client.Status.ENROLLED)
    client_b = Client.objects.create(hostname="PC-B", status=Client.Status.ENROLLED)

    pem_a = _sign_client_cert(ca_cert, ca_key, str(client_a.id))
    api = APIClient(HTTP_X_SSL_CLIENT_CERT=pem_a)
    resp = api.post(
        "/api/client/logs/",
        data={"logs": [{"level": "debug", "message": "A 로그"}]},
        format="json",
    )

    assert resp.status_code == 201
    assert ClientLog.objects.filter(client=client_a).count() == 1
    assert ClientLog.objects.filter(client=client_b).count() == 0


# ---------------------------------------------------------------------------
# 인증 실패 케이스
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_log_upload_missing_cert_header(pki, enrolled_client):
    """인증서 헤더가 없으면 401 또는 403 을 반환해야 한다."""
    api = APIClient()  # 헤더 없음
    resp = api.post(
        "/api/client/logs/",
        data={"logs": [{"level": "info", "message": "테스트"}]},
        format="json",
    )
    assert resp.status_code in (401, 403)


@pytest.mark.django_db
def test_log_upload_unknown_client_cert(pki, db):
    """DB 에 없는 UUID 로 서명된 인증서 -> 401/403."""
    ca_cert, ca_key = pki
    import uuid
    unknown_id = str(uuid.uuid4())
    pem = _sign_client_cert(ca_cert, ca_key, unknown_id)

    api = APIClient(HTTP_X_SSL_CLIENT_CERT=pem)
    resp = api.post(
        "/api/client/logs/",
        data={"logs": [{"level": "info", "message": "테스트"}]},
        format="json",
    )
    assert resp.status_code in (401, 403)


@pytest.mark.django_db
def test_log_upload_revoked_client_cert(pki, db):
    """REVOKED 상태 클라이언트의 인증서 -> 401/403."""
    ca_cert, ca_key = pki
    client = Client.objects.create(hostname="revoked-pc", status=Client.Status.REVOKED)
    pem = _sign_client_cert(ca_cert, ca_key, str(client.id))

    api = APIClient(HTTP_X_SSL_CLIENT_CERT=pem)
    resp = api.post(
        "/api/client/logs/",
        data={"logs": [{"level": "info", "message": "테스트"}]},
        format="json",
    )
    assert resp.status_code in (401, 403)


@pytest.mark.django_db
def test_log_upload_url_encoded_pem(pki, enrolled_client):
    """nginx 가 URL-인코딩한 PEM 도 올바르게 처리해야 한다."""
    ca_cert, ca_key = pki
    client_pem = _sign_client_cert(ca_cert, ca_key, str(enrolled_client.id))
    encoded_pem = quote(client_pem, safe="")

    api = APIClient(HTTP_X_SSL_CLIENT_CERT=encoded_pem)
    resp = api.post(
        "/api/client/logs/",
        data={"logs": [{"level": "info", "message": "URL-인코딩 테스트"}]},
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["created"] == 1


# ---------------------------------------------------------------------------
# 요청 본문 검증 케이스
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_log_upload_malformed_body(pki, enrolled_client):
    """올바르지 않은 요청 본문 -> 400."""
    ca_cert, ca_key = pki
    pem = _sign_client_cert(ca_cert, ca_key, str(enrolled_client.id))
    api = APIClient(HTTP_X_SSL_CLIENT_CERT=pem)

    # logs 키 자체가 없는 경우
    resp = api.post("/api/client/logs/", data={"wrong_key": []}, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_log_upload_empty_logs_array(pki, enrolled_client):
    """logs 배열이 비어 있으면 400 을 반환해야 한다."""
    ca_cert, ca_key = pki
    pem = _sign_client_cert(ca_cert, ca_key, str(enrolled_client.id))
    api = APIClient(HTTP_X_SSL_CLIENT_CERT=pem)

    resp = api.post("/api/client/logs/", data={"logs": []}, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_log_upload_invalid_level(pki, enrolled_client):
    """유효하지 않은 level 값이 있으면 400 을 반환해야 한다."""
    ca_cert, ca_key = pki
    pem = _sign_client_cert(ca_cert, ca_key, str(enrolled_client.id))
    api = APIClient(HTTP_X_SSL_CLIENT_CERT=pem)

    resp = api.post(
        "/api/client/logs/",
        data={"logs": [{"level": "INVALID_LEVEL", "message": "테스트"}]},
        format="json",
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# rate limit 테스트 (login 범위)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_login_rate_limit_returns_429():
    """login 범위 rate limit 이 임계를 초과하면 429 를 반환해야 한다.

    DRF 의 SimpleRateThrottle.THROTTLE_RATES 는 모듈 임포트 시 api_settings 로부터
    클래스 속성으로 굳어진다. unittest.mock.patch 로 "1/min" 을 직접 주입해 결정론적으로
    429 를 유발한다. override_settings 만으로는 클래스 속성이 갱신되지 않는다.

    Django 기본 캐시(LocMemCache)는 프로세스 공유이므로 이전 테스트의 throttle 카운터가
    남아 있을 수 있다. cache.clear() 로 깨끗한 상태에서 시작한다.
    """
    from unittest.mock import patch

    from django.core.cache import cache

    low_rates = {"login": "1/min", "enroll": "20/min"}

    # throttle 카운터를 초기화해 다른 테스트의 영향을 제거한다
    cache.clear()

    with patch("rest_framework.throttling.SimpleRateThrottle.THROTTLE_RATES", low_rates):
        api = APIClient()
        payload = {"username": "nobody", "password": "badpass"}

        # 첫 번째 요청: 인증 실패(401)지만 rate limit 카운트는 증가
        resp1 = api.post("/api/auth/login/", data=payload, format="json")
        assert resp1.status_code in (200, 400, 401)

        # 두 번째 요청: 1/min 초과 -> 429
        resp2 = api.post("/api/auth/login/", data=payload, format="json")
        assert resp2.status_code == 429
