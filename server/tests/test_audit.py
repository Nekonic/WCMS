import pytest
from django.contrib.auth.models import AnonymousUser

from audit.models import AuditLog
from audit.services import record

pytestmark = pytest.mark.django_db


def test_record_stores_actor_and_detail(admin_user):
    entry = record(admin_user, "room.create", "room:1", name="301")
    assert entry.actor == admin_user
    assert entry.detail == {"name": "301"}


def test_record_anonymous_actor_is_none():
    entry = record(AnonymousUser(), "admin.enrolled", "user:1")
    assert entry.actor is None


def test_list_requires_admin(api):
    assert api.get("/api/audit").status_code == 401


def test_list_is_newest_first_and_paginated(admin_api, admin_user):
    for n in range(55):
        record(admin_user, "test.action", f"t:{n}")
    first = admin_api.get("/api/audit").json()
    assert len(first["results"]) == 50
    assert first["results"][0]["target"] == "t:54"
    assert first["results"][0]["actor"] == "admin"
    assert first["next"]
    second = admin_api.get(first["next"]).json()
    assert len(second["results"]) == 5
    assert AuditLog.objects.count() == 55
