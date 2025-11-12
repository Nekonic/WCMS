import os
import time
import threading
import json
import psutil
import requests
from collector import collect_static_info, collect_dynamic_info
from executor import CommandExecutor

SERVER_URL = "http://10.211.55.2:5050/"
MACHINE_ID = next(
    (addr.address.replace(':', '').replace('-', '') for interface, addrs in psutil.net_if_addrs().items()
     for addr in addrs if addr.family == psutil.AF_LINK),
    "MACHINE-DEFAULT"
)

print(f"[*] Machine ID: {MACHINE_ID}")


def register_client():
    """서버에 클라이언트 정보를 등록"""
    static_info = collect_static_info()
    if not static_info:
        print("[!] 정적 정보 수집 실패, 등록할 수 없습니다.")
        return False

    reg_data = {
        "machine_id": MACHINE_ID,
        **static_info
    }

    try:
        print("[*] 서버에 클라이언트 등록 시도...")
        r = requests.post(f"{SERVER_URL}api/client/register", json=reg_data, timeout=10)
        if r.status_code == 200:
            result = r.json()
            print(f"[+] 등록 성공: {result.get('message')}")
            return True
        elif r.status_code == 500 and "이미 등록된 PC" in r.json().get('message', ''):
            print("[*] 이미 등록된 PC입니다. Heartbeat를 시작합니다.")
            return True
        else:
            print(f"[-] 등록 실패: {r.status_code} - {r.text}")
            return False
    except Exception as e:
        print(f"[-] 등록 중 오류 발생: {e}")
        return False


def send_heartbeat():
    """서버에 동적 정보를 Heartbeat로 전송"""
    dynamic_info = collect_dynamic_info()
    if not dynamic_info:
        print("[!] 동적 정보 수집 실패, Heartbeat를 보낼 수 없습니다.")
        return

    data = {
        "machine_id": MACHINE_ID,
        "system_info": dynamic_info
    }

    try:
        r = requests.post(f"{SERVER_URL}api/client/heartbeat", json=data, timeout=5)
        if r.status_code == 200:
            print("[+] Heartbeat: OK")
        elif r.status_code == 404:
            print("[!] Heartbeat 실패: 서버에 등록되지 않은 PC입니다. 재등록을 시도합니다.")
            register_client()  # 재등록 시도
        else:
            print(f"[-] Heartbeat 실패: {r.status_code}")
    except Exception as e:
        print(f"[-] Heartbeat 오류: {e}")


def poll_command():
    """Long-polling으로 명령 대기"""
    while True:
        try:
            r = requests.get(
                f"{SERVER_URL}api/client/command?machine_id={MACHINE_ID}",
                timeout=30
            )
            if r.status_code == 200:
                cmd_data = r.json()
                if cmd_data and cmd_data.get('command_type'):
                    cmd_type = cmd_data['command_type']
                    cmd_params = json.loads(cmd_data.get('command_data', '{}'))
                    print(f"\n[>>>] 명령 수신: {cmd_type} | 파라미터: {cmd_params}")
                    result = CommandExecutor.execute_command(cmd_type, cmd_params)
                    print(f"[<<<] 결과: {result}\n")
        except requests.exceptions.Timeout:
            continue
        except Exception as e:
            print(f"[-] 명령 조회 오류: {e}")
            time.sleep(5)


def heartbeat_thread():
    """10분 주기로 Heartbeat 전송"""
    while True:
        send_heartbeat()
        time.sleep(600)  # 10분 대기


if __name__ == "__main__":
    print("[*] WCMS 클라이언트 시작...")

    # 시작 시 먼저 등록 시도
    if not register_client():
        print("[!] 초기 등록 실패. 1분 후 재시도합니다.")
        time.sleep(60)
        if not register_client():
            print("[!] 재등록 실패. 프로그램을 종료합니다.")
            exit(1)

    # Heartbeat를 백그라운드 스레드에서 실행
    hb_thread = threading.Thread(target=heartbeat_thread, daemon=True)
    hb_thread.start()

    # 메인 스레드에서 명령 long-polling
    print("[*] 명령 대기 중...")
    poll_command()
