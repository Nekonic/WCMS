from django.urls import path

from labs import views

app_name = "labs"

urlpatterns = [
    path("rooms/manage/", views.rooms_manage, name="rooms_manage"),
    path("rooms/<int:room_id>/edit/", views.room_edit, name="room_edit"),
    path("rooms/<int:room_id>/delete/", views.room_delete, name="room_delete"),
    path("pins/", views.pins, name="pins"),
    path("pins/<int:pin_id>/revoke/", views.pin_revoke, name="pin_revoke"),
]
