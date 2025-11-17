import requests
import time
import os

BASE_URL = os.environ.get("WCMS_BASE_URL", "http://127.0.0.1:5050")  # WCMS 기본 포트는 5050

class Colors:
    """터미널 색상 코드"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_success(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.END}")

def print_error(msg):
    print(f"{Colors.RED}✗ {msg}{Colors.END}")

def print_warning(msg):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.END}")

def print_info(msg):
    print(f"{Colors.BLUE}ℹ {msg}{Colors.END}")

# ==================== 공통 API 테스트 ====================

def test_dashboard_access():
    """메인 대시보드 접근 테스트"""
    print("\n--- 1. Dashboard Access (GET /) ---")
    try:
        response = requests.get(f"{BASE_URL}/", params={"room": "1실습실"}, timeout=5)
        if response.status_code == 200:
            print_success(f"대시보드 접근 성공 (Status: {response.status_code})")
            return True
        else:
            print_error(f"대시보드 접근 실패 (Status: {response.status_code})")
            return False
    except requests.exceptions.RequestException as e:
        print_error(f"서버 연결 실패: {e}")
        return False

def test_login():
    """관리자 로그인 테스트"""
    print("\n--- 2. Admin Login (POST /login) ---")
    session = requests.Session()

    try:
        # 로그인 시도
        response = session.post(
            f"{BASE_URL}/login",
            data={"username": "admin", "password": "admin"},
            timeout=5,
            allow_redirects=False
        )

        if response.status_code in [200, 302]:
            print_success("로그인 성공")
            return session
        else:
            print_error(f"로그인 실패 (Status: {response.status_code})")
            return None
    except requests.exceptions.RequestException as e:
        print_error(f"로그인 요청 실패: {e}")
        return None

# ==================== 관리자 API 테스트 ====================

def test_pc_list(session):
    """PC 목록 조회 테스트"""
    print("\n--- 3. PC List (GET /api/pcs) ---")
    try:
        response = session.get(f"{BASE_URL}/api/pcs", timeout=5)
        if response.status_code == 200:
            pcs = response.json()
            print_success(f"PC 목록 조회 성공 (총 {len(pcs)}대)")
            if pcs:
                print_info(f"첫 번째 PC: {pcs[0].get('hostname', 'Unknown')}")
            return pcs
        else:
            print_error(f"PC 목록 조회 실패 (Status: {response.status_code})")
            return []
    except requests.exceptions.RequestException as e:
        print_error(f"PC 목록 조회 오류: {e}")
        return []

def test_pc_detail(session, pc_id=1):
    """PC 상세 정보 조회 테스트"""
    print(f"\n--- 4. PC Detail (GET /api/pc/{pc_id}) ---")
    try:
        response = session.get(f"{BASE_URL}/api/pc/{pc_id}", timeout=5)
        if response.status_code == 200:
            pc = response.json()
            print_success(f"PC 상세 정보 조회 성공")
            print_info(f"호스트명: {pc.get('hostname', 'Unknown')}")
            print_info(f"온라인 상태: {pc.get('is_online', False)}")
            return pc
        elif response.status_code == 404:
            print_warning(f"PC ID {pc_id}를 찾을 수 없습니다")
            return None
        else:
            print_error(f"PC 상세 정보 조회 실패 (Status: {response.status_code})")
            return None
    except requests.exceptions.RequestException as e:
        print_error(f"PC 상세 정보 조회 오류: {e}")
        return None

def test_pc_history(session, pc_id=1):
    """PC 프로세스 기록 조회 테스트"""
    print(f"\n--- 5. PC Process History (GET /api/pc/{pc_id}/history) ---")
    try:
        response = session.get(f"{BASE_URL}/api/pc/{pc_id}/history", timeout=5)
        if response.status_code == 200:
            history = response.json()
            print_success(f"프로세스 기록 조회 성공 (총 {len(history)}개)")
            return history
        elif response.status_code == 401:
            print_error("인증 필요 - 로그인하지 않았습니다")
            return []
        else:
            print_error(f"프로세스 기록 조회 실패 (Status: {response.status_code})")
            return []
    except requests.exceptions.RequestException as e:
        print_error(f"프로세스 기록 조회 오류: {e}")
        return []

def test_send_command(session, pc_id=1, cmd_type="shutdown", cmd_data=None):
    """PC 명령 전송 테스트 (실제 실행 안 됨)"""
    print(f"\n--- 6. Send Command to PC (POST /api/pc/{pc_id}/command) ---")
    print_warning("주의: 실제 명령은 전송되지만 테스트용이므로 shutdown은 스킵합니다")

    if cmd_data is None:
        cmd_data = {}

    # 실제로 위험한 명령은 전송하지 않음
    if cmd_type in ["shutdown", "reboot"]:
        print_warning(f"{cmd_type} 명령은 테스트에서 스킵됩니다")
        return True

    try:
        response = session.post(
            f"{BASE_URL}/api/pc/{pc_id}/command",
            json={"type": cmd_type, "data": cmd_data},
            timeout=5
        )
        if response.status_code == 200:
            result = response.json()
            print_success(f"명령 전송 성공: {result.get('message')}")
            return True
        elif response.status_code == 401:
            print_error("인증 필요 - 로그인하지 않았습니다")
            return False
        elif response.status_code == 404:
            print_error(f"PC ID {pc_id}를 찾을 수 없습니다")
            return False
        else:
            print_error(f"명령 전송 실패 (Status: {response.status_code})")
            return False
    except requests.exceptions.RequestException as e:
        print_error(f"명령 전송 오류: {e}")
        return False

def test_layout_api(session, room_name="1실습실"):
    """좌석 배치 조회 테스트"""
    print(f"\n--- 7. Layout Map (GET /api/layout/map/{room_name}) ---")
    try:
        response = session.get(f"{BASE_URL}/api/layout/map/{room_name}", timeout=5)
        if response.status_code == 200:
            layout = response.json()
            print_success(f"좌석 배치 조회 성공")
            print_info(f"행: {layout.get('rows')}, 열: {layout.get('cols')}")
            print_info(f"배치된 좌석 수: {len(layout.get('seats', []))}")
            return layout
        else:
            print_error(f"좌석 배치 조회 실패 (Status: {response.status_code})")
            return None
    except requests.exceptions.RequestException as e:
        print_error(f"좌석 배치 조회 오류: {e}")
        return None

# ==================== 클라이언트 API 테스트 ====================

def test_client_register():
    """클라이언트 등록 테스트"""
    print("\n--- 8. Client Register (POST /api/client/register) ---")

    test_data = {
        "machine_id": "TEST_MACHINE_12345",
        "hostname": "TEST-PC-001",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "cpu_model": "Intel Core i7-9700K",
        "cpu_cores": 8,
        "cpu_threads": 8,
        "ram_total": 16384,
        "disk_info": '{"C:": {"total": 512000000000, "fstype": "NTFS"}}',
        "os_edition": "Windows 10 Pro",
        "os_version": "10.0.19045"
    }

    try:
        response = requests.post(
            f"{BASE_URL}/api/client/register",
            json=test_data,
            timeout=5
        )
        if response.status_code == 200:
            result = response.json()
            print_success(f"클라이언트 등록 성공: {result.get('message')}")
            return True
        elif response.status_code == 500:
            result = response.json()
            if "이미 등록된 PC" in result.get('message', ''):
                print_warning("이미 등록된 PC입니다 (정상)")
                return True
            else:
                print_error(f"등록 실패: {result.get('message')}")
                return False
        else:
            print_error(f"클라이언트 등록 실패 (Status: {response.status_code})")
            return False
    except requests.exceptions.RequestException as e:
        print_error(f"클라이언트 등록 오류: {e}")
        return False

def test_client_heartbeat():
    """클라이언트 하트비트 테스트"""
    print("\n--- 9. Client Heartbeat (POST /api/client/heartbeat) ---")

    test_data = {
        "machine_id": "TEST_MACHINE_12345",
        "system_info": {
            "cpu_usage": 45.5,
            "ram_used": 8192,
            "ram_usage_percent": 50.0,
            "disk_usage": '{"C:": {"used": 256000000000, "free": 256000000000, "percent": 50.0}}',
            "ip_address": "192.168.1.100",
            "current_user": "test_user",
            "uptime": 3600,
            "processes": '["chrome.exe", "explorer.exe", "python.exe"]'
        }
    }

    try:
        response = requests.post(
            f"{BASE_URL}/api/client/heartbeat",
            json=test_data,
            timeout=5
        )
        if response.status_code == 200:
            result = response.json()
            print_success(f"하트비트 전송 성공: {result.get('message')}")
            return True
        elif response.status_code == 404:
            print_error("PC가 등록되지 않았습니다 - 먼저 register를 실행하세요")
            return False
        else:
            print_error(f"하트비트 전송 실패 (Status: {response.status_code})")
            return False
    except requests.exceptions.RequestException as e:
        print_error(f"하트비트 전송 오류: {e}")
        return False

def test_client_command_poll():
    """클라이언트 명령 폴링 테스트"""
    print("\n--- 10. Client Command Poll (GET /api/client/command) ---")
    print_info("Long-polling 테스트 (timeout=2초)")

    try:
        start = time.time()
        response = requests.get(
            f"{BASE_URL}/api/client/command",
            params={"machine_id": "TEST_MACHINE_12345", "timeout": 2},
            timeout=5
        )
        elapsed = time.time() - start

        if response.status_code == 200:
            result = response.json()
            if result.get('command_type'):
                print_success(f"명령 수신: {result.get('command_type')}")
                print_info(f"명령 ID: {result.get('command_id')}")
            else:
                print_success(f"명령 없음 (대기 시간: {elapsed:.1f}초)")
            return True
        else:
            print_error(f"명령 폴링 실패 (Status: {response.status_code})")
            return False
    except requests.exceptions.RequestException as e:
        print_error(f"명령 폴링 오류: {e}")
        return False

def test_client_command_result():
    """클라이언트 명령 결과 보고 테스트"""
    print("\n--- 11. Client Command Result (POST /api/client/command/result) ---")
    print_info("이 테스트는 실제 command_id가 필요하므로 스킵됩니다")
    return True

# ==================== 메인 테스트 실행 ====================

def run_all_tests():
    """모든 테스트 실행"""
    print("=" * 70)
    print("WCMS API 통합 테스트")
    print("=" * 70)

    results = {}

    # 1. 기본 접근 테스트
    results['dashboard'] = test_dashboard_access()

    # 2. 관리자 로그인
    session = test_login()
    if not session:
        print_error("\n로그인 실패로 관리자 API 테스트를 건너뜁니다")
        session = requests.Session()  # 빈 세션

    # 3. 관리자 API 테스트
    pcs = test_pc_list(session)

    if pcs:
        pc_id = pcs[0]['id']
        results['pc_detail'] = test_pc_detail(session, pc_id)
        results['pc_history'] = test_pc_history(session, pc_id)
        results['send_command'] = test_send_command(session, pc_id, "execute", {"command": "echo test"})
    else:
        print_warning("\n등록된 PC가 없어서 일부 테스트를 건너뜁니다")

    results['layout'] = test_layout_api(session)

    # 4. 클라이언트 API 테스트
    results['client_register'] = test_client_register()
    results['client_heartbeat'] = test_client_heartbeat()
    results['client_poll'] = test_client_command_poll()
    test_client_command_result()

    # 5. 결과 요약
    print("\n" + "=" * 70)
    print("테스트 결과 요약")
    print("=" * 70)

    success_count = sum(1 for v in results.values() if v)
    total_count = len(results)

    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        color = Colors.GREEN if result else Colors.RED
        print(f"{color}{status}{Colors.END} - {test_name}")

    print("\n" + "=" * 70)
    print(f"전체: {success_count}/{total_count} 테스트 성공")
    print("=" * 70)

    return success_count == total_count

if __name__ == "__main__":
    print_info("서버가 http://127.0.0.1:5050 에서 실행 중인지 확인하세요\n")
    success = run_all_tests()

    if success:
        print(f"\n{Colors.GREEN}모든 테스트가 성공했습니다! 🎉{Colors.END}")
        exit(0)
    else:
        print(f"\n{Colors.YELLOW}일부 테스트가 실패했습니다. 로그를 확인하세요.{Colors.END}")
        exit(1)
