from django.urls import include, path

urlpatterns = [
    path("", include("accounts.urls")),
    path("", include("labs.urls")),
    path("", include("live.urls")),
    path("", include("audit.urls")),
]
