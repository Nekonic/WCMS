import threading
import json
import psutil
import requests
import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Optional

from config import (
    SERVER_URL, MACHINE_ID, HEARTBEAT_INTERVAL, COMMAND_POLL_INTERVAL,
    LOG_DIR, LOG_FILE, LOG_LEVEL, LOG_MAX_BYTES, LOG_BACKUP_COUNT,
    REQUEST_TIMEOUT, __version__, POWER_COMMAND_GRACE_PERIOD, validate_config
)
from collector import collect_static_info, collect_dynamic_info
from executor import CommandExecutor
from utils import safe_request, retry_on_network_error

# 부팅 시간 기록 (전원 관리 명령 유예 시간 계산용)
BOOT_TIME = datetime.now()

# 서비스/콘솔 공통 종료 제어 이벤트
STOP_EVENT = threading.Event()

logger = logging.getLogger('wcms')


def setup_logging():
    global logger
    if logger.handlers:
        return logger
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
        handler = RotatingFileHandler(LOG_FILE, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT, encoding='utf-8')
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    except Exception as e:
        logger.setLevel(logging.INFO)
        sh = logging.StreamHandler()
        sh.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s'))
        logger.addHandler(sh)
        logger.error(f"로그 파일 초기화 실패: {e}")
    return logger


def check_for_updates():
    """서버에서 최신 버전 확인"""
    try:
        response = safe_request(f"{SERVER_URL}api/client/version", timeout=REQUEST_TIMEOUT, max_retries=2)
        if response and response.status_code == 200:
            data = response.json()
            latest_version = data.get('version', '1.0.0')

            if latest_version != __version__:
                logger.warning(f"새 버전이 있습니다! 현재: {__version__}, 최신: {latest_version}")
                logger.info(f"다운로드: {data.get('download_url', 'GitHub Release 확인')}")
                if data.get('changelog'):
                    logger.info(f"변경사항: {data.get('changelog')}")
            else:
                logger.info(f"최신 버전 사용 중: {__version__}")
    except Exception as e:
        logger.debug(f"버전 체크 실패 (무시): {e}")


@retry_on_network_error(max_retries=3, delay=5)
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
        r = safe_request(f"{SERVER_URL}api/client/register", method='POST', json=reg_data, timeout=REQUEST_TIMEOUT)
        if r and r.status_code == 200:
            result = r.json()
            logger.info(f"등록 성공: {result.get('message')}")
            return True
        elif r and r.status_code == 500:
            msg = r.json().get('message', '')
            if "이미 등록된 PC" in msg:
                logger.info("이미 등록된 PC입니다. Heartbeat를 시작합니다.")
                return True
            else:
                logger.error(f"등록 실패: {r.status_code} - {r.text}")
                return False
        else:
            logger.error(f"등록 실패: {r.status_code if r else 'No response'}")
            return False
    except Exception as e:
        logger.error(f"등록 중 오류 발생: {e}")
@retry_on_network_error(max_retries=3, delay=5)
def send_heartbeat():
    """서버에 동적 정보를 Heartbeat로 전송"""
    dynamic_info = collect_dynamic_info()
    if not dynamic_info:
        logger.warning("동적 정보 수집 실패, Heartbeat를 보낼 수 없습니다.")
        return False

    data = {
        "machine_id": MACHINE_ID,
        "system_info": dynamic_info
    }

    try:
        r = safe_request(f"{SERVER_URL}api/client/heartbeat", method='POST', json=data, timeout=REQUEST_TIMEOUT)
        if r and r.status_code == 200:
            logger.debug("Heartbeat: OK")
            return True
        elif r and r.status_code == 404:
            logger.warning("Heartbeat 실패: 서버에 등록되지 않은 PC입니다. 재등록을 시도합니다.")
            register_client()
            return False
        else:
            logger.error(f"Heartbeat 실패: {r.status_code if r else 'No response'}")
            return False
    except Exception as e:
        logger.error(f"Heartbeat 오류: {e}")
        raise


def is_power_command(cmd_type: str, cmd_params: dict) -> bool:
    """전원 관리 명령인지 확인"""
    if cmd_type in ['shutdown', 'reboot']:
        return True
    if cmd_type == 'execute' and cmd_params.get('command'):
        cmd = cmd_params['command'].lower()
        if any(x in cmd for x in ['shutdown', 'restart', 'logoff']):
            return True
    return False


