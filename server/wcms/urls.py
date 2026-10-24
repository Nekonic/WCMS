from django.urls import include, path, re_path

from wcms.api import api_not_found
from wcms.views import healthz

urlpatterns = [
    path("healthz", healthz),
    path("api/", include("wcms.api_urls")),
    re_path(r"^api/", api_not_found),
    path("client/", include("agent.urls")),
]
