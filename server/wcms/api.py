from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404, HttpRequest, JsonResponse
from rest_framework import exceptions, permissions, serializers
from rest_framework.authentication import SessionAuthentication
from rest_framework.parsers import JSONParser


class SessionAuth(SessionAuthentication):
    """세션 인증. 미인증 요청이 403이 아니라 401을 받도록 인증 헤더 값을 돌려준다."""

    def authenticate_header(self, request) -> str:
        return "Session"


def is_admin(user) -> bool:
    return bool(user is not None and user.is_authenticated and user.is_active and user.is_staff)


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view) -> bool:
        return is_admin(request.user)


class ApiError(exceptions.APIException):
    """오류 코드와 상태를 직접 지정하는 API 오류."""

    def __init__(self, code: str, detail: str, status_code: int = 400):
        self.status_code = status_code
        super().__init__(detail=detail, code=code)


class SafeJSONParser(JSONParser):
    """너무 깊게 중첩된 JSON이 500이 아니라 400이 되게 한다."""

    def parse(self, stream, media_type=None, parser_context=None):
        try:
            return super().parse(stream, media_type, parser_context)
        except RecursionError:
            raise exceptions.ParseError("JSON이 너무 깊게 중첩되어 있습니다.")


class ErrorSerializer(serializers.Serializer):
    error = serializers.CharField()
    detail = serializers.CharField()
    fields = serializers.DictField(required=False)


def error_responses(*statuses: int) -> dict:
    return {status: ErrorSerializer for status in statuses}


def error_body(code: str, detail: str, fields: dict | None = None) -> dict:
    body: dict = {"error": code, "detail": detail}
    if fields:
        body["fields"] = fields
    return body


def exception_handler(exc, context):
    # 모듈 최상단에서 import하면 DRF schemas가 아직 정의 전인 SessionAuth/IsAdmin을 참조해 순환 import가 난다.
    from rest_framework.views import exception_handler as drf_exception_handler

    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, DjangoPermissionDenied):
        exc = exceptions.PermissionDenied()
    response = drf_exception_handler(exc, context)
    if response is None:
        return None
    if isinstance(exc, exceptions.ValidationError):
        data = response.data
        fields = data if isinstance(data, dict) else {"non_field_errors": data}
        response.data = error_body("invalid", "입력값을 확인하세요.", fields)
        return response
    codes = exc.get_codes() if hasattr(exc, "get_codes") else "error"
    code = codes if isinstance(codes, str) else "error"
    detail = response.data.get("detail", "") if isinstance(response.data, dict) else ""
    response.data = error_body(code, str(detail))
    return response


def csrf_failure(request: HttpRequest, reason: str = "") -> JsonResponse:
    return JsonResponse(error_body("csrf_failed", "보안 토큰이 없거나 맞지 않습니다. 새로고침 후 다시 시도하세요."), status=403)


def api_not_found(request: HttpRequest, *args, **kwargs) -> JsonResponse:
    return JsonResponse(error_body("not_found", "없는 API입니다."), status=404)
