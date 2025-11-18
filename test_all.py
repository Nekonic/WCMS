#!/usr/bin/env python3
"""
WCMS 통합 테스트 스크립트
모든 테스트를 한 번에 실행합니다.

사용법:
    python test_all.py              # 모든 테스트 실행
    python test_all.py --server     # 서버 API 테스트만
    python test_all.py --client     # 클라이언트 테스트만
    python test_all.py --bulk       # 일괄 명령 테스트만
"""

import sys
import os
import time
import requests
import json
import argparse

# 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_DIR = os.path.join(BASE_DIR, 'client')

SERVER_URL = "http://127.0.0.1:5050"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin"
TEST_MACHINE_ID = "TEST_PC_INTEGRATION"

# 색상 출력
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_success(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.END}")

def print_error(msg):
    print(f"{Colors.RED}✗ {msg}{Colors.END}")

def print_warning(msg):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.END}")

def print_info(msg):
    print(f"{Colors.BLUE}ℹ {msg}{Colors.END}")

def print_section(title):
    print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*70}")
    print(f"{title}")
    print(f"{'='*70}{Colors.END}\n")

def print_subsection(title):
    print(f"\n{Colors.MAGENTA}--- {title} ---{Colors.END}")


# ==================== 서버 API 테스트 ====================

def test_server_api():
    """서버 API 엔드포인트 테스트"""
    print_section("📡 서버 API 테스트")

    results = []

    # 1. 대시보드 접근
    print_subsection("1. Dashboard Access (GET /)")
    try:
        response = requests.get(f"{SERVER_URL}/", timeout=5)
        if response.status_code == 200:
            print_success(f"대시보드 접근 성공 (Status: {response.status_code})")
            results.append(('dashboard', True))
        else:
            print_error(f"대시보드 접근 실패 (Status: {response.status_code})")
            results.append(('dashboard', False))
    except Exception as e:
        print_error(f"대시보드 접근 오류: {e}")
        results.append(('dashboard', False))

    # 2. 관리자 로그인
    print_subsection("2. Admin Login (POST /login)")
    session = requests.Session()
    try:
        response = session.post(
            f"{SERVER_URL}/login",
            data={'username': ADMIN_USERNAME, 'password': ADMIN_PASSWORD},
            allow_redirects=False
        )
        if response.status_code in [200, 302]:
            print_success("로그인 성공")
            results.append(('login', True))
        else:
            print_error(f"로그인 실패 (Status: {response.status_code})")
            results.append(('login', False))
    except Exception as e:
        print_error(f"로그인 오류: {e}")
        results.append(('login', False))

    # 3. PC 목록 조회
    print_subsection("3. PC List (GET /api/pcs)")
    try:
        response = session.get(f"{SERVER_URL}/api/pcs", timeout=5)
        if response.status_code == 200:
            pcs = response.json()
            print_success(f"PC 목록 조회 성공 (총 {len(pcs)}대)")
            results.append(('pc_list', True))
        else:
            print_error(f"PC 목록 조회 실패 (Status: {response.status_code})")
            results.append(('pc_list', False))
    except Exception as e:
        print_error(f"PC 목록 조회 오류: {e}")
        results.append(('pc_list', False))

    # 4. 좌석 배치 조회
    print_subsection("4. Layout Map (GET /api/layout/map/1실습실)")
    try:
        response = session.get(f"{SERVER_URL}/api/layout/map/1실습실", timeout=5)
        if response.status_code == 200:
            layout = response.json()
            print_success(f"좌석 배치 조회 성공")
            print_info(f"행: {layout.get('rows')}, 열: {layout.get('cols')}")
            results.append(('layout', True))
        else:
            print_error(f"좌석 배치 조회 실패 (Status: {response.status_code})")
            results.append(('layout', False))
    except Exception as e:
        print_error(f"좌석 배치 조회 오류: {e}")
        results.append(('layout', False))

    # 5. 클라이언트 등록
    print_subsection("5. Client Register (POST /api/client/register)")
    try:
        test_data = {
            "machine_id": TEST_MACHINE_ID,
            "hostname": "TEST-PC",
            "mac_address": "00:11:22:33:44:55",
            "cpu_model": "Test CPU",
            "cpu_cores": 4,
            "ram_total": 8192
        }
        response = requests.post(
            f"{SERVER_URL}/api/client/register",
            json=test_data,
            timeout=5
        )
        if response.status_code in [200, 500]:  # 500은 이미 등록된 경우
            result = response.json()
            print_success(f"클라이언트 등록: {result.get('message')}")
            results.append(('register', True))
        else:
            print_error(f"클라이언트 등록 실패 (Status: {response.status_code})")
            results.append(('register', False))
    except Exception as e:
        print_error(f"클라이언트 등록 오류: {e}")
        results.append(('register', False))

    # 6. 하트비트
    print_subsection("6. Client Heartbeat (POST /api/client/heartbeat)")
    try:
        heartbeat_data = {
            "machine_id": TEST_MACHINE_ID,
            "system_info": {
                "cpu_usage": 45.2,
                "ram_used": 4096,
                "ip_address": "127.0.0.1"
            }
        }
        response = requests.post(
            f"{SERVER_URL}/api/client/heartbeat",
            json=heartbeat_data,
            timeout=5
        )
        if response.status_code == 200:
            print_success("하트비트 전송 성공")
            results.append(('heartbeat', True))
        else:
            print_error(f"하트비트 전송 실패 (Status: {response.status_code})")
            results.append(('heartbeat', False))
    except Exception as e:
        print_error(f"하트비트 전송 오류: {e}")
        results.append(('heartbeat', False))

    # 7. 명령 폴링
    print_subsection("7. Client Command Poll (GET /api/client/command)")
    try:
        print_info("Long-polling 테스트 (timeout=2초)")
        start = time.time()
        response = requests.get(
            f"{SERVER_URL}/api/client/command",
            params={"machine_id": TEST_MACHINE_ID, "timeout": 2},
            timeout=5
        )
        elapsed = time.time() - start

        if response.status_code == 200:
            cmd = response.json()
            if cmd.get('command_id'):
                print_success(f"명령 수신: {cmd.get('command_type')}")
            else:
                print_success(f"명령 없음 (대기 시간: {elapsed:.1f}초)")
            results.append(('poll', True))
        else:
            print_error(f"명령 폴링 실패 (Status: {response.status_code})")
            results.append(('poll', False))
    except Exception as e:
        print_error(f"명령 폴링 오류: {e}")
        results.append(('poll', False))

    return results


