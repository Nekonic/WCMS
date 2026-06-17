"""등록 토큰 URL 설정."""
from django.urls import path

from .views import EnrollmentTokenDeleteView, EnrollmentTokenListCreateView

urlpatterns = [
    path("tokens/", EnrollmentTokenListCreateView.as_view(), name="token-list-create"),
    path("tokens/<int:pk>/", EnrollmentTokenDeleteView.as_view(), name="token-delete"),
]