def should_skip_command(cmd_type: str, cmd_params: dict) -> bool:
    """명령을 건너뛰어야 하는지 확인"""
    if not is_power_command(cmd_type, cmd_params):
        return False

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
            r = safe_request(
                f"{SERVER_URL}api/client/command",
                method='GET',
                params={"machine_id": MACHINE_ID},
                timeout=COMMAND_POLL_INTERVAL + 10,
                max_retries=2
            )
            if r and r.status_code == 200:
                commands = r.json().get('commands', [])

                for cmd in commands:
                    cmd_id = cmd.get('id')
                    cmd_type = cmd.get('type')
                    cmd_data = cmd.get('data', {})

                    logger.info(f"명령 수신: {cmd_type} | ID: {cmd_id}")

                    # 전원 관리 명령이면서 유예 시간 내라면 건너뛰기
                    if should_skip_command(cmd_type, cmd_data):
                        result = f"명령 건너뜀: 부팅 후 {POWER_COMMAND_GRACE_PERIOD}초 이내의 전원 관리 명령"
                        logger.info(result)
                        send_command_result(cmd_id, 'skipped', result)
                        continue

                    # 전원 관리 명령이면 추가 경고 출력
                    if is_power_command(cmd_type, cmd_data):
                        elapsed = (datetime.now() - BOOT_TIME).total_seconds()
                        logger.warning(f"전원 관리 명령 실행 (부팅 후 {int(elapsed)}초 경과)")

                    # 명령 실행
                    result = CommandExecutor.execute_command(cmd_type, cmd_data)
                    logger.info(f"명령 결과: {result}")

                    # 결과를 서버로 보고
                    send_command_result(cmd_id, 'completed', result)
            else:
                logger.debug(f"명령 없음 또는 오류: {r.status_code if r else 'No response'}")

        except Exception as e:
            logger.error(f"명령 조회 오류: {e}")
            if stop_event.wait(5):
                break


def send_command_result(command_id: int, status: str, result: str):
    """명령 실행 결과를 서버로 보고"""
    try:
        data = {
            "command_id": command_id,
            "status": status,
            "result": result
        }
        r = safe_request(f"{SERVER_URL}api/client/command/result", method='POST', json=data, timeout=REQUEST_TIMEOUT, max_retries=2)
        if r and r.status_code == 200:
            logger.debug(f"명령 결과 전송 완료: CMD#{command_id}")
        else:
            logger.error(f"명령 결과 전송 실패: {r.status_code if r else 'No response'}")
    except Exception as e:
        logger.error(f"명령 결과 전송 오류: {e}")


def heartbeat_thread(stop_event: threading.Event):
    """주기적 Heartbeat 전송"""
    while not stop_event.is_set():
        send_heartbeat()
        if stop_event.wait(HEARTBEAT_INTERVAL):
            break


def run_client(stop_event: Optional[threading.Event] = None):
    """클라이언트 본 동작. 서비스/콘솔 공통 진입점"""
    setup_logging()

    try:
        validate_config()
    except ValueError as e:
        logger.error(f"설정 오류: {e}")
        return

    logger.info(f"WCMS 클라이언트 v{__version__} 시작...")
    logger.info(f"Machine ID: {MACHINE_ID}")
    logger.info(f"부팅 시간: {BOOT_TIME.strftime('%Y-%m-%d %H:%M:%S')}")

    ev = stop_event or STOP_EVENT

    # 버전 체크
    check_for_updates()

    # 시작 시 먼저 등록 시도
    try:
        if not register_client():
            logger.warning("초기 등록 실패. 1분 후 재시도합니다.")
            if ev.wait(60):
                return
            if not register_client():
                logger.error("재등록 실패. 프로그램을 종료합니다.")
                return
    except Exception as e:
        logger.error(f"등록 실패: {e}")
        return

    # Heartbeat를 백그라운드 스레드에서 실행
    hb_thread = threading.Thread(target=heartbeat_thread, args=(ev,), daemon=True)
    hb_thread.start()

    # 메인 스레드에서 명령 long-polling
    logger.info("명령 대기 중...")
    try:
        poll_command(ev)
    finally:
        ev.set()
        hb_thread.join(timeout=5)
        logger.info("WCMS 클라이언트 종료")


if __name__ == "__main__":
    run_client()
