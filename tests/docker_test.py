#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WCMS Docker 통합 테스트 (개선 버전)
- Docker Compose 기반
- dockurr/windows 사용
- VNC 접속 지원
- 안정적인 부팅 대기 및 헬스체크

실행 방법:
    python tests/docker_test.py [--rebuild] [--no-cache]

옵션:
    --rebuild: 서버 이미지 강제 재빌드
    --no-cache: Docker 빌드 캐시 사용 안 함
    --cleanup: 테스트 후 컨테이너 정리
"""
import argparse
import subprocess
import sys
import time
import platform
from pathlib import Path
from typing import Tuple, Dict

# 프로젝트 루트 경로
PROJECT_ROOT = Path(__file__).parent.parent
COMPOSE_FILE = PROJECT_ROOT / "docker-compose.yml"
ENV_FILE = PROJECT_ROOT / ".env.docker"

# 컨테이너 이름
SERVER_CONTAINER = "wcms-server"
WIN_CONTAINER = "wcms-test-win"

# 접속 정보
SERVER_URL = "http://localhost:5050"
VNC_WEB_URL = "http://localhost:8006"
VNC_PORT = 5900
RDP_PORT = 3389


class Colors:
    """터미널 색상"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(msg: str):
    """헤더 출력"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{msg}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 70}{Colors.ENDC}\n")


def print_info(msg: str):
    """정보 메시지"""
    print(f"{Colors.OKBLUE}[INFO]{Colors.ENDC} {msg}")


def print_success(msg: str):
    """성공 메시지"""
    print(f"{Colors.OKGREEN}[OK]{Colors.ENDC} {msg}")


def print_warning(msg: str):
    """경고 메시지"""
    print(f"{Colors.WARNING}[WARN]{Colors.ENDC} {msg}")


def print_error(msg: str):
    """에러 메시지"""
    print(f"{Colors.FAIL}[ERROR]{Colors.ENDC} {msg}")


def run_cmd(cmd: str, timeout: int = 30, check: bool = True) -> Tuple[bool, str, str]:
    """명령 실행"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=timeout,
            check=False
        )
        success = result.returncode == 0
        if check and not success:
            print_error(f"명령 실패: {cmd}")
            if result.stderr:
                print(f"  {result.stderr}")
        return success, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        print_error(f"명령 타임아웃: {cmd}")
        return False, "", "Timeout"
    except Exception as e:
        print_error(f"명령 실행 오류: {e}")
        return False, "", str(e)


def check_prerequisites() -> bool:
    """사전 요구사항 확인"""
    print_header("사전 요구사항 확인")

    # Docker 설치 확인
    print_info("Docker 설치 확인...")
    success, stdout, _ = run_cmd("docker --version", check=False)
    if not success:
        print_error("Docker가 설치되지 않았습니다")
        print("  설치: https://www.docker.com/products/docker-desktop")
        return False
    print_success(f"Docker 설치됨: {stdout.strip()}")

    # Docker Compose 확인
    print_info("Docker Compose 확인...")
    success, stdout, _ = run_cmd("docker compose version", check=False)
    if not success:
        print_error("Docker Compose가 설치되지 않았습니다")
        return False
    print_success(f"Docker Compose: {stdout.strip()}")

    # Docker 실행 확인
    print_info("Docker 데몬 확인...")
    success, _, _ = run_cmd("docker ps", check=False)
    if not success:
        print_error("Docker 데몬이 실행되지 않았습니다")
        print("  Windows: Docker Desktop 실행")
        print("  Linux: sudo systemctl start docker")
        return False
    print_success("Docker 데몬 실행 중")

    # 설정 파일 확인
    print_info("설정 파일 확인...")
    if not COMPOSE_FILE.exists():
        print_error(f"docker-compose.yml 없음: {COMPOSE_FILE}")
        return False
    print_success(f"docker-compose.yml 존재")

    if not ENV_FILE.exists():
        print_warning(f".env.docker 없음 (기본값 사용): {ENV_FILE}")
    else:
        print_success(f".env.docker 존재")

    # KVM 확인 (Linux만)
    if platform.system() == "Linux":
        print_info("KVM 지원 확인...")
        success, _, _ = run_cmd("ls /dev/kvm", check=False)
        if not success:
            print_warning("KVM이 활성화되지 않았습니다 (Windows 부팅 느려질 수 있음)")
            print("  활성화: sudo modprobe kvm")
        else:
            print_success("KVM 지원")

    return True


