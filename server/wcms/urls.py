from django.urls import include, path, re_path

from wcms.api import api_not_found
from wcms.views import healthz

urlpatterns = [
    path("healthz", healthz),
    path("api/", include("wcms.api_urls")),
    re_path(r"^api(?:/|$)", api_not_found),
    path("client/", include("agent.urls")),
]

# 이 서버는 API, WebSocket, healthz만 내보내므로 처리하지 못한 예외는 어디서든 JSON 오류로 답한다
handler500 = "wcms.api.server_error"
