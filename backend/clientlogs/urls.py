"""클라이언트 로그 URL 설정."""
from django.urls import path

from .views import ClientLogListView, LogBatchUploadView

urlpatterns = [
    path("logs/", ClientLogListView.as_view(), name="log-list"),
    # 클라이언트(PC) 인증서 인증 후 로그 배치 업로드 (설계 4.3)
    # 전체 경로: POST /api/client/logs/  (config/urls.py 에서 "api/" 접두사로 마운트)
    path("client/logs/", LogBatchUploadView.as_view(), name="client-log-upload"),
]
