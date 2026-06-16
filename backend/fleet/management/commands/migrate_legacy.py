"""레거시 SQLite(Flask v0.9.x) -> 새 Django 스키마 데이터 이관.

    python manage.py migrate_legacy /path/to/legacy.sqlite3 [--clear]

신원 모델 전환: 레거시 pc_info(machine_id) -> Client(UUID + legacy_machine_id).
인증서는 재enrollment 시 발급되므로 이관분은 certificate_pem=null. 관리자 비밀번호는
해셔가 달라 이관하지 않고 set_unusable_password() 로 둔다(재설정/superuser 생성 필요).
"""
import ipaddress
import json
import sqlite3
from datetime import timezone as dt_timezone

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from commands.models import Command as CommandModel
from enrollment.models import EnrollmentToken
from fleet.models import (
    Client,
    ClientDynamicInfo,
    ClientSpecs,
    ClientVersion,
    NetworkEvent,
    Room,
    Seat,
)

User = get_user_model()

# 시간 민감 명령은 drop, 그 외 queue (설계 4.4).
_DROP_TYPES = {"shutdown", "restart", "reboot", "message", "kill_process", "execute"}


def _json(val, default):
    if val in (None, ""):
        return default
    if isinstance(val, (dict, list)):
        return val
    try:
        return json.loads(val)
    except (ValueError, TypeError):
        return default


def _dt(val):
    """레거시 'YYYY-MM-DD HH:MM:SS'(UTC) -> aware datetime."""
    if not val:
        return None
    parsed = parse_datetime(val.replace(" ", "T")) if isinstance(val, str) else val
    if parsed and timezone.is_naive(parsed):
        return timezone.make_aware(parsed, dt_timezone.utc)
    return parsed


def _ip(val):
    if not val:
        return None
    try:
        ipaddress.ip_address(val)
        return val
    except ValueError:
        return None


