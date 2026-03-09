import subprocess
from typing import Any


def execute(data: dict[str, Any]) -> str:
    command = data.get('command', '')
    if not command:
        return "오류: 실행할 명령어가 없습니다."
    result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
    return result.stdout or result.stderr or "실행 완료"