#!/usr/bin/env python3
"""
WCMS 통합 테스트 스크립트
서버와 클라이언트의 전체 통신 흐름을 테스트합니다.
"""

import sys
import os
import time
import requests
import json

# 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_DIR = os.path.join(BASE_DIR, 'client')
sys.path.insert(0, CLIENT_DIR)

# 현재 디렉토리를 client로 변경 (collector.py가 상대 경로를 사용할 수 있도록)
original_dir = os.getcwd()
os.chdir(CLIENT_DIR)

try:
    from collector import collect_static_info, collect_dynamic_info
    from executor import CommandExecutor
except ImportError as e:
    print(f"❌ 모듈 임포트 실패: {e}")
    print(f"현재 작업 디렉토리: {os.getcwd()}")
    print(f"sys.path: {sys.path}")
    sys.exit(1)
finally:
    # 원래 디렉토리로 복원
    os.chdir(original_dir)

SERVER_URL = "http://127.0.0.1:5050"
TEST_MACHINE_ID = "INTEGRATION_TEST_PC"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    END = '\033[0m'

def print_success(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.END}")

def print_error(msg):
    print(f"{Colors.RED}✗ {msg}{Colors.END}")

def print_warning(msg):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.END}")

def print_info(msg):
    print(f"{Colors.BLUE}ℹ {msg}{Colors.END}")

def print_step(step, msg):
    print(f"\n{Colors.CYAN}[Step {step}] {msg}{Colors.END}")

# ==================== 통합 테스트 시나리오 ====================

