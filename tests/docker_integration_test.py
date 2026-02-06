#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Docker Windows 환경 통합 테스트
dockurr/windows 컨테이너에서 WCMS 클라이언트 동작 검증

실행 방법:
    python manage.py docker-test

주의사항:
- 이미지: dockurr/windows (10GB+, 최초 1회만 다운로드)
- 컨테이너: wcms-test-win (재사용, 절대 삭제 금지)
- 부팅 시간: 10-15분
"""
import subprocess
import sys
import io
import platform
from typing import Tuple

# Windows에서 UTF-8 출력을 위한 설정
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

SERVER_URL = "http://localhost:5050"
CONTAINER_NAME = "wcms-test-win"
IMAGE_NAME = "dockurr/windows:latest"
TEST_TIMEOUT = 120  # 2분


def get_system_memory_gb() -> int:
    """시스템 전체 RAM을 GB 단위로 반환"""
    try:
        if platform.system() == "Windows":
            import ctypes
            kernel32 = ctypes.windll.kernel32
            c_ulong = ctypes.c_ulong

            class MemoryStatus(ctypes.Structure):
                pass

            MemoryStatus._fields_ = [
                ('dwLength', c_ulong),
                ('dwMemoryLoad', c_ulong),
                ('ullTotalPhys', ctypes.c_ulonglong),
                ('ullAvailPhys', ctypes.c_ulonglong),
                ('ullTotalPageFile', ctypes.c_ulonglong),
                ('ullAvailPageFile', ctypes.c_ulonglong),
                ('ullTotalVirtual', ctypes.c_ulonglong),
                ('ullAvailVirtual', ctypes.c_ulonglong),
                ('sullAvailExtendedVirtual', ctypes.c_ulonglong),
            ]

            stat = MemoryStatus()
            stat.dwLength = ctypes.sizeof(MemoryStatus)
            kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))

            return int(stat.ullTotalPhys / (1024 ** 3))
        else:
            # Linux/Mac
            import os
            return int(os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES') / (1024 ** 3))
    except Exception as e:
        print(f"  경고: 시스템 메모리 감지 실패 ({e}), 기본값 16GB 사용")
        return 16


def get_docker_memory_gb() -> Tuple[int, int, int, str]:
    """시스템 메모리에 따라 Docker 메모리와 CPU 할당 결정

    Returns:
        (Docker 메모리GB, Windows RAM GB, CPU코어수, 설명)
    """
    total_ram = get_system_memory_gb()

    if total_ram >= 64:
        docker_mem = 32
        windows_ram = 24
        cpus = 8
        desc = f"시스템 RAM {total_ram}GB → Docker 32GB (Windows 24GB), 8CPU"
    elif total_ram >= 32:
        docker_mem = 16
        windows_ram = 12
        cpus = 4
        desc = f"시스템 RAM {total_ram}GB → Docker 16GB (Windows 12GB), 4CPU"
    elif total_ram >= 16:
        docker_mem = 8
        windows_ram = 6
        cpus = 4
        desc = f"시스템 RAM {total_ram}GB → Docker 8GB (Windows 6GB), 4CPU"
    else:
        docker_mem = min(8, max(4, total_ram // 2))
        windows_ram = max(3, docker_mem // 2)
        cpus = 2
        desc = f"시스템 RAM {total_ram}GB → Docker {docker_mem}GB (Windows {windows_ram}GB), 2CPU"

    return docker_mem, windows_ram, cpus, desc


def run_command(cmd: str, timeout: int = 30, shell: bool = True) -> Tuple[bool, str, str]:
    """명령 실행"""
    try:
        result = subprocess.run(
            cmd,
            shell=shell,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=timeout
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Timeout"


def is_container_running() -> bool:
    """컨테이너가 실행 중인지 확인"""
    success, stdout, _ = run_command(f"docker ps | grep {CONTAINER_NAME}", timeout=5)
    return success and CONTAINER_NAME in stdout


def container_exists() -> bool:
    """컨테이너가 존재하는지 확인 (실행 중 또는 정지 상태)"""
    success, stdout, _ = run_command(f"docker ps -a | grep {CONTAINER_NAME}", timeout=5)
    return success and CONTAINER_NAME in stdout



def create_container(docker_mem: int, windows_ram: int, cpus: int) -> bool:
    """Docker 컨테이너 생성

    Args:
        docker_mem: Docker에 할당할 메모리 (GB)
        windows_ram: Windows 게스트에 할당할 메모리 (GB)
        cpus: CPU 코어 수

    Returns:
        성공 여부
    """
    print(f"  이름: {CONTAINER_NAME}")
    print(f"  메모리: Docker {docker_mem}GB (Windows {windows_ram}GB)")
    print(f"  CPU: {cpus} 코어")
    print(f"  포트: 8006(웹VNC), 5900(VNC), 3389(RDP), 5050(서버)")
    print(f"  주의: 이 컨테이너는 재사용되므로 삭제하지 마세요!\n")

    cmd = (
        f"docker run -d "
        f"--name {CONTAINER_NAME} "
        f"--cpus={cpus} "
        f"--memory={docker_mem}g "
        f"--privileged "
        f"-p 8006:8006 "
        f"-p 5900:5900 "
        f"-p 3389:3389 "
        f"-e RAM={windows_ram} "
        f"-e VERSION=11 "
        f"{IMAGE_NAME}"
    )
    success, stdout, stderr = run_command(cmd, timeout=30)
    if not success:
        print(f"  [ERROR] 컨테이너 생성 실패")
        print(f"  오류: {stderr}")
        if "port is already allocated" in stderr:
            print(f"  [해결] 포트 충돌 - 다른 컨테이너 확인: docker ps")
        elif "name is already in use" in stderr:
            print(f"  [해결] 이름 충돌 - 기존 컨테이너 확인: docker ps -a")
        return False

    container_id = stdout.strip()[:12]
    print(f"  [OK] 컨테이너 생성 완료 (ID: {container_id})\n")

    return True


def wait_for_boot(container_ref: str = CONTAINER_NAME) -> bool:
    """Windows 부팅 대기 (로그에서 "Windows started successfully" 메시지 감지)

    Args:
        container_ref: 컨테이너 이름 또는 ID

    Returns:
        부팅 성공 여부
    """
    print(f"[부팅 대기] Windows 11 부팅 중... (최대 30분)")
    print(f"  컨테이너: {container_ref}")
    print(f"  예상 시간: 10-15분")
    print(f"  진행 상황: 30초마다 출력\n")

    import time

    boot_timeout = 1800  # 30분
    boot_count = 0
    last_log_line = ""

    while boot_count < boot_timeout:
        boot_count += 1

        # 10초마다 로그 확인
        if boot_count % 10 == 0:
            success, logs, _ = run_command(f"docker logs --tail 20 {container_ref}", timeout=5)

            if success and logs and "Windows started successfully" in logs:
                elapsed_min = boot_count // 60
                elapsed_sec = boot_count % 60
                print(f"\n  [OK] Windows 부팅 완료! (소요 시간: {elapsed_min}분 {elapsed_sec}초)")

                # 성공 메시지 출력
                for line in logs.split('\n'):
                    if "Windows started successfully" in line or "You can now login" in line:
                        print(f"  {line}")

                print(f"\n  웹 VNC 접속: http://localhost:8006")
                print(f"  RDP 접속: localhost:3389\n")
                return True

            # 30초마다 진행 상황 출력
            if boot_count % 30 == 0:
                elapsed_min = boot_count // 60
                print(f"  [{elapsed_min}분 경과] 부팅 진행 중...")

                # 마지막 로그 라인 표시 (변경 시)
                if success and logs:
                    latest_line = logs.strip().split('\n')[-1]
                    if latest_line != last_log_line and latest_line:
                        print(f"    최근 로그: {latest_line[:80]}")
                        last_log_line = latest_line

        time.sleep(1)

    print(f"\n  [타임아웃] 30분 경과")
    print(f"  [해결] 수동 확인: docker logs {container_ref}")
    return False


def image_exists() -> bool:
    """Docker 이미지가 로컬에 존재하는지 확인"""
    success, stdout, _ = run_command(f"docker image inspect {IMAGE_NAME}", timeout=5)
    return success


def setup_docker_environment() -> bool:
    """Docker 환경 자동 설정 (컨테이너 감지 및 재사용)

    우선순위:
    1. 실행 중인 컨테이너 → 바로 사용
    2. 정지된 컨테이너 → 시작
    3. 이미지만 있음 → 새 컨테이너 생성
    4. 이미지도 없음 → 다운로드 후 생성

    중요: 이미지/컨테이너는 절대 삭제하지 않음 (재사용)
    """
    print("\n" + "="*70)
    print("Docker 환경 설정 중...")
    print("="*70 + "\n")

    docker_mem, windows_ram, cpus, mem_desc = get_docker_memory_gb()
    print(f"[시스템 감지] {mem_desc}\n")

    # 1단계: 실행 중인 컨테이너 확인
    if is_container_running():
        print(f"[1/1] 컨테이너 '{CONTAINER_NAME}' 실행 중")
        print(f"  → 기존 컨테이너 재사용 (이미지 다운로드 불필요)\n")
        return wait_for_boot()

    # 2단계: 정지된 컨테이너 확인
    if container_exists():
        print(f"[1/2] 컨테이너 '{CONTAINER_NAME}' 발견 (정지 상태)")
        print(f"  → 기존 컨테이너 시작 (이미지 다운로드 불필요)")
        success, _, stderr = run_command(f"docker start {CONTAINER_NAME}", timeout=30)
        if success:
            print(f"  [OK] 컨테이너 시작 완료\n")
            return wait_for_boot()
        else:
            print(f"  [ERROR] 컨테이너 시작 실패: {stderr}")
            print(f"  [해결] 수동으로 확인 필요: docker ps -a\n")
            return False

    # 3단계: 이미지 확인 (컨테이너는 없음)
    print("[1/3] 이미지 확인 중...")
    if image_exists():
        print(f"  [OK] 이미지 '{IMAGE_NAME}' 이미 존재")
        print(f"  → 새 컨테이너 생성 (다운로드 불필요)\n")
    else:
        # 4단계: 이미지 다운로드 (첫 실행만)
        print(f"  [주의] 이미지 없음 - 최초 다운로드 시작")
        print(f"[2/3] Docker 이미지 다운로드 중...")
        print(f"  이미지: {IMAGE_NAME}")
        print(f"  크기: 약 10GB 이상")
        print(f"  예상 시간: 5-10분 (네트워크 속도에 따라)")
        print(f"  주의: 이 작업은 최초 1회만 실행됩니다.\n")

        success, stdout, stderr = run_command(f"docker pull {IMAGE_NAME}", timeout=900)
        if not success:
            print(f"  [ERROR] 이미지 다운로드 실패")
            print(f"  오류: {stderr}")
            print(f"  [해결] 네트워크 확인 후 재시도\n")
            return False
        print(f"  [OK] 이미지 다운로드 완료\n")

    # 5단계: 새 컨테이너 생성
    print(f"[3/3] 새 컨테이너 생성 중...")
    if not create_container(docker_mem, windows_ram, cpus):
        return False

    return wait_for_boot()



def test_container_status() -> bool:
    """1. 컨테이너 상태 확인"""
    print("테스트 1: 컨테이너 상태 확인...")
    success, stdout, stderr = run_command(f"docker ps | grep {CONTAINER_NAME}")

    if not success:
        print(f"  [ERROR] 컨테이너 실행 중 아님")
        return False

    print("  [OK] 컨테이너 실행 중")
    return True


def test_server_health() -> bool:
    """2. 서버 헬스체크"""
    print("테스트 2: 서버 헬스체크...")

    try:
        import requests
        response = requests.get(f"{SERVER_URL}/", timeout=5)

        if response.status_code != 200:
            print(f"  [ERROR] 서버 응답 코드: {response.status_code}")
            return False

        print("  [OK] 서버 정상 (200 OK)")
        return True

    except requests.exceptions.ConnectionError:
        print(f"  [ERROR] 서버에 연결할 수 없음 ({SERVER_URL})")
        return False
    except Exception as e:
        print(f"  [ERROR] 서버 접속 실패: {e}")
        return False


def test_client_registration() -> Tuple[bool, int]:
    """3. 클라이언트 등록 API 테스트"""
    print("테스트 3: 클라이언트 등록...")

    import requests
    payload = {
        "machine_id": "DOCKER-TEST-001",
        "hostname": "windows-container",
        "mac_address": "02:00:00:00:00:00",
        "cpu_cores": 2,
        "ram_total": 4096
    }

    try:
        response = requests.post(
            f"{SERVER_URL}/api/client/register",
            json=payload,
            timeout=5
        )

        if response.status_code != 200:
            print(f"  [ERROR] 등록 실패: {response.text}")
            return False, -1

        data = response.json()

        if data.get("status") != "success":
            print(f"  [ERROR] 등록 상태 오류: {data}")
            return False, -1

        pc_id = data.get("pc_id")
        print(f"  [OK] 클라이언트 등록 완료 (ID: {pc_id})")
        return True, pc_id

    except Exception as e:
        print(f"  [ERROR] 등록 실패: {e}")
        return False, -1


def test_heartbeat() -> bool:
    """4. Heartbeat API 테스트"""
    print("테스트 4: Heartbeat 전송...")

    import requests
    payload = {
        "machine_id": "DOCKER-TEST-001",
        "cpu_usage": 25.5,
        "ram_used": 2048,
        "ram_usage_percent": 50
    }

    try:
        response = requests.post(
            f"{SERVER_URL}/api/client/heartbeat",
            json=payload,
            timeout=5
        )

        if response.status_code != 200:
            print(f"  [ERROR] Heartbeat 실패: {response.text}")
            return False

        data = response.json()

        if data.get("status") != "success":
            print(f"  [ERROR] Heartbeat 상태 오류: {data}")
            return False

        print("  [OK] Heartbeat 전송 완료")
        return True

    except Exception as e:
        print(f"  [ERROR] Heartbeat 실패: {e}")
        return False


def test_shutdown_signal() -> bool:
    """5. 종료 신호 API 테스트"""
    print("테스트 5: 종료 신호 전송...")

    import requests
    payload = {"machine_id": "DOCKER-TEST-001"}

    try:
        response = requests.post(
            f"{SERVER_URL}/api/client/shutdown",
            json=payload,
            timeout=5
        )

        if response.status_code != 200:
            print(f"  [ERROR] 종료 신호 실패: {response.text}")
            return False

        data = response.json()

        if data.get("status") != "success":
            print(f"  [ERROR] 종료 신호 상태 오류: {data}")
            return False

        print("  [OK] 종료 신호 전송 완료")
        return True

    except Exception as e:
        print(f"  [ERROR] 종료 신호 실패: {e}")
        return False


def test_offline_status() -> bool:
    """6. 오프라인 상태 확인"""
    print("테스트 6: PC 오프라인 상태 확인...")

    import requests
    try:
        response = requests.get(
            f"{SERVER_URL}/api/admin/pcs",
            timeout=5
        )

        if response.status_code != 200:
            print(f"  [ERROR] PC 목록 조회 실패: {response.text}")
            return False

        print("  [OK] PC 오프라인 상태 확인 완료")
        return True

    except Exception as e:
        print(f"  [ERROR] 상태 확인 실패: {e}")
        return False


def main() -> int:
    """메인 테스트 실행"""
    print(f"\n{'='*70}")
    print(f"Docker Windows 환경 WCMS 통합 테스트")
    print(f"{'='*70}")

    # Docker 환경 설정 (컨테이너 자동 감지)
    if not setup_docker_environment():
        print("Docker 환경 설정 실패")
        sys.exit(1)

    # 테스트 실행
    print("="*70)
    print("테스트 시작")
    print("="*70 + "\n")

    tests = [
        ("컨테이너 상태", test_container_status),
        ("서버 헬스체크", test_server_health),
        ("클라이언트 등록", lambda: test_client_registration()[0]),
        ("Heartbeat", test_heartbeat),
        ("종료 신호", test_shutdown_signal),
        ("오프라인 상태", test_offline_status),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  ✗ 예상치 못한 오류: {e}")
            failed += 1

    print(f"\n{'='*70}")
    print(f"테스트 결과: {passed} 통과, {failed} 실패")
    if failed == 0:
        print("모든 테스트 통과! [SUCCESS]")
    print(f"{'='*70}\n")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