def get_system_resources() -> Dict[str, int]:
    """시스템 리소스 감지"""
    total_ram_gb = 16
    cpu_count = 4

    try:
        import psutil
        total_ram_gb = int(psutil.virtual_memory().total / (1024 ** 3))
        cpu_count = psutil.cpu_count(logical=False) or 4
    except ImportError:
        print_warning("psutil 미설치, 기본값 사용")

    # Docker 할당 계산
    if total_ram_gb >= 64:
        docker_ram = 24
        docker_cpus = 8
    elif total_ram_gb >= 32:
        docker_ram = 12
        docker_cpus = 4
    elif total_ram_gb >= 16:
        docker_ram = 8
        docker_cpus = 4
    else:
        docker_ram = 6
        docker_cpus = 2

    return {
        "total_ram": total_ram_gb,
        "docker_ram": docker_ram,
        "docker_cpus": docker_cpus,
    }


def update_env_file():
    """환경 파일 업데이트 (리소스 자동 설정)"""
    resources = get_system_resources()
    print_info(f"시스템 메모리: {resources['total_ram']}GB")
    print_info(f"Docker 할당: RAM={resources['docker_ram']}G, CPU={resources['docker_cpus']}")

    if not ENV_FILE.exists():
        print_warning(".env.docker 없음, 생성 중...")
        ENV_FILE.write_text(
            f"# WCMS Docker 환경 변수 (자동 생성)\n"
            f"WCMS_SECRET_KEY=docker-test-secret-key\n"
            f"WCMS_ENV=development\n"
            f"DOCKER_WIN_RAM={resources['docker_ram']}G\n"
            f"DOCKER_WIN_CPUS={resources['docker_cpus']}\n"
            f"VNC_PASSWORD=wcms2026\n"
            f"WIN_PASSWORD=Wcms2026!\n"
        )
        print_success(".env.docker 생성 완료")


def start_services(rebuild: bool = False, no_cache: bool = False) -> bool:
    """Docker Compose 서비스 시작"""
    print_header("Docker 서비스 시작")

    # 환경 파일 업데이트
    update_env_file()

    # DB 자동 초기화 안내
    print_info("서버 컨테이너는 자동으로 DB를 초기화합니다")
    print_info("  - 스키마 적용: server/migrations/schema.sql")
    print_info("  - 기본 계정: admin / admin")

    # 빌드 옵션
    build_cmd = "docker compose --env-file .env.docker"
    if rebuild:
        print_info("서버 이미지 재빌드 중...")
        cache_opt = "--no-cache" if no_cache else ""
        success, _, _ = run_cmd(f"{build_cmd} build {cache_opt} wcms-server", timeout=300)
        if not success:
            print_error("서버 이미지 빌드 실패")
            return False
        print_success("서버 이미지 빌드 완료")

    # 서비스 시작
    print_info("컨테이너 시작 중...")
    print_warning("최초 실행 시:")
    print_warning("  - Windows ISO 다운로드 (5-6GB, 빠른 서버 사용)")
    print_warning("  - 부팅 시간: 10-15분")

    success, _, _ = run_cmd(f"{build_cmd} up -d", timeout=600, check=False)
    if not success:
        print_error("컨테이너 시작 실패")
        print_info("로그 확인: docker compose logs")
        return False

    print_success("컨테이너 시작 완료")
    return True


