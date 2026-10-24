from django.urls import path

from wcms.views import healthz

urlpatterns = [
    path("healthz", healthz),
]
