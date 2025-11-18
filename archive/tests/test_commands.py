#!/usr/bin/env python3
"""
WCMS 명령 실행 테스트 스크립트
CMD, winget, 파일 다운로드 기능을 실제로 테스트합니다.
"""

import sys
import os

# 경로 설정
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_DIR = os.path.join(SCRIPT_DIR, 'client')
sys.path.insert(0, CLIENT_DIR)

from executor import CommandExecutor

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

def print_section(title):
    print(f"\n{Colors.CYAN}{'='*70}")
    print(f"{title}")
    print(f"{'='*70}{Colors.END}")

# ==================== CMD 명령 테스트 ====================

def test_cmd_commands():
    """CMD 명령어 실행 테스트"""
    print_section("1. CMD 명령어 실행 테스트")

    test_cases = [
        ("echo Hello WCMS", "Echo 테스트"),
        ("dir", "현재 디렉토리 목록"),
        ("hostname", "호스트명 조회"),
        ("whoami", "현재 사용자 확인"),
        ("systeminfo | findstr /B /C:\"OS Name\" /C:\"OS Version\"", "OS 정보"),
        ("ipconfig | findstr IPv4", "IP 주소 확인"),
    ]

    results = []
    for command, description in test_cases:
        print(f"\n[테스트] {description}")
        print_info(f"명령: {command}")

        result = CommandExecutor.execute_command('execute', {'command': command})
        print(result)

        success = '✅' in result or '성공' in result
        results.append(success)

    success_count = sum(results)
    print(f"\n{Colors.CYAN}결과: {success_count}/{len(test_cases)} 테스트 통과{Colors.END}")
    return success_count == len(test_cases)

# ==================== winget 설치 테스트 ====================

def test_winget_install():
    """winget 설치 테스트"""
    print_section("2. winget 설치 테스트")

    print_warning("⚠️  실제 프로그램이 설치됩니다!")
    print_info("작은 유틸리티를 테스트용으로 설치합니다.")

    # 테스트용 작은 프로그램들
    test_apps = [
        # ("Notepad++.Notepad++", "Notepad++ 텍스트 에디터"),  # 실제 설치는 주석 처리
        # ("7zip.7zip", "7-Zip 압축 프로그램"),  # 실제 설치는 주석 처리
    ]

    if not test_apps:
        print_warning("실제 설치 테스트는 건너뜁니다.")
        print_info("테스트하려면 test_apps 리스트의 주석을 해제하세요.")

        # winget 버전만 확인
        print("\n[테스트] winget 설치 확인")
        result = CommandExecutor.execute_command('execute', {'command': 'winget --version'})
        print(result)

        if '✅' in result:
            print_success("winget이 설치되어 있습니다.")
            return True
        else:
            print_error("winget이 설치되어 있지 않습니다.")
            return False

    results = []
    for app_id, description in test_apps:
        print(f"\n[테스트] {description}")
        print_info(f"앱 ID: {app_id}")

        result = CommandExecutor.execute_command('install', {'app_name': app_id})
        print(result)

        success = '✅' in result
        results.append(success)

    if results:
        success_count = sum(results)
        print(f"\n{Colors.CYAN}결과: {success_count}/{len(test_apps)} 설치 성공{Colors.END}")
        return success_count == len(test_apps)

    return True

# ==================== 파일 다운로드 테스트 ====================

