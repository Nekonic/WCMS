import requests
import json

SERVER_URL = "http://localhost:5050"


def test_register():
    """등록 테스트"""
    data = {
        "machine_id": "TEST-001",
        "hostname": "PC-TEST",
        "room_name": "1실습실",
        "seat_number": 99
    }

    try:
        response = requests.post(f"{SERVER_URL}/api/client/register", json=data)
        print(f"[등록] 상태코드: {response.status_code}")
        print(f"[등록] 응답: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"[등록] 오류: {e}")
        return False


def test_heartbeat():
    """Heartbeat 테스트"""
    data = {
        "machine_id": "TEST-001",
        "system_info": {
            "cpu_model": "Intel i5-10400",
            "cpu_cores": 6,
            "cpu_threads": 12,
            "cpu_usage": 45.2,
            "ram_total": 8192,
            "ram_used": 4096,
            "ram_usage_percent": 50.0,
            "ram_type": "DDR4",
            "disk_info": '{"C:": {"total": 500, "used": 250, "type": "SSD"}}',
            "os_edition": "Windows 10 Pro",
            "os_version": "22H2",
            "os_build": "19045",
            "os_activated": True,
            "ip_address": "192.168.1.99",
            "mac_address": "AA:BB:CC:DD:EE:99",
            "gpu_model": "NVIDIA GTX 1650",
            "gpu_vram": 4096,
            "current_user": "test_user",
            "uptime": 3600
        }
    }

    try:
        response = requests.post(f"{SERVER_URL}/api/client/heartbeat", json=data)
        print(f"[Heartbeat] 상태코드: {response.status_code}")
        print(f"[Heartbeat] 응답: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"[Heartbeat] 오류: {e}")
        return False


def test_get_command():
    """명령 확인 테스트"""
    try:
        response = requests.get(f"{SERVER_URL}/api/client/command?machine_id=TEST-001")
        print(f"[명령확인] 상태코드: {response.status_code}")
        print(f"[명령확인] 응답: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"[명령확인] 오류: {e}")
        return False


if __name__ == "__main__":
    print("=== 서버-클라이언트 API 통신 테스트 ===\n")

    print("1. 등록 테스트")
    if test_register():
        print("✅ 등록 성공\n")
    else:
        print("❌ 등록 실패\n")

    print("2. Heartbeat 테스트")
    if test_heartbeat():
        print("✅ Heartbeat 성공\n")
    else:
        print("❌ Heartbeat 실패\n")

    print("3. 명령 확인 테스트")
    if test_get_command():
        print("✅ 명령 확인 성공\n")
    else:
        print("❌ 명령 확인 실패\n")

    print("=== 테스트 완료 ===")
