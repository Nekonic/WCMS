import threading
import psutil
import requests
import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Optional

from config import (
    SERVER_URL, MACHINE_ID, REGISTRATION_PIN, HEARTBEAT_INTERVAL, COMMAND_POLL_INTERVAL,
    LOG_DIR, LOG_FILE, LOG_LEVEL, LOG_MAX_BYTES, LOG_BACKUP_COUNT,
    REQUEST_TIMEOUT, SHUTDOWN_TIMEOUT, __version__, POWER_COMMAND_GRACE_PERIOD, validate_config
)
from collector import collect_static_info, collect_dynamic_info
from executor import CommandExecutor
from utils import safe_request, retry_on_network_error
from updater import perform_update

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
                download_url = data.get('download_url')
                if download_url:
                    logger.info(f"업데이트 시작: {download_url}")
                    perform_update(download_url, latest_version)
                else:
                    logger.info("다운로드 URL이 없어 업데이트를 건너뜁니다.")
            else:
                logger.info(f"최신 버전 사용 중: {__version__}")
    except Exception as e:
        logger.debug(f"버전 체크 실패 (무시): {e}")


@retry_on_network_error(max_retries=3, delay=5)
def register_client():
    """서버에 클라이언트 정보를 등록 (v0.8.0 - PIN 인증)"""
    # 등록 플래그 파일 확인 추가
    registered_flag = os.path.join(os.path.dirname(LOG_DIR), 'registered.flag')
    if os.path.exists(registered_flag):
        logger.info("이미 등록된 PC입니다 (registered.flag 존재)")
        return True

    static_info = collect_static_info()
    if not static_info:
        logger.warning("정적 정보 수집 실패, 등록할 수 없습니다.")
        return False

    # 동적 정보도 함께 수집 (첫 등록 시 디스크/프로세스 정보 즉시 표시)
    dynamic_info = collect_dynamic_info()
    if not dynamic_info:
        logger.warning("동적 정보 수집 실패, 기본값으로 진행합니다.")
        dynamic_info = {}

    # PIN 체크 (v0.8.0)
    if not REGISTRATION_PIN:
        logger.error("등록 PIN이 설정되지 않았습니다. config.json에 REGISTRATION_PIN을 추가하세요.")
        return False

    reg_data = {
        "machine_id": MACHINE_ID,
        "pin": REGISTRATION_PIN,  # v0.8.0: PIN 추가
        **static_info,
        "system_info": dynamic_info  # 동적 정보 포함 (디스크/프로세스)
    }

    try:
        logger.info("서버에 클라이언트 등록 시도...")
        r = safe_request(f"{SERVER_URL}api/client/register", method='POST', json=reg_data, timeout=REQUEST_TIMEOUT)
        if r and r.status_code == 200:
            result = r.json()
            logger.info(f"등록 성공: {result.get('message')}")
            try:
                with open(registered_flag, 'w') as f:
                    f.write(f"Registered at {datetime.now().isoformat()}\n")
            except:
                pass
            return True
        elif r and r.status_code == 403:
            # PIN 검증 실패
            error_msg = r.json().get('message', 'PIN 검증 실패')
            logger.error(f"등록 실패 (PIN 오류): {error_msg}")
            logger.error("올바른 PIN을 config.json에 설정하세요.")
            return False
        elif r and r.status_code == 400:
            error_msg = r.json().get('message', '잘못된 요청')
            logger.error(f"등록 실패: {error_msg}")
            return False
        elif r and r.status_code == 500:
            msg = r.json().get('message', '')
            if "이미 등록된 PC" in msg:
                logger.info("이미 등록된 PC입니다. Heartbeat를 시작합니다.")
                try:
                    with open(registered_flag, 'w') as f:
                        f.write(f"Registered at {datetime.now().isoformat()}\n")
                except:
                    pass
                return True
            else:
                logger.error(f"등록 실패: {r.status_code} - {r.text}")
                return False
        else:
            logger.error(f"등록 실패: {r.status_code if r else 'No response'}")
            return False
    except Exception as e:
        logger.error(f"등록 중 오류 발생: {e}")
        raise  # retry decorator에서 재시도
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
            # 등록 플래그 삭제하여 재등록 유도
            registered_flag = os.path.join(os.path.dirname(LOG_DIR), 'registered.flag')
            if os.path.exists(registered_flag):
                try:
                    os.remove(registered_flag)
                except:
                    pass
            register_client()
            return False
        else:
            logger.error(f"Heartbeat 실패: {r.status_code if r else 'No response'}")
            return False
    except Exception as e:
        logger.error(f"Heartbeat 오류: {e}")
        raise


def send_shutdown_signal():
    """윈도우 종료 시 서버에 오프라인 신호 전송 (단발성)"""
    data = {"machine_id": MACHINE_ID}
    try:
        logger.info("서버에 종료 신호 전송 시도...")
        # 재시도 없이 짧은 타임아웃으로 전송
        r = requests.post(
            f"{SERVER_URL}api/client/shutdown",
            json=data,
            timeout=SHUTDOWN_TIMEOUT
        )
        if r.status_code == 200:
            logger.info("종료 신호 전송 성공")
        else:
            logger.warning(f"종료 신호 전송 실패: {r.status_code}")
    except Exception as e:
        logger.error(f"종료 신호 전송 오류: {e}")


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