def wait_for_service(container: str, timeout: int = 120) -> bool:
    """컨테이너 헬스체크 대기"""
    print_info(f"{container} 헬스체크 대기 중... (최대 {timeout}초)")

    start = time.time()
    check_interval = 3

    while time.time() - start < timeout:
        elapsed = int(time.time() - start)

        # 1. 컨테이너 실행 상태 확인
        success, stdout, _ = run_cmd(
            f"docker ps --filter name={container} --format '{{{{.Status}}}}'",
            check=False
        )

        if not success or not stdout.strip():
            time.sleep(check_interval)
            continue

        # 2. Docker 헬스체크 상태 확인 (있는 경우)
        success, stdout, _ = run_cmd(
            f"docker inspect --format='{{{{.State.Health.Status}}}}' {container}",
            check=False
        )

        if success and stdout.strip():
            status = stdout.strip()
            if status == "healthy":
                print_success(f"{container} 준비 완료 ({elapsed}초)")
                return True
            elif status == "unhealthy":
                print_error(f"{container} unhealthy 상태")
                print_info(f"로그 확인: docker logs {container} --tail 20")
                return False
            # starting 상태면 계속 대기

        # 3. 헬스체크 없으면 HTTP 직접 확인 (서버만)
        if container == SERVER_CONTAINER and elapsed > 10:
            try:
                import requests
                resp = requests.get(SERVER_URL, timeout=3)
                if resp.status_code == 200:
                    print_success(f"{container} 실행 중 (HTTP 200, {elapsed}초)")
                    return True
            except:
                pass  # 아직 준비 안됨

        # 진행상황 출력
        if elapsed % 15 == 0 and elapsed > 0:
            print_info(f"{elapsed}초 경과... 대기 중")

        time.sleep(check_interval)

    print_error(f"{container} 타임아웃")
    print_info(f"로그 확인: docker logs {container} --tail 30")
    return False


def wait_for_windows_boot(timeout: int = 1800) -> bool:
    """Windows 부팅 대기 (30분)"""
    print_header("Windows 11 부팅 대기")
    print_info(f"예상 시간: 10-15분 (최대 {timeout // 60}분)")
    print_info(f"VNC 접속: {VNC_WEB_URL}")
    print_info(f"RDP 접속: localhost:{RDP_PORT}")

    start = time.time()
    last_log = ""
    check_count = 0

    while time.time() - start < timeout:
        elapsed = int(time.time() - start)
        check_count += 1

        # 30초마다 진행 상황 출력
        if check_count % 15 == 0:
            print_info(f"{elapsed // 60}분 경과... 부팅 진행 중")

        # 로그 확인
        success, logs, _ = run_cmd(
            f"docker logs --tail 50 {WIN_CONTAINER}",
            timeout=10,
            check=False
        )

        if success and logs:
            # 부팅 완료 감지
            if "Windows started successfully" in logs or "Ready for use" in logs:
                print_success(f"Windows 부팅 완료! ({elapsed // 60}분 {elapsed % 60}초)")
                print_success(f"웹 VNC: {VNC_WEB_URL}")
                return True

            # 새 로그 출력
            lines = logs.strip().split('\n')
            if lines and lines[-1] != last_log:
                last_log = lines[-1]
                if check_count % 5 == 0:  # 10초마다
                    print(f"  {last_log[:100]}")

        time.sleep(2)

    print_error(f"부팅 타임아웃 ({timeout // 60}분)")
    print_info(f"수동 확인: docker logs {WIN_CONTAINER}")
    return False


