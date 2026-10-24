from django.urls import path

from agent.views import RegisterView

urlpatterns = [
    path("register", RegisterView.as_view()),
]
