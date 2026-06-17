"""WCMS CA(인증 기관) 유틸리티.

서버 CA 인증서·개인키를 로드하거나, 파일이 없으면 자체 서명 CA 를 생성한다.
클라이언트 CSR 에 서명해 클라이언트 인증서를 발급한다(설계 4.2).

CA 파일 경로:
    settings.WCMS_CA_CERT_PATH  — PEM CA 인증서
    settings.WCMS_CA_KEY_PATH   — PEM EC P-256 개인키 (파일 모드 0o600)
"""
from __future__ import annotations

import datetime
import os
import stat
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID
from django.conf import settings


# CA 유효 기간: 약 10년
_CA_VALIDITY_DAYS: int = 365 * 10

# 클라이언트 인증서 유효 기간: 약 2년
_CLIENT_VALIDITY_DAYS: int = 365 * 2


def _build_ca() -> tuple[x509.Certificate, ec.EllipticCurvePrivateKey]:
    """EC P-256 자체 서명 CA 키쌍과 인증서를 생성해 반환한다."""
    private_key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "WCMS Dev CA"),
    ])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert: x509.Certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=_CA_VALIDITY_DAYS))
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        )
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(private_key.public_key()),
            critical=False,
        )
        .sign(private_key, hashes.SHA256())
    )
    return cert, private_key


def _write_ca(
    cert: x509.Certificate,
    private_key: ec.EllipticCurvePrivateKey,
    cert_path: Path,
    key_path: Path,
) -> None:
    """CA 인증서와 개인키를 PEM 파일로 저장한다. 개인키 파일은 0o600 권한."""
    cert_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.parent.mkdir(parents=True, exist_ok=True)

    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )

    cert_path.write_bytes(cert_pem)
    key_path.write_bytes(key_pem)
    os.chmod(key_path, stat.S_IRUSR | stat.S_IWUSR)  # 0o600


def get_ca() -> tuple[x509.Certificate, ec.EllipticCurvePrivateKey]:
    """CA 인증서와 개인키를 반환한다.

    파일이 모두 존재하면 디스크에서 읽고, 하나라도 없으면 새 CA 를 생성해
    디스크에 저장한 뒤 반환한다.

    Returns:
        (ca_cert, ca_key) 튜플.
    """
    cert_path = Path(settings.WCMS_CA_CERT_PATH)
    key_path = Path(settings.WCMS_CA_KEY_PATH)

    if cert_path.exists() and key_path.exists():
        cert = x509.load_pem_x509_certificate(cert_path.read_bytes())
        private_key = serialization.load_pem_private_key(
            key_path.read_bytes(), password=None
        )
        return cert, private_key  # type: ignore[return-value]

    # 파일 부재: 자체 서명 CA 생성
    cert, private_key = _build_ca()
    _write_ca(cert, private_key, cert_path, key_path)
    return cert, private_key


def sign_client_csr(
    csr: x509.CertificateSigningRequest,
    client_id: str,
) -> x509.Certificate:
    """클라이언트 CSR 에 서명하여 인증서를 발급한다.

    발급된 인증서의 Subject CN 은 client_id(UUID 문자열)이며 유효 기간은 2년이다.

    Args:
        csr: 파싱된 x509 CSR 객체.
        client_id: 클라이언트 UUID 문자열 (Subject CN 으로 삽입).

    Returns:
        서명된 x509 Certificate.
    """
    ca_cert, ca_key = get_ca()

    now = datetime.datetime.now(datetime.timezone.utc)
    subject = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, client_id),
    ])
    cert: x509.Certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(csr.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=_CLIENT_VALIDITY_DAYS))
        .add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        )
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(csr.public_key()),
            critical=False,
        )
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_cert.public_key()),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )
    return cert
