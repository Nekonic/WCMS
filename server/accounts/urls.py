from django.urls import path

from accounts import views

urlpatterns = [
    path("auth/me", views.MeView.as_view()),
    path("auth/login", views.LoginView.as_view()),
    path("auth/otp", views.OtpView.as_view()),
    path("auth/logout", views.LogoutView.as_view()),
    path("auth/enroll/<str:token>", views.EnrollView.as_view()),
    path("admins", views.AdminListView.as_view()),
    path("admins/<int:pk>", views.AdminDetailView.as_view()),
    path("admins/<int:pk>/reset", views.AdminResetView.as_view()),
]
