from django.contrib import admin

from .models import EnrollmentToken


@admin.register(EnrollmentToken)
class EnrollmentTokenAdmin(admin.ModelAdmin):
    list_display = ("token", "usage_type", "used_count", "is_expired", "expires_at", "created_by")
    list_filter = ("usage_type", "is_expired")
    search_fields = ("token", "created_by")
