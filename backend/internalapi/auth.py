"""게이트웨이 전용 내부 API 인증.

Rust 게이트웨이는 공유 베어러 토큰(WCMS_INTERNAL_TOKEN)으로 Django 내부 API를
호출한다. 세션/CSRF/사용자 인증과 완전히 분리되어 있다(설계 §3).

Authorization: Bearer <WCMS_INTERNAL_TOKEN>

헤더가 없으면 None 을 반환해 다음 인증 클래스로 폴스루한다.
토큰이 있지만 일치하지 않으면 AuthenticationFailed(401)를 발생시킨다.
"""
from __future__ import annotations

from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions
from rest_framework.permissions import BasePermission


class InternalTokenAuthentication(BaseAuthentication):
    """Authorization: Bearer <WCMS_INTERNAL_TOKEN> 검증.

    성공 시 (None, None)을 반환한다. 내부 API 는 사용자 컨텍스트가 필요 없으므로
    request.user 는 AnonymousUser 로 유지된다. 권한 검사는 IsGateway 에서 수행한다.
    """

    def authenticate(self, request) -> tuple[None, None] | None:
        """Authorization 헤더에서 베어러 토큰을 읽어 공유 시크릿과 비교한다."""
        auth_header: str | None = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header:
            return None

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None

        token: str = parts[1]
        expected: str = getattr(settings, "WCMS_INTERNAL_TOKEN", "dev-internal-token-change-me")

        if token != expected:
            raise exceptions.AuthenticationFailed("내부 API 토큰이 유효하지 않습니다.")

        # 인증 성공: (user, auth) 형태로 반환. 게이트웨이는 사용자 주체가 없음.
        return (None, token)

    def authenticate_header(self, request) -> str:
        """WWW-Authenticate 헤더 값."""
        return 'Bearer realm="internal"'


class IsGateway(BasePermission):
    """InternalTokenAuthentication 이 통과한 요청만 허용한다.

    authenticate() 가 성공하면 request.auth 에 토큰 문자열이 주입된다.
    그 값이 있으면 게이트웨이 요청으로 간주한다.
    """

    def has_permission(self, request, view) -> bool:
        """request.auth 가 비어 있지 않으면 True."""
        return bool(request.auth)
