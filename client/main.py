import os
import time
import threading
import json
import psutil
import requests
from collector import collect_system_info
from executor import CommandExecutor

SERVER_URL = "http://10.211.55.2:5050/"
MACHINE_ID = next(
    (addr.address.replace(':', '') for interface, addrs in psutil.net_if_addrs().items()
     for addr in addrs if addr.family == psutil.AF_LINK),
    "MACHINE-DEFAULT"
)

print(f"[*] Machine ID: {MACHINE_ID}")


def register_or_heartbeat():
    """5초마다 heartbeat 전송"""
    data = {
        "machine_id": MACHINE_ID,
        "system_info": collect_system_info()
    }
    try:
        r = requests.post(f"{SERVER_URL}api/client/heartbeat", json=data, timeout=5)

        if r.status_code == 404:
            # 미등록 PC → 간단한 등록 요청
            print("[!] 미등록 PC → 서버에 등록 요청")
            reg_data = {
                "machine_id": MACHINE_ID,
                "hostname": os.getenv('COMPUTERNAME', 'WCMS-CLIENT'),
                "ip_address": collect_system_info().get('ip_address')
            }

            r = requests.post(f"{SERVER_URL}api/client/register", json=reg_data, timeout=5)
            if r.status_code == 200:
                result = r.json()
                print(f"[+] 등록 성공: {result.get('room_name')} - {result.get('seat_number')}번")
            elif r.status_code == 202:
                print("[-] 등록 대기 중... (관리자 승인 필요)")
        elif r.status_code == 200:
            print("[+] Heartbeat: OK")
    except Exception as e:
        print(f"[-] Heartbeat 오류: {e}")

def poll_command():
    """Long-polling으로 명령 대기 (이벤트 기반)"""
    while True:
        try:
            # 30초 타임아웃으로 대기
            r = requests.get(
                f"{SERVER_URL}api/client/command?machine_id={MACHINE_ID}",
                timeout=30
            )

            if r.status_code == 200:
                cmd_data = r.json()
                cmd_type = cmd_data.get('command_type')
                cmd_params = json.loads(cmd_data.get('command_data', '{}'))

                if cmd_type:
                    print(f"\n[>>>] 명령 수신: {cmd_type} | 파라미터: {cmd_params}")
                    result = CommandExecutor.execute_command(cmd_type, cmd_params)
                    print(f"[<<<] 결과: {result}\n")

                    # 실행 결과 서버에 전송 (옵션)
                    # send_command_result(cmd_id, result)

        except requests.exceptions.Timeout:
            # 타임아웃은 정상 (명령 없음)
            continue
        except Exception as e:
            print(f"[-] 명령 조회 오류: {e}")
            time.sleep(5)


def heartbeat_thread():
    """별도 스레드에서 5초마다 heartbeat"""
    while True:
        register_or_heartbeat()
        time.sleep(5)


if __name__ == "__main__":
    print("[*] WCMS 클라이언트 시작...")

    # Heartbeat를 백그라운드 스레드에서 실행
    hb_thread = threading.Thread(target=heartbeat_thread, daemon=True)
    hb_thread.start()

    # 메인 스레드에서 명령 long-polling (블로킹)
    print("[*] 명령 대기 중...")
    poll_command()
