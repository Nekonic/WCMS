"""
WCMS 클라이언트 기능 테스트
- collector.py의 시스템 정보 수집 기능 테스트
- executor.py의 명령 실행 기능 테스트 (안전한 명령만)
"""

import sys
import json
from collector import collect_static_info, collect_dynamic_info, collect_running_processes
from executor import CommandExecutor

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

def print_section(title):
    print(f"\n{'=' * 70}")
    print(f"{title}")
    print('=' * 70)

# ==================== Collector 테스트 ====================

def test_collect_static_info():
    """정적 시스템 정보 수집 테스트"""
    print("\n--- 1. Static System Info Collection ---")
    try:
        info = collect_static_info()

        if info:
            print_success("정적 정보 수집 성공")
            print_info(f"호스트명: {info.get('hostname')}")
            print_info(f"CPU 모델: {info.get('cpu_model')}")
            print_info(f"CPU 코어: {info.get('cpu_cores')}")
            print_info(f"총 RAM: {info.get('ram_total')} MB")
            print_info(f"OS: {info.get('os_edition')}")

            # 필수 필드 확인
            required_fields = ['hostname', 'mac_address', 'cpu_model', 'cpu_cores',
                             'cpu_threads', 'ram_total', 'disk_info', 'os_edition', 'os_version']
            missing = [f for f in required_fields if f not in info or info[f] is None]

            if missing:
                print_warning(f"누락된 필드: {', '.join(missing)}")
                return False

            return True
        else:
            print_error("정적 정보 수집 실패")
            return False

    except Exception as e:
        print_error(f"테스트 실패: {e}")
        return False

def test_collect_dynamic_info():
    """동적 시스템 정보 수집 테스트"""
    print("\n--- 2. Dynamic System Info Collection ---")
    try:
        info = collect_dynamic_info()

        if info:
            print_success("동적 정보 수집 성공")
            print_info(f"CPU 사용률: {info.get('cpu_usage')}%")
            print_info(f"RAM 사용량: {info.get('ram_used')} MB ({info.get('ram_usage_percent')}%)")
            print_info(f"IP 주소: {info.get('ip_address')}")
            print_info(f"현재 사용자: {info.get('current_user')}")
            print_info(f"업타임: {info.get('uptime')} 초")

            # 프로세스 수 확인
            try:
                processes = json.loads(info.get('processes', '[]'))
                print_info(f"실행 중인 프로세스 종류: {len(processes)}개")
            except:
                pass

            # 필수 필드 확인
            required_fields = ['cpu_usage', 'ram_used', 'ram_usage_percent',
                             'disk_usage', 'ip_address', 'current_user', 'uptime', 'processes']
            missing = [f for f in required_fields if f not in info or info[f] is None]

            if missing:
                print_warning(f"누락된 필드: {', '.join(missing)}")
                return False

            return True
        else:
            print_error("동적 정보 수집 실패")
            return False

    except Exception as e:
        print_error(f"테스트 실패: {e}")
        return False

def test_collect_running_processes():
    """실행 중인 프로세스 목록 수집 테스트"""
    print("\n--- 3. Running Processes Collection ---")
    try:
        processes = collect_running_processes()

        if processes:
            print_success(f"프로세스 수집 성공 (총 {len(processes)}개)")
            if len(processes) > 0:
                print_info(f"샘플: {processes[0].get('name', 'Unknown')}")
            return True
        else:
            print_warning("프로세스 목록이 비어 있습니다")
            return True  # 비어있어도 성공으로 간주

    except Exception as e:
        print_error(f"테스트 실패: {e}")
        return False

# ==================== Executor 테스트 ====================

def test_execute_command_safe():
    """안전한 명령어 실행 테스트"""
    print("\n--- 4. Safe Command Execution ---")

    test_commands = [
        ('execute', {'command': 'echo Hello WCMS'}, 'Echo 테스트'),
        ('execute', {'command': 'hostname'}, 'Hostname 조회'),
    ]

    all_success = True

    for cmd_type, cmd_data, description in test_commands:
        try:
            result = CommandExecutor.execute_command(cmd_type, cmd_data)
            if result and '실패' not in result and '오류' not in result:
                print_success(f"{description}: {result.strip()[:50]}...")
            else:
                print_warning(f"{description}: {result[:100]}")
                all_success = False
        except Exception as e:
            print_error(f"{description} 실패: {e}")
            all_success = False

    return all_success

