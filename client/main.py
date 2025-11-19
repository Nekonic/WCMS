import time
import threading
import json
import psutil
import requests
from datetime import datetime
from collector import collect_static_info, collect_dynamic_info
from executor import CommandExecutor

SERVER_URL = "http://aps.or.kr:8057/"
MACHINE_ID = next(
    (addr.address.replace(':', '').replace('-', '') for interface, addrs in psutil.net_if_addrs().items()
     for addr in addrs if addr.family == psutil.AF_LINK),
    "MACHINE-DEFAULT"
)

# 부팅 시간 기록 (전원 관리 명령 유예 시간 계산용)
BOOT_TIME = datetime.now()
POWER_COMMAND_GRACE_PERIOD = 60  # 부팅 후 60초 동안은 전원 명령 실행 안 함

print(f"[*] Machine ID: {MACHINE_ID}")
print(f"[*] 부팅 시간: {BOOT_TIME.strftime('%Y-%m-%d %H:%M:%S')}")


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


def is_power_command(cmd_type, cmd_params):
    """전원 관리 명령인지 확인"""
    if cmd_type == 'power':
        return True
    if cmd_type in ['shutdown', 'reboot']:
        return True
    # execute 타입 중에서 shutdown 관련 명령 체크
    if cmd_type == 'execute' and cmd_params.get('command'):
        cmd = cmd_params['command'].lower()
        if 'shutdown' in cmd or 'restart' in cmd or 'logoff' in cmd:
            return True
    return False


def should_skip_command(cmd_type, cmd_params):
    """명령을 건너뛰어야 하는지 확인"""
    # 전원 관리 명령인지 확인
    if not is_power_command(cmd_type, cmd_params):
        return False

    # 부팅 후 유예 시간 확인
    elapsed = (datetime.now() - BOOT_TIME).total_seconds()
    if elapsed < POWER_COMMAND_GRACE_PERIOD:
        print(f"[!] 전원 관리 명령이지만 부팅 후 {int(elapsed)}초 경과 (유예 시간: {POWER_COMMAND_GRACE_PERIOD}초)")
        print(f"[!] 안전을 위해 이 명령을 건너뜁니다.")
        return True

    return False


def poll_command():
    """Long-polling으로 명령 대기"""
    while True:
        try:
            r = requests.get(
                f"{SERVER_URL}api/client/command",
                params={"machine_id": MACHINE_ID, "timeout": 30},
                timeout=35
            )
            if r.status_code == 200:
                cmd_data = r.json()
                if cmd_data and cmd_data.get('command_type'):
                    cmd_id = cmd_data.get('command_id')
                    cmd_type = cmd_data['command_type']
                    cmd_params = json.loads(cmd_data.get('command_data', '{}'))

                    print(f"\n[>>>] 명령 수신: {cmd_type} | 파라미터: {cmd_params}")

                    # 전원 관리 명령이면서 유예 시간 내라면 건너뛰기
                    if should_skip_command(cmd_type, cmd_params):
                        result = f"⏭️ 명령 건너뜀: 부팅 후 {POWER_COMMAND_GRACE_PERIOD}초 이내의 전원 관리 명령은 안전을 위해 실행하지 않습니다."
                        print(f"[<<<] {result}\n")
                        send_command_result(cmd_id, 'skipped', result)
                        continue

                    # 전원 관리 명령이면 추가 경고 출력
                    if is_power_command(cmd_type, cmd_params):
                        elapsed = (datetime.now() - BOOT_TIME).total_seconds()
                        print(f"[⚠️] 전원 관리 명령 실행 (부팅 후 {int(elapsed)}초 경과)")

                    # 명령 실행
                    result = CommandExecutor.execute_command(cmd_type, cmd_params)
                    print(f"[<<<] 결과: {result}\n")

                    # 결과를 서버로 보고
                    send_command_result(cmd_id, 'completed', result)

        except requests.exceptions.Timeout:
            continue
        except Exception as e:
            print(f"[-] 명령 조회 오류: {e}")
            time.sleep(5)


def send_command_result(command_id, status, result):
    """명령 실행 결과를 서버로 보고"""
    try:
        data = {
            "machine_id": MACHINE_ID,
            "command_id": command_id,
            "status": status,
            "result": result
        }
        r = requests.post(f"{SERVER_URL}api/client/command/result", json=data, timeout=5)
        if r.status_code == 200:
            print(f"[+] 명령 결과 전송 완료: CMD#{command_id}")
        else:
            print(f"[-] 명령 결과 전송 실패: {r.status_code}")
    except Exception as e:
        print(f"[-] 명령 결과 전송 오류: {e}")


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