def execute_command_async(cmd_id: int, cmd_type: str, cmd_data: dict):
    """명령을 비동기(별도 스레드)로 실행"""
    def _run():
        try:
            # 전원 관리 명령이면서 유예 시간 내라면 건너뛰기
            if should_skip_command(cmd_type, cmd_data):
                result = f"명령 건너뜀: 부팅 후 {POWER_COMMAND_GRACE_PERIOD}초 이내의 전원 관리 명령"
                logger.info(result)
                send_command_result(cmd_id, 'skipped', result)
                return

            # 전원 관리 명령이면 추가 경고 출력
            if is_power_command(cmd_type, cmd_data):
                elapsed = (datetime.now() - BOOT_TIME).total_seconds()
                logger.warning(f"전원 관리 명령 실행 (부팅 후 {int(elapsed)}초 경과)")

            # 명령 실행
            result = CommandExecutor.execute_command(cmd_type, cmd_data)
            logger.info(f"명령 결과: {result}")

            # 결과를 서버로 보고
            send_command_result(cmd_id, 'completed', result)
        except Exception as e:
            logger.error(f"명령 실행 중 오류 발생: {e}")
            send_command_result(cmd_id, 'error', str(e))

    # 데몬 스레드로 실행하여 메인 프로세스 종료 시 함께 종료되도록 함
    # (단, 중요한 작업은 데몬이 아니어야 할 수도 있으나, 여기서는 빠른 응답성을 위해 데몬 사용)
    t = threading.Thread(target=_run, daemon=True)
    t.start()


def poll_command(stop_event: threading.Event):
    """명령 폴링 + 경량 하트비트 통합 (v0.8.0 네트워크 최적화)

    - POST 방식으로 명령 조회
    - 경량 하트비트 (CPU, RAM, IP) 함께 전송
    - 2초마다 폴링 (즉시 응답)
    """
    import socket

    def get_ip_address():
        """현재 IP 주소 조회"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "Unknown"

    logger.info("명령 폴링 시작 (경량 하트비트 통합)")

    while not stop_event.is_set():
        try:
            # 경량 하트비트 데이터 수집
            cpu_usage = psutil.cpu_percent(interval=0.1)
            ram_usage = psutil.virtual_memory().percent
            ip_address = get_ip_address()

            # POST 방식으로 명령 조회 + 경량 하트비트 전송
            r = safe_request(
                f"{SERVER_URL}api/client/commands",  # 변경: command → commands
                method='POST',
                json={
                    "machine_id": MACHINE_ID,
                    "heartbeat": {
                        "cpu_usage": cpu_usage,
                        "ram_usage_percent": ram_usage,
                        "ip_address": ip_address
                    }
                },
                timeout=REQUEST_TIMEOUT,
                max_retries=2
            )

            if r and r.status_code == 200:
                data = r.json()

                # 새 API 응답 형식 체크
                if data.get('status') != 'success':
                    logger.error(f"API 오류: {data.get('error', {}).get('message', 'Unknown error')}")
                    if stop_event.wait(5):
                        break
                    continue

                response_data = data.get('data', {})

                # IP 변경 감지
                if response_data.get('ip_changed'):
                    logger.info(f"IP 주소 변경됨: {ip_address}")

                # 명령 처리 (v0.8.0: 새 API 형식)
                if response_data.get('has_command'):
                    cmd = response_data.get('command', {})
                    cmd_id = cmd.get('id')
                    cmd_type = cmd.get('type')
                    cmd_data = cmd.get('parameters', {})

                    logger.info(f"명령 수신: {cmd_type} | ID: {cmd_id}")

                    # 비동기 실행 (스레드 분리)
                    execute_command_async(cmd_id, cmd_type, cmd_data)
                else:
                    logger.debug(f"명령 없음 (경량 하트비트 전송됨)")
            else:
                logger.debug(f"명령 조회 오류: {r.status_code if r else 'No response'}")

        except Exception as e:
            logger.error(f"명령 조회 오류: {e}")
            if stop_event.wait(5):
                break

        # 2초 대기 (폴링 주기)
        if stop_event.wait(COMMAND_POLL_INTERVAL):
            break


def send_command_result(command_id: int, status: str, result: str):
    """명령 실행 결과를 서버로 보고 (v0.8.0 - 새 API)"""
    try:
        # 상태 매핑: completed/skipped → success, error → error
        api_status = 'success' if status in ['completed', 'skipped'] else 'error'

        data = {
            "status": api_status,
            "output": result,
            "error_message": result if status == 'error' else None
        }

        # 새 API: RESTful 경로 사용
        r = safe_request(
            f"{SERVER_URL}api/client/commands/{command_id}/result",
            method='POST',
            json=data,
            timeout=REQUEST_TIMEOUT,
            max_retries=2
        )

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
