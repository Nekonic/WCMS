from django.db import transaction
from django.http import HttpRequest, HttpResponse, QueryDict
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.permissions import admin_required
from labs.forms import PinForm, RoomForm
from labs.models import PC, RegistrationPin, Room

Seat = tuple[int, int]


def _parse_seats(post: QueryDict, rows: int, cols: int) -> tuple[dict[Seat, int], str]:
    assignments: dict[Seat, int] = {}
    seen: set[int] = set()
    for row in range(rows):
        for col in range(cols):
            raw = post.get(f"seat-{row}-{col}", "")
            if not raw:
                continue
            if not raw.isdigit():
                return {}, "잘못된 PC 선택입니다."
            pc_id = int(raw)
            if pc_id in seen:
                return {}, "같은 PC를 두 자리에 배치할 수 없습니다."
            seen.add(pc_id)
            assignments[(row, col)] = pc_id
    if seen and PC.objects.filter(pk__in=seen).count() != len(seen):
        return {}, "존재하지 않는 PC입니다."
    return assignments, ""


def _seat_rows(rows: int, cols: int, current: dict[Seat, int]) -> list[list[dict]]:
    return [
        [
            {
                "name": f"seat-{row}-{col}",
                "number": row * cols + col + 1,
                "current": current.get((row, col)),
            }
            for col in range(cols)
        ]
        for row in range(rows)
    ]


@admin_required
def rooms_manage(request: HttpRequest) -> HttpResponse:
    form = RoomForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        room = form.save()
        return redirect("labs:room_edit", room_id=room.id)
    return render(
        request, "labs/rooms_manage.html", {"nav": "manage", "rooms": Room.objects.all(), "form": form}
    )


@admin_required
def room_edit(request: HttpRequest, room_id: int) -> HttpResponse:
    room = get_object_or_404(Room, pk=room_id)
    form = RoomForm(request.POST or None, instance=room)
    seat_error = ""
    current = {(pc.row, pc.col): pc.id for pc in room.pcs.all()}
    rows, cols = room.rows, room.cols

    if request.method == "POST" and form.is_valid():
        rows, cols = form.cleaned_data["rows"], form.cleaned_data["cols"]
        assignments, seat_error = _parse_seats(request.POST, rows, cols)
        if not seat_error:
            with transaction.atomic():
                room = form.save()
                PC.objects.filter(room=room).update(room=None, row=None, col=None)
                for (row, col), pc_id in assignments.items():
                    PC.objects.filter(pk=pc_id).update(room=room, row=row, col=col)
            return redirect("labs:room_edit", room_id=room.id)
        current = {}
        for row in range(rows):
            for col in range(cols):
                value = request.POST.get(f"seat-{row}-{col}", "")
                if value.isdigit():
                    current[(row, col)] = int(value)

    pcs = PC.objects.select_related("room").order_by("hostname")
    context = {
        "nav": "manage",
        "room": room,
        "form": form,
        "seat_error": seat_error,
        "seat_rows": _seat_rows(rows, cols, current),
        "pc_choices": [{"id": pc.id, "text": f"{pc.hostname} ({pc.label})"} for pc in pcs],
    }
    return render(request, "labs/room_edit.html", context)


@admin_required
@require_POST
def room_delete(request: HttpRequest, room_id: int) -> HttpResponse:
    room = get_object_or_404(Room, pk=room_id)
    with transaction.atomic():
        PC.objects.filter(room=room).update(room=None, row=None, col=None)
        room.delete()
    return redirect("labs:rooms_manage")


@admin_required
def pins(request: HttpRequest) -> HttpResponse:
    form = PinForm(request.POST or None)
    new_pin = None
    if request.method == "POST" and form.is_valid():
        new_pin = RegistrationPin.issue(
            user=request.user,
            multi_use=form.cleaned_data["multi_use"],
            minutes=form.cleaned_data["minutes"],
        )
        form = PinForm()
    now = timezone.now()
    active = [
        pin
        for pin in RegistrationPin.objects.filter(revoked=False, expires_at__gt=now).order_by("-created_at")
        if pin.is_usable(now)
    ]
    return render(
        request, "labs/pins.html", {"nav": "pins", "form": form, "new_pin": new_pin, "pins": active}
    )


@admin_required
@require_POST
def pin_revoke(request: HttpRequest, pin_id: int) -> HttpResponse:
    RegistrationPin.objects.filter(pk=pin_id).update(revoked=True)
    return redirect("labs:pins")
