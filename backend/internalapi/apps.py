"""internalapi 앱 설정."""
from django.apps import AppConfig


class InternalApiConfig(AppConfig):
    """게이트웨이-Django 내부 API 앱."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "internalapi"
