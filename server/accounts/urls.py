from django.urls import path

from accounts import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("login/otp/", views.otp_view, name="otp"),
    path("login/otp/setup/", views.otp_setup_view, name="otp_setup"),
    path("logout/", views.logout_view, name="logout"),
]
