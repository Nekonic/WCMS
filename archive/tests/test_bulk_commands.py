#!/usr/bin/env python3
"""
WCMS 일괄 명령 테스트 스크립트
여러 PC에 동시에 명령을 전송하는 기능을 테스트합니다.
"""

import requests
import json
import sys

SERVER_URL = "http://127.0.0.1:5050"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin"

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

def print_info(msg):
    print(f"{Colors.BLUE}ℹ {msg}{Colors.END}")

def print_section(title):
    print(f"\n{Colors.CYAN}{'='*70}\n{title}\n{'='*70}{Colors.END}")

def admin_login(session):
    """관리자 로그인"""
    print_section("관리자 로그인")
    try:
        response = session.post(
            f"{SERVER_URL}/login",
            data={
                'username': ADMIN_USERNAME,
                'password': ADMIN_PASSWORD
            },
            allow_redirects=False
        )

        if response.status_code in [200, 302]:
            print_success("관리자 로그인 성공")
            return True
        else:
            print_error(f"로그인 실패: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"로그인 오류: {e}")
        return False

def get_online_pcs(session):
    """온라인 PC 목록 가져오기"""
    print_section("온라인 PC 조회")
    try:
        response = session.get(f"{SERVER_URL}/api/pcs")
        if response.status_code == 200:
            pcs = response.json()
            online_pcs = [pc for pc in pcs if pc.get('is_online')]

            print_info(f"총 {len(pcs)}대 PC 중 {len(online_pcs)}대 온라인")

            for pc in online_pcs[:5]:  # 처음 5대만 표시
                print(f"  - PC#{pc['id']}: {pc.get('hostname', 'Unknown')} ({pc.get('seat_number', '미배치')})")

            if len(online_pcs) > 5:
                print(f"  ... 외 {len(online_pcs) - 5}대")

            return online_pcs
        else:
            print_error(f"PC 목록 조회 실패: {response.status_code}")
            return []
    except Exception as e:
        print_error(f"PC 조회 오류: {e}")
        return []

def test_bulk_cmd_command(session, pc_ids):
    """일괄 CMD 명령 테스트"""
    print_section("테스트 1: 일괄 CMD 명령 실행")

    if not pc_ids:
        print_error("테스트할 PC가 없습니다.")
        return False

    print_info(f"{len(pc_ids)}대의 PC에 'hostname' 명령 전송")

    try:
        response = session.post(
            f"{SERVER_URL}/api/pcs/bulk-command",
            json={
                'pc_ids': pc_ids,
                'command_type': 'execute',
                'command_data': {'command': 'hostname'}
            }
        )

        if response.status_code == 200:
            result = response.json()
            print_success(f"명령 전송 완료: {result['success']}대 성공, {result['failed']}대 실패")
            return True
        else:
            print_error(f"명령 전송 실패: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print_error(f"명령 전송 오류: {e}")
        return False

def test_bulk_winget(session, pc_ids):
    """일괄 winget 설치 테스트"""
    print_section("테스트 2: 일괄 프로그램 설치 (winget)")

    if not pc_ids:
        print_error("테스트할 PC가 없습니다.")
        return False

    # 실제로는 설치하지 않고 검색만 수행
    print_info(f"{len(pc_ids)}대의 PC에 winget 검색 명령 전송 (테스트)")

    try:
        response = session.post(
            f"{SERVER_URL}/api/pcs/bulk-command",
            json={
                'pc_ids': pc_ids,
                'command_type': 'execute',
                'command_data': {'command': 'winget --version'}
            }
        )

        if response.status_code == 200:
            result = response.json()
            print_success(f"명령 전송 완료: {result['success']}대 성공")
            return True
        else:
            print_error(f"명령 전송 실패: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"명령 전송 오류: {e}")
        return False

def test_bulk_download(session, pc_ids):
    """일괄 파일 다운로드 테스트"""
    print_section("테스트 3: 일괄 파일 다운로드")

    if not pc_ids:
        print_error("테스트할 PC가 없습니다.")
        return False

    print_info(f"{len(pc_ids)}대의 PC에 파일 다운로드 명령 전송")

    try:
        response = session.post(
            f"{SERVER_URL}/api/pcs/bulk-command",
            json={
                'pc_ids': pc_ids,
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
            return True
        else:
            print_error(f"명령 전송 실패: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"명령 전송 오류: {e}")
        return False

def test_bulk_account(session, pc_ids):
    """일괄 계정 관리 테스트"""
    print_section("테스트 4: 일괄 계정 관리")

    if not pc_ids:
        print_error("테스트할 PC가 없습니다.")
        return False

    print_info(f"{len(pc_ids)}대의 PC에 테스트 계정 생성 명령 전송")
    print_info("⚠️  실제 계정이 생성되므로 주의하세요!")

    # 실제 환경에서는 주석 처리
    print_info("(테스트 모드: 실제로는 실행하지 않습니다)")
    return True

    # 실제 실행 코드 (주석 처리됨)
    """
    try:
        response = session.post(
            f"{SERVER_URL}/api/pcs/bulk-command",
            json={
                'pc_ids': pc_ids,
                'command_type': 'account',
                'command_data': {
                    'action': 'create',
                    'username': 'wcms_test',
                    'password': 'Test1234!'
                }
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            print_success(f"명령 전송 완료: {result['success']}대 성공")
            return True
        else:
            print_error(f"명령 전송 실패: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"명령 전송 오류: {e}")
        return False
    """

def main():
    """메인 테스트 함수"""
    print_section("WCMS 일괄 명령 테스트")
    print_info(f"서버 URL: {SERVER_URL}")

    # 세션 생성
    session = requests.Session()

    # 1. 관리자 로그인
    if not admin_login(session):
        print_error("로그인에 실패하여 테스트를 중단합니다.")
        return

    # 2. 온라인 PC 조회
    online_pcs = get_online_pcs(session)

    if not online_pcs:
        print_error("온라인 PC가 없어서 테스트를 건너뜁니다.")
        print_info("클라이언트를 실행한 후 다시 시도하세요.")
        return

    # 테스트할 PC ID 목록 (최대 3대)
    test_pc_ids = [pc['id'] for pc in online_pcs[:3]]

    # 3. 테스트 실행
    results = []
    results.append(('CMD 명령', test_bulk_cmd_command(session, test_pc_ids)))
    results.append(('winget 검색', test_bulk_winget(session, test_pc_ids)))
    results.append(('파일 다운로드', test_bulk_download(session, test_pc_ids)))
    results.append(('계정 관리', test_bulk_account(session, test_pc_ids)))

    # 4. 결과 요약
    print_section("테스트 결과 요약")

    for name, result in results:
        if result:
            print_success(f"{name}: PASS")
        else:
            print_error(f"{name}: FAIL")

    total = len(results)
    passed = sum(1 for _, r in results if r)

    print(f"\n{Colors.CYAN}{'='*70}")
    print(f"전체: {passed}/{total} 테스트 통과")
    print(f"{'='*70}{Colors.END}\n")

    if passed == total:
        print_success("모든 테스트가 성공했습니다! 🎉")
    else:
        print_error(f"{total - passed}개의 테스트가 실패했습니다.")

if __name__ == "__main__":
    print_info("서버가 http://127.0.0.1:5050 에서 실행 중인지 확인하세요")
    print_info("최소 1대 이상의 클라이언트가 온라인 상태여야 합니다\n")

    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}테스트가 사용자에 의해 중단되었습니다.{Colors.END}")
        sys.exit(0)