def test_file_download():
    """파일 다운로드 테스트"""
    print_section("3. 파일 다운로드 테스트")

    import tempfile
    temp_dir = tempfile.gettempdir()

    test_files = [
        (
            "https://raw.githubusercontent.com/git/git/master/README.md",
            os.path.join(temp_dir, "wcms_test_readme.md"),
            "GitHub README 다운로드"
        ),
        (
            "https://www.google.com/robots.txt",
            os.path.join(temp_dir, "wcms_test_robots.txt"),
            "robots.txt 다운로드"
        ),
    ]

    results = []
    for url, save_path, description in test_files:
        print(f"\n[테스트] {description}")
        print_info(f"URL: {url}")
        print_info(f"저장 경로: {save_path}")

        result = CommandExecutor.execute_command('download', {
            'url': url,
            'path': save_path
        })
        print(result)

        success = '✅' in result and os.path.exists(save_path)
        results.append(success)

        if success:
            # 파일 내용 미리보기
            try:
                with open(save_path, 'r', encoding='utf-8', errors='ignore') as f:
                    preview = f.read(200)
                    print_info(f"내용 미리보기:\n{preview}...")
            except:
                pass

    success_count = sum(results)
    print(f"\n{Colors.CYAN}결과: {success_count}/{len(test_files)} 다운로드 성공{Colors.END}")

    # 임시 파일 정리
    print_info("\n임시 파일 정리 중...")
    for _, save_path, _ in test_files:
        try:
            if os.path.exists(save_path):
                os.remove(save_path)
                print(f"  삭제: {save_path}")
        except:
            pass

    return success_count == len(test_files)

# ==================== 통합 시나리오 테스트 ====================

def test_integration_scenario():
    """통합 시나리오: 실제 사용 사례"""
    print_section("4. 통합 시나리오 테스트")

    import tempfile
    temp_dir = tempfile.gettempdir()

    print_info("시나리오: 시스템 정보 수집 후 파일로 저장")

    # 1단계: 시스템 정보 수집
    print("\n[1단계] 시스템 정보 수집")
    info_file = os.path.join(temp_dir, "wcms_system_info.txt")

    result = CommandExecutor.execute_command('execute', {
        'command': f'systeminfo > "{info_file}"'
    })
    print(result)

    if not os.path.exists(info_file):
        print_error("시스템 정보 파일 생성 실패")
        return False

    print_success(f"시스템 정보 파일 생성 완료: {info_file}")

    # 2단계: 파일 크기 확인
    print("\n[2단계] 생성된 파일 확인")
    file_size = os.path.getsize(info_file)
    print_info(f"파일 크기: {file_size:,} bytes")

    # 3단계: 파일 내용 미리보기
    print("\n[3단계] 파일 내용 미리보기")
    try:
        with open(info_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(500)
            print(content[:500])
    except Exception as e:
        print_error(f"파일 읽기 실패: {e}")

    # 정리
    try:
        os.remove(info_file)
        print_info(f"\n임시 파일 삭제: {info_file}")
    except:
        pass

    return True

# ==================== 메인 실행 ====================

def run_all_tests():
    """모든 테스트 실행"""
    print("=" * 70)
    print("WCMS 명령 실행 기능 테스트")
    print("=" * 70)

    results = {}

    # 1. CMD 명령 테스트
    results['cmd_commands'] = test_cmd_commands()

    # 2. winget 설치 테스트
    results['winget_install'] = test_winget_install()

    # 3. 파일 다운로드 테스트
    results['file_download'] = test_file_download()

    # 4. 통합 시나리오
    results['integration'] = test_integration_scenario()

    # 결과 요약
    print(f"\n{Colors.CYAN}{'='*70}")
    print("테스트 결과 요약")
    print(f"{'='*70}{Colors.END}")

    success_count = sum(1 for v in results.values() if v)
    total_count = len(results)

    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        color = Colors.GREEN if result else Colors.RED
        print(f"{color}{status}{Colors.END} - {test_name}")

    print(f"\n{Colors.CYAN}{'='*70}")
    print(f"전체: {success_count}/{total_count} 테스트 성공")
    print(f"{'='*70}{Colors.END}")

    return success_count == total_count

if __name__ == "__main__":
    print_info("WCMS 명령 실행 기능 테스트를 시작합니다.\n")
    print_warning("⚠️  일부 테스트는 실제 시스템을 변경할 수 있습니다.")
    print_info("안전한 테스트만 실행됩니다.\n")

    success = run_all_tests()

    if success:
        print(f"\n{Colors.GREEN}✅ 모든 테스트가 성공했습니다! 🎉{Colors.END}")
        sys.exit(0)
    else:
        print(f"\n{Colors.YELLOW}⚠️  일부 테스트가 실패했습니다.{Colors.END}")
        sys.exit(1)

