from django.urls import include, path

from wcms.views import healthz

urlpatterns = [
    path("healthz", healthz),
    path("client/", include("clientapi.urls")),
    path("", include("accounts.urls")),
    path("", include("web.urls")),
]
