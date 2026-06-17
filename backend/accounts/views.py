"""관리자 인증 API (세션 기반, 설계 4.2).

SPA 흐름: GET /csrf 로 csrftoken 쿠키 수령 -> POST /login -> 이후 unsafe 요청에
X-CSRFToken 헤더 동봉. 클라이언트(PC) 인증서 스킴과 완전히 분리된다.
"""
from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


def _user_payload(user):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_superuser": user.is_superuser,
    }


class CSRFView(APIView):
    """csrftoken 쿠키를 발급하고 토큰 값을 반환한다."""
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"csrfToken": get_token(request)})


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        if not username or not password:
            return Response({"detail": "username과 password가 필요합니다"}, status=400)
        user = authenticate(request, username=username, password=password)
        if user is None or not user.is_active:
            return Response({"detail": "아이디 또는 비밀번호가 올바르지 않습니다"}, status=401)
        login(request, user)
        return Response(_user_payload(user))


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response(status=204)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(_user_payload(request.user))
