import pytest
from django.contrib.auth import get_user_model
from django.http import Http404
from django.middleware.csrf import get_token
from django.test import RequestFactory
from django.urls import path
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.test import APIClient
from rest_framework.views import APIView

from wcms.api import CSRF_FAILED_DETAIL, ApiError

pytestmark = pytest.mark.urls("tests.test_api_contract")


class NameSerializer(serializers.Serializer):
    name = serializers.CharField()


class AdminView(APIView):
    def get(self, request):
        return Response({"ok": True})

    def post(self, request):
        return Response({"ok": True})


class BoomView(APIView):
    def get(self, request):
        raise ApiError("boom", "x", 409)


class InvalidView(APIView):
    def post(self, request):
        serializer = NameSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({"ok": True})


class MissingView(APIView):
    def get(self, request):
        raise Http404


urlpatterns = [
    path("contract/admin", AdminView.as_view()),
    path("contract/boom", BoomView.as_view()),
    path("contract/invalid", InvalidView.as_view()),
    path("contract/missing", MissingView.as_view()),
]


def test_unauthenticated_is_401_with_challenge(api):
    response = api.get("/contract/admin")
    assert response.status_code == 401
    assert response.json()["error"] == "not_authenticated"
    assert response["WWW-Authenticate"] == "Session"


def test_logged_in_non_staff_is_403(db, api):
    user = get_user_model().objects.create_user("regular")
    api.force_login(user)
    response = api.get("/contract/admin")
    assert response.status_code == 403
    assert response.json()["error"] == "permission_denied"


def test_admin_is_200(admin_api):
    response = admin_api.get("/contract/admin")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_api_error_is_custom_code_and_status(admin_api):
    response = admin_api.get("/contract/boom")
    assert response.status_code == 409
    assert response.json() == {"error": "boom", "detail": "x"}


def test_validation_error_is_invalid_with_fields(admin_api):
    response = admin_api.post("/contract/invalid", {}, format="json")
    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "invalid"
    assert body["detail"] == "입력값을 확인하세요."
    assert "name" in body["fields"]


def test_http404_is_not_found_json(admin_api):
    response = admin_api.get("/contract/missing")
    assert response.status_code == 404
    assert response.json()["error"] == "not_found"


def test_wrong_method_is_405(admin_api):
    response = admin_api.post("/contract/boom", {}, format="json")
    assert response.status_code == 405
    assert response.json()["error"] == "method_not_allowed"


def test_session_post_without_csrf_token_is_csrf_failed(admin_user):
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(admin_user)
    response = client.post("/contract/admin", {}, format="json")
    assert response.status_code == 403
    assert response.json() == {"error": "csrf_failed", "detail": CSRF_FAILED_DETAIL}


def test_session_post_with_matching_csrf_token_is_200(admin_user):
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(admin_user)
    request = RequestFactory().get("/")
    token = get_token(request)
    client.cookies["csrftoken"] = request.META["CSRF_COOKIE"]
    response = client.post("/contract/admin", {}, format="json", HTTP_X_CSRFTOKEN=token)
    assert response.status_code == 200
    assert response.json() == {"ok": True}
