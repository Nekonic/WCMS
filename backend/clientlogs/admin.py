from django.contrib import admin

from .models import ClientLog


@admin.register(ClientLog)
class ClientLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "level", "client", "source", "message")
    list_filter = ("level",)
    search_fields = ("message", "source", "client__hostname")
    readonly_fields = ("created_at",)
