"""레거시 SQLite -> Django 데이터 이관(migrate_legacy) 검증.

레거시 schema.sql 로 픽스처 DB 를 만들고 샘플 데이터를 넣은 뒤, 명령을 실행해
각 엔티티가 새 스키마로 올바르게 매핑되는지 확인한다.
"""
import sqlite3
from pathlib import Path

import pytest
from django.core.management import call_command

from commands.models import Command
from enrollment.models import EnrollmentToken
from fleet.models import Client, NetworkEvent, Room, Seat

REPO_ROOT = Path(__file__).resolve().parents[2]
LEGACY_SCHEMA = REPO_ROOT / "server" / "migrations" / "schema.sql"


def _build_legacy_db(path):
    conn = sqlite3.connect(path)
    conn.executescript(LEGACY_SCHEMA.read_text(encoding="utf-8"))
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO admins (username, password_hash, email, is_active) VALUES (?,?,?,?)",
        ("admin", "$2b$12$abc", "a@x.local", 1),
    )
    cur.execute(
        "INSERT INTO pc_registration_tokens (token, usage_type, expires_in, used_count, created_by, expires_at) "
        "VALUES (?,?,?,?,?,?)",
        ("123456", "single", 600, 0, "admin", "2030-01-01 00:00:00"),
    )
    cur.execute(
        "INSERT INTO pc_info (machine_id, hostname, mac_address, room_name, seat_number, ip_address, "
        "is_online, is_verified, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
        ("MID-1", "PC-1", "AA:BB:CC:DD:EE:01", "1실습실", "2, 3", "10.0.0.5", 1, 1, "2025-01-01 10:00:00"),
    )
    pc_id = cur.lastrowid
    cur.execute(
        "INSERT INTO pc_specs (pc_id, cpu_model, cpu_cores, cpu_threads, ram_total, disk_info, "
        "os_edition, os_version) VALUES (?,?,?,?,?,?,?,?)",
        (pc_id, "i5", 4, 8, 16.0, '{"C:": {"total_gb": 237.0}}', "Win11 Pro", "23H2"),
    )
    cur.execute(
        "INSERT INTO pc_dynamic_info (pc_id, cpu_usage, ram_used, ram_usage_percent, disk_usage, "
        "current_user, uptime, processes) VALUES (?,?,?,?,?,?,?,?)",
        (pc_id, 12.5, 6.0, 40.0, '{"C:": {"used_gb": 107.2}}', "student", 3600, '["chrome.exe"]'),
    )
    cur.execute(
        "INSERT INTO commands (pc_id, admin_username, command_type, command_data, priority, status, "
        "timeout_seconds, created_at) VALUES (?,?,?,?,?,?,?,?)",
        (pc_id, "admin", "shutdown", '{"delay": 0}', 5, "completed", 300, "2025-01-02 11:00:00"),
    )
    cur.execute(
        "INSERT INTO seat_map (room_name, row, col, pc_id) VALUES (?,?,?,?)",
        ("1실습실", 2, 3, pc_id),
    )
    cur.execute(
        "INSERT INTO network_events (pc_id, offline_at, online_at, duration_sec, reason) VALUES (?,?,?,?,?)",
        (pc_id, "2025-01-03 09:00:00", "2025-01-03 09:05:00", 300, "shutdown"),
    )
    cur.execute(
        "INSERT INTO client_versions (version, download_url, changelog) VALUES (?,?,?)",
        ("0.9.8", "https://example.invalid/c.exe", "rel"),
    )
    conn.commit()
    conn.close()


@pytest.mark.django_db
def test_migrate_legacy_imports_all_entities(tmp_path):
    legacy = tmp_path / "legacy.sqlite3"
    _build_legacy_db(str(legacy))

    call_command("migrate_legacy", str(legacy))

    client = Client.objects.get(legacy_machine_id="MID-1")
    assert client.hostname == "PC-1"
    assert client.room.name == "1실습실"
    assert client.is_online is True
    assert str(client.ip_address) == "10.0.0.5"
    assert client.enrolled_at.year == 2025  # 레거시 created_at 보존

    assert client.specs.cpu_model == "i5"
    assert client.specs.disk_info == {"C:": {"total_gb": 237.0}}
    assert client.dynamic.processes == ["chrome.exe"]
    assert client.dynamic.current_user == "student"

    assert Room.objects.filter(name="1실습실").exists()
    assert EnrollmentToken.objects.get(token="123456").usage_type == "single"

    cmd = Command.objects.get(client=client)
    assert cmd.command_type == "shutdown"
    assert cmd.parameters == {"delay": 0}
    assert cmd.status == "completed"
    assert cmd.delivery_mode == Command.DeliveryMode.DROP_IF_OFFLINE
    assert cmd.issuer.username == "admin"

    seat = Seat.objects.get(room__name="1실습실", row=2, col=3)
    assert seat.client_id == client.id

    assert NetworkEvent.objects.filter(client=client, reason="shutdown").count() == 1


@pytest.mark.django_db
def test_migrate_legacy_clear_is_rerunnable(tmp_path):
    legacy = tmp_path / "legacy.sqlite3"
    _build_legacy_db(str(legacy))
    call_command("migrate_legacy", str(legacy))
    call_command("migrate_legacy", str(legacy), "--clear")
    assert Client.objects.filter(legacy_machine_id="MID-1").count() == 1