class Command(BaseCommand):
    help = "레거시 SQLite 데이터를 새 Django 스키마로 이관한다."

    def add_arguments(self, parser):
        parser.add_argument("sqlite_path")
        parser.add_argument("--clear", action="store_true", help="이관 전 기존 데이터 삭제")

    @transaction.atomic
    def handle(self, *args, **opts):
        conn = sqlite3.connect(opts["sqlite_path"])
        conn.row_factory = sqlite3.Row
        try:
            if opts["clear"]:
                self._clear()
            self._run(conn)
        finally:
            conn.close()

    def _clear(self):
        for model in (CommandModel, NetworkEvent, Seat, ClientDynamicInfo,
                      ClientSpecs, Client, ClientVersion, EnrollmentToken, Room):
            model.objects.all().delete()
        self.stdout.write("기존 데이터 삭제 완료 (users 제외)")

    def _run(self, conn):
        users = self._migrate_admins(conn)
        rooms = self._migrate_rooms(conn)
        self._migrate_tokens(conn)
        clients = self._migrate_clients(conn, rooms)
        self._migrate_specs(conn, clients)
        self._migrate_dynamic(conn, clients)
        self._migrate_seats(conn, rooms, clients)
        self._migrate_commands(conn, clients, users)
        self._migrate_network_events(conn, clients)
        self._migrate_versions(conn)
        self.stdout.write(self.style.SUCCESS(
            f"이관 완료: clients={len(clients)} rooms={len(rooms)} users={len(users)}"
        ))

    def _migrate_admins(self, conn):
        by_name = {}
        for row in conn.execute("SELECT * FROM admins"):
            user, _ = User.objects.get_or_create(
                username=row["username"],
                defaults={
                    "email": row["email"] or "",
                    "is_active": bool(row["is_active"]),
                    "is_staff": True,
                    "is_superuser": True,
                },
            )
            user.set_unusable_password()
            user.save(update_fields=["password"])
            by_name[row["username"]] = user
        return by_name

    def _migrate_rooms(self, conn):
        by_name = {}
        for row in conn.execute("SELECT * FROM seat_layout"):
            room, _ = Room.objects.get_or_create(
                name=row["room_name"],
                defaults={
                    "rows": row["rows"],
                    "cols": row["cols"],
                    "description": row["description"] or "",
                    "is_active": bool(row["is_active"]),
                },
            )
            by_name[row["room_name"]] = room
        return by_name

    def _migrate_tokens(self, conn):
        for row in conn.execute("SELECT * FROM pc_registration_tokens"):
            token, created = EnrollmentToken.objects.get_or_create(
                token=row["token"],
                defaults={
                    "usage_type": row["usage_type"],
                    "expires_in": row["expires_in"],
                    "is_expired": bool(row["is_expired"]),
                    "used_count": row["used_count"],
                    "created_by": row["created_by"],
                    "expires_at": _dt(row["expires_at"]),
                },
            )
            if created and row["created_at"]:
                EnrollmentToken.objects.filter(pk=token.pk).update(
                    created_at=_dt(row["created_at"]))

    def _migrate_clients(self, conn, rooms):
        by_pcid = {}
        for row in conn.execute("SELECT * FROM pc_info"):
            room = rooms.get(row["room_name"]) if row["room_name"] else None
            if row["room_name"] and room is None:
                room, _ = Room.objects.get_or_create(name=row["room_name"])
                rooms[row["room_name"]] = room
            client = Client.objects.create(
                legacy_machine_id=row["machine_id"],
                hostname=row["hostname"],
                mac_address=row["mac_address"] or "",
                room=room,
                ip_address=_ip(row["ip_address"]),
                is_online=bool(row["is_online"]),
                last_seen=_dt(row["last_seen"]),
                is_verified=bool(row["is_verified"]),
            )
            if row["created_at"]:
                Client.objects.filter(pk=client.pk).update(
                    enrolled_at=_dt(row["created_at"]))
            by_pcid[row["id"]] = client
        return by_pcid

    def _migrate_specs(self, conn, clients):
        for row in conn.execute("SELECT * FROM pc_specs"):
            client = clients.get(row["pc_id"])
            if client is None:
                continue
            ClientSpecs.objects.update_or_create(
                client=client,
                defaults={
                    "cpu_model": row["cpu_model"],
                    "cpu_cores": row["cpu_cores"],
                    "cpu_threads": row["cpu_threads"],
                    "ram_total": row["ram_total"],
                    "disk_info": _json(row["disk_info"], {}),
                    "os_edition": row["os_edition"],
                    "os_version": row["os_version"],
                },
            )

    def _migrate_dynamic(self, conn, clients):
        for row in conn.execute("SELECT * FROM pc_dynamic_info"):
            client = clients.get(row["pc_id"])
            if client is None:
                continue
            ClientDynamicInfo.objects.update_or_create(
                client=client,
                defaults={
                    "cpu_usage": row["cpu_usage"],
                    "ram_used": row["ram_used"],
                    "ram_usage_percent": row["ram_usage_percent"],
                    "disk_usage": _json(row["disk_usage"], None),
                    "current_user": row["current_user"],
                    "uptime": row["uptime"],
                    "processes": _json(row["processes"], None),
                },
            )

    def _migrate_seats(self, conn, rooms, clients):
        for row in conn.execute("SELECT * FROM seat_map"):
            room = rooms.get(row["room_name"])
            if room is None:
                continue
            Seat.objects.update_or_create(
                room=room, row=row["row"], col=row["col"],
                defaults={"client": clients.get(row["pc_id"])},
            )

    def _migrate_commands(self, conn, clients, users):
        for row in conn.execute("SELECT * FROM commands"):
            client = clients.get(row["pc_id"])
            if client is None:
                continue
            ctype = row["command_type"]
            mode = (CommandModel.DeliveryMode.DROP_IF_OFFLINE
                    if ctype in _DROP_TYPES else CommandModel.DeliveryMode.QUEUE)
            cmd = CommandModel.objects.create(
                client=client,
                issuer=users.get(row["admin_username"]),
                command_type=ctype,
                parameters=_json(row["command_data"], {}),
                priority=row["priority"],
                delivery_mode=mode,
                status=row["status"],
                result=row["result"],
                error_message=row["error_message"],
                timeout_seconds=row["timeout_seconds"],
                started_at=_dt(row["started_at"]),
                completed_at=_dt(row["completed_at"]),
            )
            if row["created_at"]:
                CommandModel.objects.filter(pk=cmd.pk).update(
                    created_at=_dt(row["created_at"]))

    def _migrate_network_events(self, conn, clients):
        for row in conn.execute("SELECT * FROM network_events"):
            client = clients.get(row["pc_id"])
            if client is None:
                continue
            NetworkEvent.objects.create(
                client=client,
                offline_at=_dt(row["offline_at"]),
                online_at=_dt(row["online_at"]),
                duration_sec=row["duration_sec"],
                reason=row["reason"],
            )

    def _migrate_versions(self, conn):
        for row in conn.execute("SELECT * FROM client_versions"):
            ClientVersion.objects.create(
                version=row["version"],
                download_url=row["download_url"],
                changelog=row["changelog"] or "",
                released_at=_dt(row["released_at"]) or timezone.now(),
            )
