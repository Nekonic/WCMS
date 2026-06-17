"""클라이언트 인증서 기반 DRF 인증 (설계 4.2 mTLS).

nginx 가 mTLS 에서 검증한 클라이언트 인증서를 요청 헤더로 전달하면, Django/DRF 가
해당 인증서를 재검증하고 대응하는 Client 객체를 request.user 로 주입한다.

헤더 이름: settings.WCMS_CLIENT_CERT_HEADER (기본 HTTP_X_SSL_CLIENT_CERT).
값 형식: PEM 원문 또는 URL-인코딩(percent-encoded) PEM.
"""
from __future__ import annotations

import datetime
import uuid
from urllib.parse import unquote

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ec import (
    ECDSA,
    EllipticCurvePublicKey,
)
from cryptography.hazmat.primitives import hashes
from django.conf import settings
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication
from rest_framework.permissions import BasePermission

from enrollment.ca import get_ca
from fleet.models import Client


def _parse_cert(raw: str) -> x509.Certificate:
    """원문 또는 URL-인코딩 PEM 문자열을 x509 Certificate 로 파싱한다.

    nginx 의 $ssl_client_escaped_cert 는 PEM 을 percent-encode 해 전달한다.
    unquote 후에도 PEM 헤더가 없으면 ValueError 를 발생시킨다.
    """
    pem = unquote(raw).strip()
    if not pem.startswith("-----BEGIN"):
        raise ValueError("PEM 헤더가 없습니다.")
    return x509.load_pem_x509_certificate(pem.encode())


def _verify_signature(cert: x509.Certificate, ca_cert: x509.Certificate) -> None:
    """발급자의 공개키로 인증서 서명을 검증한다.

    서명이 유효하지 않으면 InvalidSignature 를 발생시킨다.
    """
    ca_pub: EllipticCurvePublicKey = ca_cert.public_key()  # type: ignore[assignment]
    ca_pub.verify(
        cert.signature,
        cert.tbs_certificate_bytes,
        ECDSA(hashes.SHA256()),
    )


class ClientCertAuthentication(BaseAuthentication):
    """nginx mTLS 포워딩 헤더에서 클라이언트 인증서를 읽어 DRF 인증을 수행한다.

    성공 시 (Client, cert) 튜플을 반환해 request.user = Client 가 된다.
    헤더가 없으면 None 을 반환해 다음 인증 클래스로 폴스루한다.
    인증서가 있지만 유효하지 않으면 AuthenticationFailed 를 발생시킨다.
    """

    def authenticate(
        self, request
    ) -> tuple[Client, x509.Certificate] | None:
        """요청 헤더에서 클라이언트 인증서를 읽어 검증하고 (Client, cert) 를 반환한다."""
        header_name: str = getattr(
            settings, "WCMS_CLIENT_CERT_HEADER", "HTTP_X_SSL_CLIENT_CERT"
        )
        raw: str | None = request.META.get(header_name)
        if not raw:
            # 헤더 부재: 이 인증 클래스를 건너뜀 (401/403 은 DRF 가 처리)
            return None

        # 1. PEM 파싱
        try:
            cert = _parse_cert(raw)
        except Exception as exc:
            raise exceptions.AuthenticationFailed(
                f"클라이언트 인증서 파싱 실패: {exc}"
            ) from exc

        # 2. CA 서명 검증 — 발급자 일치 + 서명 유효
        try:
            ca_cert, _ = get_ca()
        except Exception as exc:
            raise exceptions.AuthenticationFailed(
                f"CA 로드 실패: {exc}"
            ) from exc

        if cert.issuer != ca_cert.subject:
            raise exceptions.AuthenticationFailed(
                "인증서 발급자가 서버 CA 와 일치하지 않습니다."
            )

        try:
            _verify_signature(cert, ca_cert)
        except InvalidSignature as exc:
            raise exceptions.AuthenticationFailed(
                "인증서 서명 검증 실패."
            ) from exc
        except Exception as exc:
            raise exceptions.AuthenticationFailed(
                f"서명 검증 중 오류: {exc}"
            ) from exc

        # 3. 만료 검사 (not_valid_before / not_valid_after vs UTC now)
        now = datetime.datetime.now(datetime.timezone.utc)
        if now < cert.not_valid_before_utc or now > cert.not_valid_after_utc:
            raise exceptions.AuthenticationFailed("인증서가 만료됐거나 아직 유효하지 않습니다.")

        # 4. Subject CN -> Client UUID 매핑
        try:
            cn: str = cert.subject.get_attributes_for_oid(
                x509.NameOID.COMMON_NAME
            )[0].value
            client_id = uuid.UUID(cn)
        except (IndexError, ValueError) as exc:
            raise exceptions.AuthenticationFailed(
                f"인증서 Subject CN 을 UUID 로 파싱할 수 없습니다: {exc}"
            ) from exc

        try:
            client = Client.objects.get(pk=client_id, status=Client.Status.ENROLLED)
        except Client.DoesNotExist:
            raise exceptions.AuthenticationFailed(
                "인증서에 대응하는 등록된 클라이언트를 찾을 수 없습니다."
            )

        return (client, cert)

    def authenticate_header(self, request) -> str:
        """WWW-Authenticate 헤더 값 (DRF 401 응답에 사용)."""
        return "ClientCert"


class IsEnrolledClient(BasePermission):
    """request.user 가 ENROLLED 상태의 Client 인지 확인하는 DRF 권한 클래스."""

    def has_permission(self, request, view) -> bool:
        """Client 인스턴스이고 status == ENROLLED 이면 True."""
        return (
            isinstance(request.user, Client)
            and request.user.status == Client.Status.ENROLLED
        )