def test_server_api() -> bool:
    """서버 API 테스트"""
    print_header("서버 API 테스트")

    try:
        import requests
    except ImportError:
        print_error("requests 라이브러리 필요: pip install requests")
        return False

    tests_passed = 0
    tests_total = 0

    # 테스트 1: 헬스체크
    tests_total += 1
    print_info("1. 서버 헬스체크...")
    try:
        resp = requests.get(f"{SERVER_URL}/", timeout=5)
        if resp.status_code == 200:
            print_success("서버 정상 응답")
            tests_passed += 1
        else:
            print_error(f"서버 응답 코드: {resp.status_code}")
    except Exception as e:
        print_error(f"서버 접속 실패: {e}")

    # 테스트 2: 클라이언트 등록
    tests_total += 1
    print_info("2. 클라이언트 등록...")
    payload = {
        "machine_id": "DOCKER-TEST-001",
        "hostname": "windows-docker",
        "mac_address": "02:00:00:00:00:01",
        "cpu_cores": 4,
        "ram_total": 8192
    }
    try:
        resp = requests.post(f"{SERVER_URL}/api/client/register", json=payload, timeout=5)
        if resp.status_code == 200 and resp.json().get("status") == "success":
            pc_id = resp.json().get("pc_id")
            print_success(f"등록 성공 (ID: {pc_id})")
            tests_passed += 1
        else:
            print_error(f"등록 실패: {resp.text}")
    except Exception as e:
        print_error(f"등록 오류: {e}")

    # 테스트 3: Heartbeat
    tests_total += 1
    print_info("3. Heartbeat 전송...")
    payload = {
        "machine_id": "DOCKER-TEST-001",
        "cpu_usage": 30.5,
        "ram_used": 4096,
        "ram_usage_percent": 50.0
    }
    try:
        resp = requests.post(f"{SERVER_URL}/api/client/heartbeat", json=payload, timeout=5)
        if resp.status_code == 200 and resp.json().get("status") == "success":
            print_success("Heartbeat 성공")
            tests_passed += 1
        else:
            print_error(f"Heartbeat 실패: {resp.text}")
    except Exception as e:
        print_error(f"Heartbeat 오류: {e}")

    print(f"\n테스트 결과: {tests_passed}/{tests_total} 통과")
    return tests_passed == tests_total


def show_access_info():
    """접속 정보 출력"""
    print_header("접속 정보")
    print(f"  WCMS 서버:  {SERVER_URL}")
    print(f"  웹 VNC:     {VNC_WEB_URL}")
    print(f"  VNC 포트:   localhost:{VNC_PORT}")
    print(f"  RDP 포트:   localhost:{RDP_PORT}")
    print(f"\n  Windows 로그인:")
    print(f"    - 사용자: Administrator")
    print(f"    - 비밀번호: Wcms2026!")
    print(f"\n  컨테이너 관리:")
    print(f"    - 로그 확인: docker compose logs -f")
    print(f"    - 중지: docker compose down")
    print(f"    - 재시작: docker compose restart")


def cleanup_services():
    """서비스 정리"""
    print_header("서비스 정리")
    print_info("컨테이너 중지 및 제거...")
    run_cmd("docker compose --env-file .env.docker down", timeout=60)
    print_success("정리 완료")


def main():
    """메인 실행"""
    parser = argparse.ArgumentParser(description="WCMS Docker 통합 테스트")
    parser.add_argument("--rebuild", action="store_true", help="서버 이미지 재빌드")
    parser.add_argument("--no-cache", action="store_true", help="빌드 캐시 사용 안 함")
    parser.add_argument("--cleanup", action="store_true", help="테스트 후 정리")
    parser.add_argument("--skip-boot", action="store_true", help="Windows 부팅 대기 스킵")
    args = parser.parse_args()

    try:
        # 1. 사전 확인
        if not check_prerequisites():
            return 1

        # 2. 서비스 시작
        if not start_services(rebuild=args.rebuild, no_cache=args.no_cache):
            return 1

        # 3. 서버 대기
        if not wait_for_service(SERVER_CONTAINER, timeout=120):
            print_error("서버 시작 실패")
            return 1

        # 4. Windows 부팅 대기
        if not args.skip_boot:
            if not wait_for_windows_boot(timeout=1800):
                print_warning("Windows 부팅 확인 실패 (수동 확인 필요)")

        # 5. API 테스트
        if not test_server_api():
            print_warning("일부 테스트 실패")

        # 6. 접속 정보
        show_access_info()

        # 7. 정리
        if args.cleanup:
            input("\n[Enter]를 눌러 정리 시작...")
            cleanup_services()

        print_success("\n테스트 완료!")
        return 0

    except KeyboardInterrupt:
        print_warning("\n\n사용자 중단")
        if args.cleanup:
            cleanup_services()
        return 130
    except Exception as e:
        print_error(f"\n예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
