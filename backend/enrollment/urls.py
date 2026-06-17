"""등록 토큰 및 클라이언트 enrollment URL 설정."""
from django.urls import path

from .views import ClientEnrollView, EnrollmentTokenDeleteView, EnrollmentTokenListCreateView

urlpatterns = [
    path("tokens/", EnrollmentTokenListCreateView.as_view(), name="token-list-create"),
    path("tokens/<int:pk>/", EnrollmentTokenDeleteView.as_view(), name="token-delete"),
    path("client/enroll/", ClientEnrollView.as_view(), name="client-enroll"),
]
