from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from accounts.permissions import is_admin
from labs.live import pc_payload
from labs.models import PC, Room


def _grid_columns(room: Room) -> str:
    if room.aisle_after:
        left = room.aisle_after
        right = room.cols - room.aisle_after
        return f"repeat({left}, minmax(0, 1fr)) 24px repeat({right}, minmax(0, 1fr))"
    return f"repeat({room.cols}, minmax(0, 1fr))"


def _cells(room: Room, by_seat: dict[tuple[int, int], dict]) -> list[dict]:
    cells: list[dict] = []
    for row in range(room.rows):
        for col in range(room.cols):
            cells.append(
                {"kind": "seat", "pc": by_seat.get((row, col)), "number": row * room.cols + col + 1}
            )
            if room.aisle_after and col + 1 == room.aisle_after:
                cells.append({"kind": "aisle"})
    return cells


def home(request: HttpRequest) -> HttpResponse:
    room = Room.objects.first()
    if room is None:
        return render(request, "web/empty.html", {"nav": "rooms"})
    return redirect("web:room", room_id=room.id)


def room_view(request: HttpRequest, room_id: int) -> HttpResponse:
    room = get_object_or_404(Room, pk=room_id)
    admin = is_admin(request.user)
    payloads = [pc_payload(pc, admin=admin) for pc in room.pcs.select_related("room")]
    by_seat = {(p["row"], p["col"]): p for p in payloads}
    context = {
        "nav": "rooms",
        "room": room,
        "rooms": Room.objects.all(),
        "cells": _cells(room, by_seat),
        "grid_columns": _grid_columns(room),
        "is_admin": admin,
        "online_count": sum(1 for p in payloads if p["state"] != "offline"),
        "total": len(payloads),
        "unassigned": PC.objects.filter(room__isnull=True) if admin else [],
    }
    return render(request, "web/room.html", context)
