"""클라이언트 로그 URL 설정."""
from django.urls import path

from .views import ClientLogListView

urlpatterns = [
    path("logs/", ClientLogListView.as_view(), name="log-list"),
]