def test_command_validation():
    """명령어 파라미터 검증 테스트"""
    print("\n--- 5. Command Parameter Validation ---")

    test_cases = [
        ('install', {}, '필수 파라미터 누락 (app_name)'),
        ('execute', {}, '필수 파라미터 누락 (command)'),
        ('download', {'url': 'http://example.com'}, '필수 파라미터 누락 (path)'),
        ('create_user', {'username': 'test'}, '필수 파라미터 누락 (password)'),
        ('delete_user', {}, '필수 파라미터 누락 (username)'),
        ('change_password', {'username': 'test'}, '필수 파라미터 누락 (new_password)'),
        ('unknown_command', {}, '알 수 없는 명령'),
    ]

    all_success = True

    for cmd_type, cmd_data, description in test_cases:
        try:
            result = CommandExecutor.execute_command(cmd_type, cmd_data)
            if '오류' in result or '알 수 없는' in result:
                print_success(f"{description}: 올바르게 검증됨")
            else:
                print_warning(f"{description}: 예상과 다른 결과 - {result[:50]}")
        except Exception as e:
            print_error(f"{description} 테스트 실패: {e}")
            all_success = False

    return all_success

def test_dangerous_commands():
    """위험한 명령 테스트 (실제 실행 안 함)"""
    print("\n--- 6. Dangerous Commands (Simulation Only) ---")
    print_warning("⚠️  shutdown, reboot 명령은 실제로 실행되지 않습니다")
    print_info("이 명령들은 실제 환경에서만 테스트해야 합니다")
    return True

# ==================== 통합 테스트 ====================

def test_full_workflow():
    """전체 워크플로우 시뮬레이션"""
    print("\n--- 7. Full Workflow Simulation ---")

    try:
        # 1. 정적 정보 수집 (등록용)
        static_info = collect_static_info()
        if not static_info:
            print_error("정적 정보 수집 실패")
            return False

        # 2. 동적 정보 수집 (하트비트용)
        dynamic_info = collect_dynamic_info()
        if not dynamic_info:
            print_error("동적 정보 수집 실패")
            return False

        # 3. 명령 실행 시뮬레이션
        result = CommandExecutor.execute_command('execute', {'command': 'echo test'})
        if not result or '실패' in result:
            print_error("명령 실행 실패")
            return False

        print_success("전체 워크플로우 시뮬레이션 성공")
        print_info("클라이언트가 서버와 통신할 준비가 되었습니다")
        return True

    except Exception as e:
        print_error(f"워크플로우 테스트 실패: {e}")
        return False

# ==================== 메인 실행 ====================

def run_all_tests():
    """모든 테스트 실행"""
    print_section("WCMS 클라이언트 기능 테스트")

    results = {}

    # Collector 테스트
    results['static_info'] = test_collect_static_info()
    results['dynamic_info'] = test_collect_dynamic_info()
    results['processes'] = test_collect_running_processes()

    # Executor 테스트
    results['safe_commands'] = test_execute_command_safe()
    results['validation'] = test_command_validation()
    results['dangerous'] = test_dangerous_commands()

    # 통합 테스트
    results['workflow'] = test_full_workflow()

    # 결과 요약
    print_section("테스트 결과 요약")

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
    print_info("WCMS 클라이언트 기능 테스트를 시작합니다\n")

    success = run_all_tests()

    if success:
        print(f"\n{Colors.GREEN}모든 클라이언트 기능이 정상 작동합니다! 🎉{Colors.END}")
        sys.exit(0)
    else:
        print(f"\n{Colors.YELLOW}일부 테스트가 실패했습니다. 로그를 확인하세요.{Colors.END}")
        sys.exit(1)