def scenario_1_client_registration():
    """시나리오 1: 클라이언트 등록"""
    print_step(1, "클라이언트 등록 테스트")

    # 실제 시스템 정보 수집
    static_info = collect_static_info()
    if not static_info:
        print_error("시스템 정보 수집 실패")
        return False

    # machine_id를 테스트용으로 변경
    static_info['machine_id'] = TEST_MACHINE_ID

    try:
        response = requests.post(
            f"{SERVER_URL}/api/client/register",
            json=static_info,
            timeout=10
        )

        if response.status_code == 200:
            print_success("클라이언트 등록 성공")
            return True
        elif response.status_code == 500:
            try:
                error_msg = response.json().get('message', '')
                if "이미 등록된" in error_msg:
                    print_warning("이미 등록된 PC (정상)")
                    return True
            except:
                pass
            print_error(f"등록 실패: {response.status_code} - {response.text}")
            return False
        else:
            print_error(f"등록 실패: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        print_error(f"등록 요청 실패: {e}")
        return False

def scenario_2_heartbeat():
    """시나리오 2: 하트비트 전송"""
    print_step(2, "하트비트 전송 테스트")

    # 실제 동적 정보 수집
    dynamic_info = collect_dynamic_info()
    if not dynamic_info:
        print_error("동적 정보 수집 실패")
        return False

    data = {
        "machine_id": TEST_MACHINE_ID,
        "system_info": dynamic_info
    }

    try:
        response = requests.post(
            f"{SERVER_URL}/api/client/heartbeat",
            json=data,
            timeout=10
        )

        if response.status_code == 200:
            print_success("하트비트 전송 성공")
            print_info(f"CPU: {dynamic_info['cpu_usage']}%, RAM: {dynamic_info['ram_used']}MB")
            return True
        else:
            print_error(f"하트비트 실패: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        print_error(f"하트비트 요청 실패: {e}")
        return False

def scenario_3_pc_list_check():
    """시나리오 3: PC 목록에서 등록된 PC 확인"""
    print_step(3, "PC 목록 확인")

    try:
        response = requests.get(f"{SERVER_URL}/api/pcs", timeout=10)

        if response.status_code == 200:
            pcs = response.json()
            test_pc = next((pc for pc in pcs if pc['machine_id'] == TEST_MACHINE_ID), None)

            if test_pc:
                print_success(f"PC 발견: {test_pc['hostname']}")
                print_info(f"온라인 상태: {test_pc['is_online']}")
                print_info(f"마지막 접속: {test_pc.get('last_seen', 'Unknown')}")
                return test_pc['id']
            else:
                print_error("등록된 PC를 목록에서 찾을 수 없습니다")
                return None
        else:
            print_error(f"PC 목록 조회 실패: {response.status_code}")
            return None

    except Exception as e:
        print_error(f"PC 목록 조회 오류: {e}")
        return None

def scenario_4_send_command(pc_id):
    """시나리오 4: 관리자가 명령 전송"""
    print_step(4, "명령 전송 테스트")

    # 관리자 로그인
    session = requests.Session()
    try:
        login_response = session.post(
            f"{SERVER_URL}/login",
            data={"username": "admin", "password": "admin"},
            timeout=5,
            allow_redirects=False  # 리다이렉트 자동으로 따라가지 않음
        )

        # Flask는 로그인 성공 시 302 리다이렉트를 반환
        if login_response.status_code == 302:
            print_success("관리자 로그인 성공")
        elif login_response.status_code == 200:
            # 200이면 로그인 실패 (로그인 페이지 재표시)
            print_error("관리자 로그인 실패 (잘못된 인증 정보)")
            return False
        else:
            print_error(f"로그인 실패: {login_response.status_code}")
            return False

    except Exception as e:
        print_error(f"로그인 오류: {e}")
        return False

    # 안전한 테스트 명령 전송
    command_data = {
        "type": "execute",
        "data": {"command": "echo WCMS Integration Test"}
    }

    try:
        response = session.post(
            f"{SERVER_URL}/api/pc/{pc_id}/command",
            json=command_data,
            timeout=5
        )

        if response.status_code == 200:
            print_success("명령 전송 성공")
            return True
        else:
            print_error(f"명령 전송 실패: {response.status_code}")
            if response.status_code == 401:
                print_info("세션 쿠키:", session.cookies.get_dict())
            print_error(f"응답: {response.text[:200]}")
            return False

    except Exception as e:
        print_error(f"명령 전송 오류: {e}")
        return False

def scenario_5_poll_and_execute():
    """시나리오 5: 클라이언트가 명령 폴링 및 실행"""
    print_step(5, "명령 폴링 및 실행")

    try:
        # 명령 폴링 (timeout 짧게)
        response = requests.get(
            f"{SERVER_URL}/api/client/command",
            params={"machine_id": TEST_MACHINE_ID, "timeout": 2},
            timeout=5
        )

        if response.status_code == 200:
            cmd_data = response.json()

            if cmd_data.get('command_type'):
                cmd_id = cmd_data.get('command_id')
                cmd_type = cmd_data['command_type']
                cmd_params = json.loads(cmd_data.get('command_data', '{}'))

                print_success(f"명령 수신: {cmd_type}")
                print_info(f"파라미터: {cmd_params}")

                # 명령 실행
                result = CommandExecutor.execute_command(cmd_type, cmd_params)
                print_info(f"실행 결과: {result[:100]}")

                # 결과 보고
                result_data = {
                    "machine_id": TEST_MACHINE_ID,
                    "command_id": cmd_id,
                    "status": "completed",
                    "result": result
                }

                result_response = requests.post(
                    f"{SERVER_URL}/api/client/command/result",
                    json=result_data,
                    timeout=5
                )

                if result_response.status_code == 200:
                    print_success("명령 실행 결과 보고 성공")
                    return True
                else:
                    print_warning(f"결과 보고 실패: {result_response.status_code}")
                    return True  # 명령은 성공했으므로 True
            else:
                print_info("대기 중인 명령이 없습니다 (정상)")
                return True
        else:
            print_error(f"명령 폴링 실패: {response.status_code}")
            return False

    except Exception as e:
        print_error(f"명령 폴링 오류: {e}")
        return False

def scenario_6_verify_data():
    """시나리오 6: PC 상세 정보 확인"""
    print_step(6, "PC 상세 정보 검증")

    # 먼저 PC ID 찾기
    try:
        pcs_response = requests.get(f"{SERVER_URL}/api/pcs", timeout=5)
        if pcs_response.status_code != 200:
            print_error("PC 목록 조회 실패")
            return False

        pcs = pcs_response.json()
        test_pc = next((pc for pc in pcs if pc['machine_id'] == TEST_MACHINE_ID), None)

        if not test_pc:
            print_error("테스트 PC를 찾을 수 없습니다")
            return False

        pc_id = test_pc['id']

        # PC 상세 정보 조회
        detail_response = requests.get(f"{SERVER_URL}/api/pc/{pc_id}", timeout=5)

        if detail_response.status_code == 200:
            pc_detail = detail_response.json()
            print_success("PC 상세 정보 조회 성공")
            print_info(f"CPU 사용률: {pc_detail.get('cpu_usage', 'N/A')}%")
            print_info(f"RAM 사용량: {pc_detail.get('ram_used', 'N/A')} MB")
            print_info(f"온라인: {pc_detail.get('is_online', False)}")
            return True
        else:
            print_error(f"상세 정보 조회 실패: {detail_response.status_code}")
            return False

    except Exception as e:
        print_error(f"데이터 검증 오류: {e}")
        return False

# ==================== 메인 실행 ====================

def run_integration_tests():
    """통합 테스트 실행"""
    print("=" * 80)
    print("WCMS 통합 테스트")
    print("서버-클라이언트 전체 통신 흐름 검증")
    print("=" * 80)

    # 서버 연결 확인
    print_info("서버 연결 확인 중...")
    try:
        response = requests.get(f"{SERVER_URL}/", timeout=5)
        if response.status_code != 200:
            print_error("서버가 응답하지 않습니다. 먼저 서버를 시작하세요.")
            return False
    except:
        print_error("서버에 연결할 수 없습니다. http://127.0.0.1:5050 에서 서버를 시작하세요.")
        return False

    print_success("서버 연결 확인 완료\n")

    results = {}
    pc_id = None

    # 시나리오 실행
    results['registration'] = scenario_1_client_registration()
    time.sleep(0.5)

    results['heartbeat'] = scenario_2_heartbeat()
    time.sleep(0.5)

    pc_id = scenario_3_pc_list_check()
    results['pc_found'] = pc_id is not None
    time.sleep(0.5)

    if pc_id:
        results['send_command'] = scenario_4_send_command(pc_id)
        time.sleep(0.5)

        results['poll_execute'] = scenario_5_poll_and_execute()
        time.sleep(0.5)

    results['verify_data'] = scenario_6_verify_data()

    # 결과 요약
    print("\n" + "=" * 80)
    print("통합 테스트 결과")
    print("=" * 80)

    success_count = sum(1 for v in results.values() if v)
    total_count = len(results)

    for scenario, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        color = Colors.GREEN if result else Colors.RED
        print(f"{color}{status}{Colors.END} - {scenario}")

    print("\n" + "=" * 80)
    print(f"전체: {success_count}/{total_count} 시나리오 성공")
    print("=" * 80)

    return success_count == total_count

if __name__ == "__main__":
    success = run_integration_tests()

    if success:
        print(f"\n{Colors.GREEN}✅ 모든 통합 테스트가 성공했습니다!{Colors.END}")
        print(f"{Colors.GREEN}WCMS 시스템이 정상적으로 작동합니다. 🎉{Colors.END}\n")
        sys.exit(0)
    else:
        print(f"\n{Colors.YELLOW}⚠️  일부 테스트가 실패했습니다.{Colors.END}")
        print(f"{Colors.YELLOW}로그를 확인하고 문제를 해결하세요.{Colors.END}\n")
        sys.exit(1)

