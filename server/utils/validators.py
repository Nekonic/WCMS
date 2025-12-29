"""
검증 유틸리티 함수
"""
from typing import Any, Optional
import re


def validate_not_null(value: Any, default: Any) -> Any:
    """
    NOT NULL 필드 기본값 보정

    Args:
        value: 검증할 값
        default: 기본값

    Returns:
        검증된 값 또는 기본값
    """
    try:
        if isinstance(default, int):
            return int(value) if value is not None else default
        elif isinstance(default, float):
            return float(value) if value is not None else default
        return value if value else default
    except (ValueError, TypeError):
        return default


def validate_machine_id(machine_id: Optional[str]) -> bool:
    """
    Machine ID 유효성 검증

    MAC 주소 기반 12자리 16진수 문자열

    Args:
        machine_id: 검증할 Machine ID

    Returns:
        유효 여부
    """
    if not machine_id:
        return False
    # 12자리 16진수 (MAC 주소에서 : 또는 - 제거)
    return bool(re.match(r'^[0-9A-Fa-f]{12}$', machine_id))


def validate_ip_address(ip: Optional[str]) -> bool:
    """
    IP 주소 유효성 검증 (IPv4)

    Args:
        ip: 검증할 IP 주소

    Returns:
        유효 여부
    """
    if not ip:
        return False
    pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if not re.match(pattern, ip):
        return False
    # 각 옥텟이 0-255 범위인지 확인
    return all(0 <= int(octet) <= 255 for octet in ip.split('.'))


def validate_mac_address(mac: Optional[str]) -> bool:
    """
    MAC 주소 유효성 검증

    Args:
        mac: 검증할 MAC 주소

    Returns:
        유효 여부
    """
    if not mac:
        return False
    # XX:XX:XX:XX:XX:XX 또는 XX-XX-XX-XX-XX-XX 형식
    pattern = r'^([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$'
    return bool(re.match(pattern, mac))


def sanitize_hostname(hostname: Optional[str]) -> str:
    """
    호스트명 정제 (안전한 문자만 허용)

    Args:
        hostname: 정제할 호스트명

    Returns:
        정제된 호스트명
    """
    if not hostname:
        return 'Unknown-PC'
    # 알파벳, 숫자, 하이픈, 언더스코어만 허용
    sanitized = re.sub(r'[^a-zA-Z0-9\-_]', '', hostname)
    return sanitized[:64] if sanitized else 'Unknown-PC'  # 최대 64자


def validate_room_name(room: Optional[str]) -> bool:
    """
    실습실 이름 유효성 검증

    Args:
        room: 검증할 실습실 이름

    Returns:
        유효 여부
    """
    if not room:
        return False
    # 한글, 영문, 숫자 허용 (최대 50자)
    return len(room) <= 50 and bool(re.match(r'^[\w가-힣\s]+$', room))


def validate_command_type(cmd_type: Optional[str]) -> bool:
    """
    명령 타입 유효성 검증

    Args:
        cmd_type: 검증할 명령 타입

    Returns:
        유효 여부
    """
    valid_types = {
        'shutdown',
        'reboot',
        'execute',
        'install',
        'download',
        'create_user',
        'delete_user',
        'change_password',
        'logoff',
    }
    return cmd_type in valid_types


def sanitize_command_output(output: str, max_length: int = 5000) -> str:
    """
    명령 실행 결과 정제 (너무 긴 출력 자르기)

    Args:
        output: 명령 출력
        max_length: 최대 길이

    Returns:
        정제된 출력
    """
    if not output:
        return ''
    if len(output) <= max_length:
        return output
    return output[:max_length] + f'\n\n... (출력이 너무 김, {len(output) - max_length}자 생략)'