# ==================== 일괄 명령 테스트 ====================

def test_bulk_commands():
    """일괄 명령 기능 테스트"""
    print_section("📦 일괄 명령 테스트")

    # 로그인
    session = requests.Session()
    try:
        response = session.post(
            f"{SERVER_URL}/login",
            data={'username': ADMIN_USERNAME, 'password': ADMIN_PASSWORD},
            allow_redirects=False
        )
        if response.status_code not in [200, 302]:
            print_error("로그인 실패 - 테스트 중단")
            return []
    except Exception as e:
        print_error(f"로그인 오류: {e}")
        return []

    # 온라인 PC 조회
    try:
        response = session.get(f"{SERVER_URL}/api/pcs")
        pcs = response.json()
        online_pcs = [pc for pc in pcs if pc.get('is_online')]

        print_info(f"총 {len(pcs)}대 PC 중 {len(online_pcs)}대 온라인")

        if not online_pcs:
            print_warning("온라인 PC가 없어 일괄 명령 테스트를 건너뜁니다")
            return []

        # 최대 3대만 테스트
        test_pc_ids = [pc['id'] for pc in online_pcs[:3]]
        print_info(f"테스트 대상: {len(test_pc_ids)}대")

    except Exception as e:
        print_error(f"PC 조회 오류: {e}")
        return []

    results = []

    # 1. 일괄 CMD 명령
    print_subsection("1. 일괄 CMD 명령 (hostname)")
    try:
        response = session.post(
            f"{SERVER_URL}/api/pcs/bulk-command",
            json={
                'pc_ids': test_pc_ids,
                'command_type': 'execute',
                'command_data': {'command': 'hostname'}
            }
        )
        if response.status_code == 200:
            result = response.json()
            print_success(f"명령 전송 완료: {result['success']}대 성공, {result['failed']}대 실패")
            results.append(('bulk_cmd', True))
        else:
            print_error(f"명령 전송 실패: {response.status_code}")
            results.append(('bulk_cmd', False))
    except Exception as e:
        print_error(f"명령 전송 오류: {e}")
        results.append(('bulk_cmd', False))

    # 2. 일괄 winget (버전 확인만)
    print_subsection("2. 일괄 winget 버전 확인")
    try:
        response = session.post(
            f"{SERVER_URL}/api/pcs/bulk-command",
            json={
                'pc_ids': test_pc_ids,
                'command_type': 'execute',
                'command_data': {'command': 'winget --version'}
            }
        )
        if response.status_code == 200:
            result = response.json()
            print_success(f"명령 전송 완료: {result['success']}대 성공")
            results.append(('bulk_winget', True))
        else:
            print_error(f"명령 전송 실패")
            results.append(('bulk_winget', False))
    except Exception as e:
        print_error(f"명령 전송 오류: {e}")
        results.append(('bulk_winget', False))

    # 3. 일괄 파일 다운로드
    print_subsection("3. 일괄 파일 다운로드")
    try:
        response = session.post(
            f"{SERVER_URL}/api/pcs/bulk-command",
            json={
                'pc_ids': test_pc_ids,
                'command_type': 'download',
                'command_data': {
                    'url': 'https://www.google.com/robots.txt',
                    'destination': 'C:\\temp\\wcms_test.txt'
                }
            }
        )
        if response.status_code == 200:
            result = response.json()
            print_success(f"명령 전송 완료: {result['success']}대 성공")
            results.append(('bulk_download', True))
        else:
            print_error(f"명령 전송 실패")
            results.append(('bulk_download', False))
    except Exception as e:
        print_error(f"명령 전송 오류: {e}")
        results.append(('bulk_download', False))

    return results


