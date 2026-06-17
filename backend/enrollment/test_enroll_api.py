"""클라이언트 enrollment API 검증 (POST /api/client/enroll/).

테스트마다 임시 CA 디렉터리를 사용해 backend/ca/ 를 건드리지 않는다.
클라이언트 EC 키쌍 + CSR 은 cryptography 라이브러리로 직접 생성한다.
"""
from __future__ import annotations

import datetime

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID
from django.utils import timezone
from rest_framework.test import APIClient

from enrollment.models import EnrollmentToken
from fleet.models import Client


# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------

def _make_client_csr() -> tuple[ec.EllipticCurvePrivateKey, str]:
    """EC P-256 클라이언트 키쌍과 PEM CSR 을 생성한다."""
    key = ec.generate_private_key(ec.SECP256R1())
    csr = (
        x509.CertificateSigningRequestBuilder()
        .subject_name(x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, "test-client"),
        ]))
        .sign(key, hashes.SHA256())
    )
    csr_pem = csr.public_bytes(serialization.Encoding.PEM).decode()
    return key, csr_pem


def _make_token(
    usage_type: str = "single",
    expires_in: int = 600,
    used_count: int = 0,
    is_expired: bool = False,
) -> EnrollmentToken:
    """유효한 EnrollmentToken 을 생성한다."""
    now = timezone.now()
    return EnrollmentToken.objects.create(
        token="123456",
        usage_type=usage_type,
        expires_in=expires_in,
        expires_at=now + datetime.timedelta(seconds=expires_in),
        created_by="test",
        used_count=used_count,
        is_expired=is_expired,
    )


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _use_tmp_ca(tmp_path, settings):
    """각 테스트마다 임시 CA 디렉터리를 사용해 실제 CA 파일을 건드리지 않는다."""
    settings.WCMS_CA_CERT_PATH = str(tmp_path / "ca.crt")
    settings.WCMS_CA_KEY_PATH = str(tmp_path / "ca.key")
    # enrollment.ca 모듈은 settings 값을 호출 시점에 읽으므로 캐시 초기화 불필요.


@pytest.fixture
def api() -> APIClient:
    """인증 없는 API 클라이언트."""
    return APIClient()


@pytest.fixture
def csr_pem() -> str:
    """테스트용 클라이언트 CSR PEM."""
    _, pem = _make_client_csr()
    return pem


# ---------------------------------------------------------------------------
# 테스트 케이스
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_enroll_success_201(api, csr_pem):
    """정상 enrollment 시 201, client_id + 인증서가 반환되고 DB 가 갱신된다."""
    token = _make_token(usage_type="single")

    resp = api.post(
        "/api/client/enroll/",
        {
            "pin": token.token,
            "csr_pem": csr_pem,
            "hostname": "lab-pc-01",
            "mac_address": "AA:BB:CC:DD:EE:FF",
        },
        format="json",
    )

    assert resp.status_code == 201, resp.data

    data = resp.data
    assert "client_id" in data
    assert "certificate_pem" in data
    assert "ca_certificate_pem" in data

    # certificate_pem 이 유효한 x509 인증서이어야 한다
    cert = x509.load_pem_x509_certificate(data["certificate_pem"].encode())

    # Subject CN 이 client_id 와 일치해야 한다
    cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
    assert cn == data["client_id"]

    # DB 확인: Client 행 존재, certificate_pem 저장
    from uuid import UUID
    client_uuid = UUID(data["client_id"])
    client = Client.objects.get(pk=client_uuid)
    assert client.certificate_pem is not None
    assert client.hostname == "lab-pc-01"
    assert client.mac_address == "AA:BB:CC:DD:EE:FF"
    assert client.is_verified is True

    # 토큰 used_count 증가, 1회용이면 is_expired=True
    token.refresh_from_db()
    assert token.used_count == 1
    assert token.is_expired is True


@pytest.mark.django_db
def test_enroll_wrong_pin_returns_403(api, csr_pem):
    """존재하지 않는 PIN 은 403 을 반환한다."""
    resp = api.post(
        "/api/client/enroll/",
        {"pin": "000000", "csr_pem": csr_pem},
        format="json",
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_enroll_single_token_reuse_returns_403(api, csr_pem):
    """1회용 토큰을 두 번 사용하면 두 번째 호출이 403 을 반환한다."""
    _, csr_pem2 = _make_client_csr()
    token = _make_token(usage_type="single")

    # 첫 번째 호출 — 성공해야 한다
    resp1 = api.post(
        "/api/client/enroll/",
        {"pin": token.token, "csr_pem": csr_pem},
        format="json",
    )
    assert resp1.status_code == 201

    # 두 번째 호출 — 403 이어야 한다
    resp2 = api.post(
        "/api/client/enroll/",
        {"pin": token.token, "csr_pem": csr_pem2},
        format="json",
    )
    assert resp2.status_code == 403


@pytest.mark.django_db
def test_enroll_missing_csr_pem_returns_400(api):
    """csr_pem 누락 시 400 을 반환한다."""
    token = _make_token()
    resp = api.post(
        "/api/client/enroll/",
        {"pin": token.token},
        format="json",
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_enroll_missing_pin_returns_400(api, csr_pem):
    """pin 누락 시 400 을 반환한다."""
    resp = api.post(
        "/api/client/enroll/",
        {"csr_pem": csr_pem},
        format="json",
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_enroll_invalid_csr_returns_400(api):
    """잘못된 CSR PEM 은 400 을 반환한다."""
    token = _make_token()
    resp = api.post(
        "/api/client/enroll/",
        {"pin": token.token, "csr_pem": "not-a-valid-csr"},
        format="json",
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_enroll_expired_token_returns_403(api, csr_pem):
    """만료 시각이 과거인 토큰은 403 을 반환한다."""
    now = timezone.now()
    token = EnrollmentToken.objects.create(
        token="999999",
        usage_type="single",
        expires_in=600,
        expires_at=now - datetime.timedelta(seconds=1),
        created_by="test",
    )
    resp = api.post(
        "/api/client/enroll/",
        {"pin": token.token, "csr_pem": csr_pem},
        format="json",
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_enroll_multi_token_allows_multiple_uses(api):
    """multi 타입 토큰은 여러 번 사용 가능하다."""
    token = _make_token(usage_type="multi")

    for _ in range(3):
        _, csr_pem_i = _make_client_csr()
        resp = api.post(
            "/api/client/enroll/",
            {"pin": token.token, "csr_pem": csr_pem_i},
            format="json",
        )
        assert resp.status_code == 201

    token.refresh_from_db()
    assert token.used_count == 3
    assert token.is_expired is False
