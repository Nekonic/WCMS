from drf_spectacular.extensions import OpenApiAuthenticationExtension


class SessionAuthScheme(OpenApiAuthenticationExtension):
    target_class = "wcms.api.SessionAuth"
    name = "sessionAuth"

    def get_security_definition(self, auto_schema):
        return {"type": "apiKey", "in": "cookie", "name": "sessionid"}


# 응답에 항상 들어 있는 필드를 optional로 만들지 않도록 required를 전부 채울 응답 컴포넌트.
ALWAYS_PRESENT = ("Room", "PC", "Pin", "AuditLog")
ERROR_REF = {"$ref": "#/components/schemas/Error"}
UNSAFE_METHODS = ("post", "put", "patch", "delete")
HTTP_METHODS = ("get", "put", "post", "delete", "options", "head", "patch", "trace")


def _error_response(description: str) -> dict:
    return {"content": {"application/json": {"schema": ERROR_REF}}, "description": description}


def postprocess_responses(result, generator, request, public):
    schemas = result.get("components", {}).get("schemas", {})
    for name in ALWAYS_PRESENT:
        component = schemas.get(name)
        if component is not None:
            component["required"] = sorted(component["properties"])

    for path_item in result.get("paths", {}).values():
        for method, operation in path_item.items():
            if method not in HTTP_METHODS:
                continue
            responses = operation.setdefault("responses", {})
            if {} not in operation.get("security", []):
                responses.setdefault("401", _error_response("인증 필요"))
                responses.setdefault("403", _error_response("권한 없음 또는 CSRF 실패"))
            if method in UNSAFE_METHODS:
                responses.setdefault("403", _error_response("권한 없음 또는 CSRF 실패"))
    return result
