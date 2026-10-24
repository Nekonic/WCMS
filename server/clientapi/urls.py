from django.urls import path

from clientapi import views

app_name = "clientapi"

urlpatterns = [
    path("register", views.register, name="register"),
]
