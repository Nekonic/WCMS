from django.urls import path

from live import views

urlpatterns = [
    path("public/rooms", views.PublicRoomList.as_view()),
    path("public/rooms/<int:pk>", views.PublicRoomDetail.as_view()),
    path("rooms/<int:pk>/pcs", views.RoomLivePCs.as_view()),
    path("pcs/<int:pk>/live", views.PCLive.as_view()),
]
