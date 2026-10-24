from django.urls import path

from labs import views

urlpatterns = [
    path("rooms", views.RoomList.as_view()),
    path("rooms/<int:pk>", views.RoomDetail.as_view()),
    path("rooms/<int:pk>/seats", views.RoomSeats.as_view()),
    path("pcs", views.PCList.as_view()),
    path("pcs/<int:pk>", views.PCDetail.as_view()),
    path("pins", views.PinList.as_view()),
    path("pins/<int:pk>", views.PinDetail.as_view()),
]
