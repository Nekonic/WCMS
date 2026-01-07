"""
WCMS 클라이언트 설정 관리
환경변수 기반 설정 중앙화
"""
import os
import psutil


# ==================== 서버 연결 설정 ====================

SERVER_URL = os.getenv('WCMS_SERVER_URL', 'http://aps.or.kr:8057/')

# Machine ID 생성 (MAC 주소 기반)
MACHINE_ID = next(
    (addr.address.replace(':', '').replace('-', '')
     for interface, addrs in psutil.net_if_addrs().items()
     for addr in addrs if addr.family == psutil.AF_LINK),
    "MACHINE-DEFAULT"
)


# ==================== 주기 설정 ====================

# 하트비트 전송 주기 (초)
HEARTBEAT_INTERVAL = int(os.getenv('WCMS_HEARTBEAT_INTERVAL', '300'))  # 5분

# 명령 폴링 주기 (초)
COMMAND_POLL_INTERVAL = int(os.getenv('WCMS_COMMAND_POLL_INTERVAL', '10'))  # 10초

# 전원 명령 유예 시간 (초) - 부팅 직후 전원 명령 방지
POWER_COMMAND_GRACE_PERIOD = int(os.getenv('WCMS_POWER_GRACE_PERIOD', '60'))  # 60초


# ==================== 로깅 설정 ====================

# 로그 디렉토리
LOG_DIR = os.path.join(
    os.environ.get('PROGRAMDATA', os.getcwd()),
    'WCMS',
    'logs'
)

# 로그 파일 경로
LOG_FILE = os.path.join(LOG_DIR, 'client.log')

# 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL = os.getenv('WCMS_LOG_LEVEL', 'INFO')

# 로그 파일 최대 크기 (바이트)
LOG_MAX_BYTES = int(os.getenv('WCMS_LOG_MAX_BYTES', str(10 * 1024 * 1024)))  # 10MB

# 로그 백업 개수
LOG_BACKUP_COUNT = int(os.getenv('WCMS_LOG_BACKUP_COUNT', '5'))


# ==================== 네트워크 설정 ====================

# HTTP 요청 타임아웃 (초)
REQUEST_TIMEOUT = int(os.getenv('WCMS_REQUEST_TIMEOUT', '30'))

# 종료 신호 전송 타임아웃 (초) - 짧게 설정
SHUTDOWN_TIMEOUT = int(os.getenv('WCMS_SHUTDOWN_TIMEOUT', '2'))

# 네트워크 에러 시 재시도 횟수
MAX_RETRIES = int(os.getenv('WCMS_MAX_RETRIES', '3'))

# 재시도 지연 시간 (초)
RETRY_DELAY = int(os.getenv('WCMS_RETRY_DELAY', '5'))

# 지수 백오프 사용 여부
USE_EXPONENTIAL_BACKOFF = os.getenv('WCMS_USE_EXPONENTIAL_BACKOFF', 'true').lower() == 'true'


# ==================== 버전 정보 ====================

# 클라이언트 버전 (GitHub Actions에서 자동 교체)
__version__ = "dev"


# ==================== 시스템 프로세스 필터 ====================

# 시스템 프로세스 JSON 파일 경로
SYSTEM_PROCESSES_FILE = os.path.join(
    os.path.dirname(__file__),
    'data',
    'system_processes.json'
)


# ==================== 설정 검증 ====================

def validate_config():
    """설정 유효성 검증"""
    errors = []

    # 서버 URL 검증
    if not SERVER_URL or not SERVER_URL.startswith('http'):
        errors.append(f"Invalid SERVER_URL: {SERVER_URL}")

    # Machine ID 검증
    if not MACHINE_ID or MACHINE_ID == "MACHINE-DEFAULT":
        errors.append("Machine ID를 생성할 수 없습니다. 네트워크 인터페이스를 확인하세요.")

    # 주기 설정 검증
    if HEARTBEAT_INTERVAL < 10:
        errors.append(f"HEARTBEAT_INTERVAL이 너무 짧습니다: {HEARTBEAT_INTERVAL}초 (최소 10초)")

    if COMMAND_POLL_INTERVAL < 1:
        errors.append(f"COMMAND_POLL_INTERVAL이 너무 짧습니다: {COMMAND_POLL_INTERVAL}초 (최소 1초)")

    if errors:
        raise ValueError(f"설정 검증 실패:\n" + "\n".join(f"  - {e}" for e in errors))


def print_config():
    """현재 설정 출력 (디버깅용)"""
    print("=" * 60)
    print("WCMS 클라이언트 설정")
    print("=" * 60)
    print(f"버전:             {__version__}")
    print(f"서버 URL:         {SERVER_URL}")
    print(f"Machine ID:       {MACHINE_ID}")
    print(f"하트비트 주기:    {HEARTBEAT_INTERVAL}초")
    print(f"명령 폴링 주기:   {COMMAND_POLL_INTERVAL}초")
    print(f"로그 디렉토리:    {LOG_DIR}")
    print(f"로그 레벨:        {LOG_LEVEL}")
    print("=" * 60)


# 모듈 임포트 시 설정 검증 (필요 시)
if __name__ == '__main__':
    validate_config()
    print_config()