# ==================== 클라이언트 테스트 ====================

def test_client_functions():
    """클라이언트 함수 테스트"""
    print_section("🖥️  클라이언트 기능 테스트")

    # client 모듈 임포트
    sys.path.insert(0, CLIENT_DIR)
    original_dir = os.getcwd()
    os.chdir(CLIENT_DIR)

    try:
        from collector import collect_static_info, collect_dynamic_info
        from executor import CommandExecutor
    except ImportError as e:
        print_error(f"모듈 임포트 실패: {e}")
        os.chdir(original_dir)
        return []
    finally:
        os.chdir(original_dir)

    results = []

    # 1. 정적 정보 수집
    print_subsection("1. 정적 정보 수집")
    try:
        static_info = collect_static_info()
        if static_info and 'cpu_model' in static_info:
            print_success(f"정적 정보 수집 성공")
            print_info(f"CPU: {static_info.get('cpu_model')}")
            print_info(f"RAM: {static_info.get('ram_total')} MB")
            results.append(('static_info', True))
        else:
            print_error("정적 정보 수집 실패")
            results.append(('static_info', False))
    except Exception as e:
        print_error(f"정적 정보 수집 오류: {e}")
        results.append(('static_info', False))

    # 2. 동적 정보 수집
    print_subsection("2. 동적 정보 수집")
    try:
        dynamic_info = collect_dynamic_info()
        if dynamic_info and 'cpu_usage' in dynamic_info:
            print_success(f"동적 정보 수집 성공")
            print_info(f"CPU 사용률: {dynamic_info.get('cpu_usage')}%")
            results.append(('dynamic_info', True))
        else:
            print_error("동적 정보 수집 실패")
            results.append(('dynamic_info', False))
    except Exception as e:
        print_error(f"동적 정보 수집 오류: {e}")
        results.append(('dynamic_info', False))

    # 3. CMD 명령 실행 (안전한 명령만)
    print_subsection("3. CMD 명령 실행 테스트")
    try:
        result = CommandExecutor.execute('echo Test')
        if result and 'Test' in result:
            print_success("CMD 명령 실행 성공")
            results.append(('cmd_execute', True))
        else:
            print_error("CMD 명령 실행 실패")
            results.append(('cmd_execute', False))
    except Exception as e:
        print_error(f"CMD 명령 실행 오류: {e}")
        results.append(('cmd_execute', False))

    return results


# ==================== 메인 함수 ====================

def main():
    """통합 테스트 메인 함수"""
    parser = argparse.ArgumentParser(description='WCMS 통합 테스트')
    parser.add_argument('--server', action='store_true', help='서버 API 테스트만')
    parser.add_argument('--client', action='store_true', help='클라이언트 테스트만')
    parser.add_argument('--bulk', action='store_true', help='일괄 명령 테스트만')
    args = parser.parse_args()

    # 모든 옵션이 False면 전체 테스트
    run_all = not (args.server or args.client or args.bulk)

    print_section("🧪 WCMS 통합 테스트")
    print_info(f"서버 URL: {SERVER_URL}")
    print_info("서버가 실행 중이고, 클라이언트가 온라인 상태인지 확인하세요\n")

    all_results = []

    # 서버 연결 확인
    try:
        requests.get(f"{SERVER_URL}/", timeout=3)
    except:
        print_error("서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요.")
        return

    # 테스트 실행
    if run_all or args.server:
        all_results.extend(test_server_api())

    if run_all or args.bulk:
        all_results.extend(test_bulk_commands())

    if run_all or args.client:
        all_results.extend(test_client_functions())

    # 결과 요약
    print_section("📊 테스트 결과 요약")

    passed = 0
    failed = 0

    for name, result in all_results:
        if result:
            print_success(f"{name}: PASS")
            passed += 1
        else:
            print_error(f"{name}: FAIL")
            failed += 1

    total = len(all_results)

    print(f"\n{Colors.CYAN}{'='*70}")
    print(f"전체: {passed}/{total} 테스트 통과")
    print(f"{'='*70}{Colors.END}\n")

    if passed == total:
        print_success("모든 테스트가 성공했습니다! 🎉")
    else:
        print_error(f"{failed}개의 테스트가 실패했습니다.")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}테스트가 사용자에 의해 중단되었습니다.{Colors.END}")
        sys.exit(0)

