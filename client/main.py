import threading
import json
import psutil
import requests
import os
import logging
from logging.handlers import RotatingFileHandler
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

# 서비스/콘솔 공통 종료 제어 이벤트
STOP_EVENT = threading.Event()

logger = logging.getLogger('wcms')


def setup_logging():
    global logger
    if logger.handlers:
        return logger
    try:
        log_dir = os.path.join(os.environ.get('PROGRAMDATA', os.getcwd()), 'WCMS', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, 'client.log')
        logger.setLevel(logging.INFO)
        handler = RotatingFileHandler(log_path, maxBytes=10 * 1024 * 1024, backupCount=5, encoding='utf-8')
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    except Exception as e:
        # 마지막 수단: 콘솔 핸들러
        logger.setLevel(logging.INFO)
        sh = logging.StreamHandler()
        sh.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s'))
        logger.addHandler(sh)
        logger.error(f"로그 파일 초기화 실패: {e}")
    return logger


def register_client():
    """서버에 클라이언트 정보를 등록"""
    static_info = collect_static_info()
    if not static_info:
        logger.warning("정적 정보 수집 실패, 등록할 수 없습니다.")
        return False

    reg_data = {
        "machine_id": MACHINE_ID,
        **static_info
    }

    try:
        logger.info("서버에 클라이언트 등록 시도...")
        r = requests.post(f"{SERVER_URL}api/client/register", json=reg_data, timeout=10)
        if r.status_code == 200:
            result = r.json()
            logger.info(f"등록 성공: {result.get('message')}")
            return True
        elif r.status_code == 500 and "이미 등록된 PC" in r.json().get('message', ''):
            logger.info("이미 등록된 PC입니다. Heartbeat를 시작합니다.")
            return True
        else:
            logger.error(f"등록 실패: {r.status_code} - {r.text}")
            return False
    except Exception as e:
        logger.error(f"등록 중 오류 발생: {e}")
        return False


def send_heartbeat():
    """서버에 동적 정보를 Heartbeat로 전송"""
    dynamic_info = collect_dynamic_info()
    if not dynamic_info:
        logger.warning("동적 정보 수집 실패, Heartbeat를 보낼 수 없습니다.")
        return

    data = {
        "machine_id": MACHINE_ID,
        "system_info": dynamic_info
    }

    try:
        r = requests.post(f"{SERVER_URL}api/client/heartbeat", json=data, timeout=5)
        if r.status_code == 200:
            logger.info("Heartbeat: OK")
        elif r.status_code == 404:
            logger.warning("Heartbeat 실패: 서버에 등록되지 않은 PC입니다. 재등록을 시도합니다.")
            register_client()  # 재등록 시도
        else:
            logger.error(f"Heartbeat 실패: {r.status_code}")
    except Exception as e:
        logger.error(f"Heartbeat 오류: {e}")


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
        logger.warning(
            f"전원 관리 명령이지만 부팅 후 {int(elapsed)}초 경과 (유예 시간: {POWER_COMMAND_GRACE_PERIOD}초). 안전을 위해 건너뜁니다.")
        return True

    return False


def poll_command(stop_event: threading.Event):
    """Long-polling으로 명령 대기"""
    while not stop_event.is_set():
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

                    logger.info(f"명령 수신: {cmd_type} | 파라미터: {cmd_params}")

                    # 전원 관리 명령이면서 유예 시간 내라면 건너뛰기
                    if should_skip_command(cmd_type, cmd_params):
                        result = (
                            f"⏭️ 명령 건너뜀: 부팅 후 {POWER_COMMAND_GRACE_PERIOD}초 이내의 전원 관리 명령은 안전을 위해 실행하지 않습니다.")
                        logger.info(result)
                        send_command_result(cmd_id, 'skipped', result)
                        continue

                    # 전원 관리 명령이면 추가 경고 출력
                    if is_power_command(cmd_type, cmd_params):
                        elapsed = (datetime.now() - BOOT_TIME).total_seconds()
                        logger.warning(f"전원 관리 명령 실행 (부팅 후 {int(elapsed)}초 경과)")

                    # 명령 실행
                    result = CommandExecutor.execute_command(cmd_type, cmd_params)
                    logger.info(f"명령 결과: {result}")

                    # 결과를 서버로 보고
                    send_command_result(cmd_id, 'completed', result)

        except requests.exceptions.Timeout:
            # 타임아웃은 정상 동작. 루프 재시도
            continue
        except Exception as e:
            logger.error(f"명령 조회 오류: {e}")
            # 에러 시 짧게 대기하며 종료 이벤트 체크
            if stop_event.wait(5):
                break


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
            logger.info(f"명령 결과 전송 완료: CMD#{command_id}")
        else:
            logger.error(f"명령 결과 전송 실패: {r.status_code}")
    except Exception as e:
        logger.error(f"명령 결과 전송 오류: {e}")


def heartbeat_thread(stop_event: threading.Event):
    """10분 주기로 Heartbeat 전송"""
    while not stop_event.is_set():
        send_heartbeat()
        # 대기 도중 종료 이벤트 감지
        if stop_event.wait(600):
            break


def run_client(stop_event: threading.Event | None = None):
    """클라이언트 본 동작. 서비스/콘솔 공통 진입점"""
    setup_logging()
    logger.info("WCMS 클라이언트 시작...")
    logger.info(f"Machine ID: {MACHINE_ID}")
    logger.info(f"부팅 시간: {BOOT_TIME.strftime('%Y-%m-%d %H:%M:%S')}")

    ev = stop_event or STOP_EVENT

    # 시작 시 먼저 등록 시도
    if not register_client():
        logger.warning("초기 등록 실패. 1분 후 재시도합니다.")
        if ev.wait(60):
            return
        if not register_client():
            logger.error("재등록 실패. 프로그램을 종료합니다.")
            return

    # Heartbeat를 백그라운드 스레드에서 실행
    hb_thread = threading.Thread(target=heartbeat_thread, args=(ev,), daemon=True)
    hb_thread.start()

    # 메인 스레드에서 명령 long-polling
    logger.info("명령 대기 중...")
    try:
        poll_command(ev)
    finally:
        # 종료 시 정리
        ev.set()
        hb_thread.join(timeout=5)
        logger.info("WCMS 클라이언트 종료")


if __name__ == "__main__":
    run_client()
