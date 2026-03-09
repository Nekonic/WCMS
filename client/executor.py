"""
명령 실행 모듈
서버에서 수신한 명령을 commands/ 패키지로 디스패치합니다.
"""
import logging
from typing import Any

from commands import HANDLERS

logger = logging.getLogger('wcms')


class CommandExecutor:
    """Windows 명령 실행 클래스"""

    @staticmethod
    def execute_command(command_type: str, command_data: dict[str, Any]) -> str:
        handler = HANDLERS.get(command_type)
        if not handler:
            return f"알 수 없는 명령 타입: {command_type}"
        try:
            return handler(command_data)
        except Exception as e:
            logger.error(f"명령 실행 오류 ({command_type}): {e}")
            return f"오류: {str(e)}"