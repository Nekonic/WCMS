import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

PASSWORD = "correct-horse-battery-9"


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api() -> APIClient:
    return APIClient()


@pytest.fixture
def admin_user(db):
    return get_user_model().objects.create_user("admin", password=PASSWORD, is_staff=True)


@pytest.fixture
def admin_api(admin_user) -> APIClient:
    client = APIClient()
    client.force_login(admin_user)
    return client
