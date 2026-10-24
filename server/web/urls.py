from django.urls import path

from web import views

app_name = "web"

urlpatterns = [
    path("", views.home, name="home"),
    path("rooms/<int:room_id>/", views.room_view, name="room"),
]
