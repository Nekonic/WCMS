from django.contrib import admin

from .models import Command


@admin.register(Command)
class CommandAdmin(admin.ModelAdmin):
    list_display = (
        "id", "command_type", "client", "status", "delivery_mode",
        "priority", "issuer", "created_at",
    )
    list_filter = ("status", "delivery_mode", "command_type")
    search_fields = ("command_type", "client__hostname")
    readonly_fields = ("created_at", "sent_at", "started_at", "completed_at")
