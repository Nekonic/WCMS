"""비로그인 요청이 /api/ 전체에서 막히는지 실제 URLconf를 돌며 확인한다.

허용 목록은 일부러 리터럴로 둔다. 비로그인 경로를 추가하려면 여기를 같이 고쳐야 한다.
"""

import re

import pytest
import yaml
from django.core.management import call_command
from django.urls import URLPattern, URLResolver, get_resolver
from django.urls.resolvers import RoutePattern
from rest_framework.test import APIClient

from wcms.api import api_not_found

ANONYMOUS_ALLOWED = {
    ("GET", "/api/auth/me"),
    ("POST", "/api/auth/login"),
    ("POST", "/api/auth/otp"),
    ("POST", "/api/auth/logout"),
    ("GET", "/api/auth/enroll/{token}"),
    ("POST", "/api/auth/enroll/{token}"),
    ("GET", "/api/public/rooms"),
    ("GET", "/api/public/rooms/{id}"),
}
METHODS = ("get", "post", "put", "patch", "delete")
SAMPLE = {"int": "1", "str": "x", "slug": "x", "path": "x", "uuid": "00000000-0000-0000-0000-000000000000"}
PARAM = re.compile(r"<(?:(\w+):)?(\w+)>")


def _walk(patterns, prefix: str = ""):
    for entry in patterns:
        if isinstance(entry, URLResolver):
            yield from _walk(entry.url_patterns, prefix + str(entry.pattern))
        elif isinstance(entry, URLPattern):
            yield prefix + str(entry.pattern), entry


def api_routes() -> list[tuple[str, type]]:
    routes = []
    for route, entry in _walk(get_resolver().url_patterns):
        if not route.startswith("api/"):
            continue
        if entry.callback is api_not_found:
            continue
        assert isinstance(entry.pattern, RoutePattern), f"/{route}: path()로 등록해야 이 테스트가 확인할 수 있다"
        view = getattr(entry.callback, "cls", None)
        assert view is not None, f"/{route}: DRF 뷰가 아니다"
        routes.append(("/" + route, view))
    return routes


def schema_path(route: str) -> str:
    """URLconf 경로를 OpenAPI 경로 형식으로. drf-spectacular는 pk를 id로 바꾼다."""
    return PARAM.sub(lambda m: "{" + ("id" if m.group(2) == "pk" else m.group(2)) + "}", route)


def concrete_path(route: str) -> str:
    return PARAM.sub(lambda m: SAMPLE[m.group(1) or "str"], route)


def operations() -> list[tuple[str, str, str]]:
    ops = []
    for route, view in api_routes():
        for method in METHODS:
            if hasattr(view, method):
                ops.append((method.upper(), schema_path(route), concrete_path(route)))
    return ops


def test_routes_found():
    found = {(method, path) for method, path, _ in operations()}
    assert ANONYMOUS_ALLOWED <= found
    assert ("GET", "/api/rooms") in found and ("DELETE", "/api/admins/{id}") in found


@pytest.mark.django_db
@pytest.mark.parametrize("method,path,url", operations())
def test_anonymous_request_is_rejected(method, path, url):
    if (method, path) in ANONYMOUS_ALLOWED:
        pytest.skip("비로그인 허용")
    # 실제 브라우저처럼 CSRF를 검사한다. 비로그인 요청은 DRF가 CSRF를 검사하지 않으므로 401이 먼저다.
    client = APIClient(enforce_csrf_checks=True)
    response = getattr(client, method.lower())(url, data={}, format="json")
    assert response.status_code == 401, response.content
    assert response["Content-Type"] == "application/json"
    assert response.json()["error"] == "not_authenticated"


@pytest.mark.django_db
@pytest.mark.parametrize("route", [route for route, _ in api_routes()])
def test_anonymous_options_is_rejected(route):
    if any(path == schema_path(route) for _, path in ANONYMOUS_ALLOWED):
        pytest.skip("비로그인 허용 경로")
    response = APIClient(enforce_csrf_checks=True).options(concrete_path(route))
    assert response.status_code == 401
    assert response.json()["error"] == "not_authenticated"


def test_schema_anonymous_operations_match_allowlist(tmp_path):
    target = tmp_path / "openapi.yaml"
    call_command("spectacular", "--file", str(target))
    schema = yaml.safe_load(target.read_text(encoding="utf-8"))
    anonymous = {
        (method.upper(), path)
        for path, item in schema["paths"].items()
        for method, operation in item.items()
        if isinstance(operation, dict) and {} in operation.get("security", [])
    }
    assert anonymous == ANONYMOUS_ALLOWED
    documented = {(method.upper(), path) for path, item in schema["paths"].items() for method in item}
    assert documented == {(method, path) for method, path, _ in operations()}
