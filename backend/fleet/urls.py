from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ClientVersionViewSet, ClientViewSet, RoomViewSet, SeatLayoutView

router = DefaultRouter()
router.register(r"pcs", ClientViewSet, basename="pc")
router.register(r"rooms", RoomViewSet, basename="room")
router.register(r"versions", ClientVersionViewSet, basename="version")

urlpatterns = router.urls + [
    path("rooms/<str:room_name>/layout/", SeatLayoutView.as_view(), name="room-layout"),
]
