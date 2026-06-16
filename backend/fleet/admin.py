from django.contrib import admin

from .models import (
    Client,
    ClientDynamicInfo,
    ClientSpecs,
    ClientVersion,
    NetworkEvent,
    Room,
    Seat,
)


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("hostname", "id", "status", "room", "is_online", "is_verified", "last_seen")
    list_filter = ("status", "is_online", "is_verified", "room")
    search_fields = ("hostname", "id", "legacy_machine_id", "mac_address")


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("name", "rows", "cols", "is_active")


@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ("room", "row", "col", "client")
    list_filter = ("room",)


@admin.register(ClientVersion)
class ClientVersionAdmin(admin.ModelAdmin):
    list_display = ("version", "released_at", "download_url")


admin.site.register(ClientSpecs)
admin.site.register(ClientDynamicInfo)
admin.site.register(NetworkEvent)
