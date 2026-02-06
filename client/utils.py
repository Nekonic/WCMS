"""
클라이언트 유틸리티 함수
네트워크 재시도, 에러 핸들링 등
"""
import time
import logging
from functools import wraps
from typing import Callable, Any, Optional
import requests


logger = logging.getLogger('wcms')


def retry_on_network_error(max_retries: int = 3, delay: int = 5, exponential_backoff: bool = True):
    """
    네트워크 에러 시 재시도 데코레이터

    Args:
        max_retries: 최대 재시도 횟수
        delay: 기본 지연 시간 (초)
        exponential_backoff: 지수 백오프 사용 여부

    Usage:
        @retry_on_network_error(max_retries=3, delay=5)
        def my_network_function():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (
                    ConnectionError,  # 일반 ConnectionError 포함
                    requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout,
                    requests.exceptions.RequestException
                ) as e:
                    last_exception = e

                    if attempt < max_retries - 1:
                        # 지수 백오프: delay * 2^attempt
                        wait_time = delay * (2 ** attempt) if exponential_backoff else delay
                        logger.warning(
                            f"{func.__name__} 실패 (시도 {attempt + 1}/{max_retries}): {e}. "
                            f"{wait_time}초 후 재시도..."
                        )
                        time.sleep(wait_time)
                    else:
                        logger.error(
                            f"{func.__name__} 최종 실패 ({max_retries}회 시도): {e}"
                        )

            # 모든 재시도 실패 시 마지막 예외 발생
            raise last_exception

        return wrapper
    return decorator


def safe_request(
    url: str,
    method: str = 'GET',
    timeout: int = 30,
    max_retries: int = 3,
    **kwargs
) -> Optional[requests.Response]:
    """
    안전한 HTTP 요청 (자동 재시도 포함)

    Args:
        url: 요청 URL
        method: HTTP 메소드 (GET, POST, PUT, DELETE)
        timeout: 타임아웃 (초)
        max_retries: 최대 재시도 횟수
        **kwargs: requests 함수에 전달할 추가 인자

    Returns:
        Response 객체 또는 None (실패 시)
    """
    @retry_on_network_error(max_retries=max_retries)
    def _request():
        method_func = getattr(requests, method.lower())
        response = method_func(url, timeout=timeout, **kwargs)
        response.raise_for_status()
        return response

    try:
        return _request()
    except Exception as e:
        logger.error(f"HTTP 요청 실패: {method} {url} - {e}")
        return None


def load_json_file(file_path: str, default: Any = None) -> Any:
    """
    JSON 파일 로드 (안전)

    Args:
        file_path: JSON 파일 경로
        default: 로드 실패 시 반환할 기본값

    Returns:
        로드된 데이터 또는 기본값
    """
    import json
    import os

    if not os.path.exists(file_path):
        logger.warning(f"JSON 파일이 없습니다: {file_path}")
        return default

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"JSON 파일 로드 실패: {file_path} - {e}")
        return default


def save_json_file(file_path: str, data: Any) -> bool:
    """
    JSON 파일 저장 (안전)

    Args:
        file_path: JSON 파일 경로
        data: 저장할 데이터

    Returns:
        성공 여부
    """
    import json
    import os

    try:
        # 디렉토리 생성
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"JSON 파일 저장 실패: {file_path} - {e}")
        return False


def format_bytes(bytes_value: int, precision: int = 2) -> str:
    """
    바이트를 사람이 읽기 쉬운 형식으로 변환

    Args:
        bytes_value: 바이트 값
        precision: 소수점 자리수

    Returns:
        형식화된 문자열 (예: "1.23 GB")
    """
    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    unit_index = 0
    value = float(bytes_value)

    while value >= 1024 and unit_index < len(units) - 1:
        value /= 1024
        unit_index += 1

    return f"{value:.{precision}f} {units[unit_index]}"


def format_uptime(seconds: int) -> str:
    """
    업타임(초)을 사람이 읽기 쉬운 형식으로 변환

    Args:
        seconds: 업타임 (초)

    Returns:
        형식화된 문자열 (예: "2일 3시간 15분")
    """
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)

    parts = []
    if days > 0:
        parts.append(f"{days}일")
    if hours > 0:
        parts.append(f"{hours}시간")
    if minutes > 0 or not parts:  # 최소 분은 표시
        parts.append(f"{minutes}분")

    return " ".join(parts)


def truncate_string(s: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    문자열 자르기

    Args:
        s: 원본 문자열
        max_length: 최대 길이
        suffix: 잘린 경우 끝에 붙일 문자열

    Returns:
        잘린 문자열
    """
    if len(s) <= max_length:
        return s
    return s[:max_length - len(suffix)] + suffix


def is_admin_process() -> bool:
    """
    현재 프로세스가 관리자 권한으로 실행 중인지 확인

    Returns:
        관리자 권한 여부
    """
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def get_process_priority_class(priority: int) -> str:
    """
    psutil 우선순위 값을 Windows 우선순위 클래스로 변환

    Args:
        priority: psutil의 nice() 값

    Returns:
        우선순위 클래스 문자열
    """
    priority_map = {
        32: "IDLE",
        64: "BELOW_NORMAL",
        128: "NORMAL",
        256: "ABOVE_NORMAL",
        16384: "HIGH",
        32768: "REALTIME",
    }
    return priority_map.get(priority, "UNKNOWN")

