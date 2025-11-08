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
    """5초마다 heartbeat 전송 (상태 유지 + 등록)"""
    data = {
        "machine_id": MACHINE_ID,
        "system_info": collect_system_info()
    }
    try:
        r = requests.post(f"{SERVER_URL}api/client/heartbeat", json=data)

        if r.status_code == 404:
            print("[!] 미등록 PC → 등록 시작")
            for seat in range(1, 41):
                reg_data = {
                    "machine_id": MACHINE_ID,
                    "hostname": "WCMS-CLIENT",
                    "room_name": "1실습실",
                    "seat_number": seat
                }
                r = requests.post(f"{SERVER_URL}api/client/register", json=reg_data)
                if r.status_code == 200:
                    print(f"[+] 좌석 {seat}에 등록 성공")
                    break
                elif r.status_code != 409:  # 409 = UNIQUE constraint
                    break
        elif r.status_code == 200:
            print(f"[+] Heartbeat: OK")
        else:
            print(f"[-] Heartbeat 오류: {r.status_code}")
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
