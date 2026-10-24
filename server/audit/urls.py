from django.urls import path

from audit.views import AuditLogList

urlpatterns = [
    path("audit", AuditLogList.as_view()),
]
