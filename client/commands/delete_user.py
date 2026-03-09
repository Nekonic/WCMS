import subprocess
from typing import Any


def execute(data: dict[str, Any]) -> str:
    username = data.get('username', '')
    if not username:
        return "오류: username이 필요합니다."
    result = subprocess.run(['net', 'user', username, '/delete'], capture_output=True, text=True)
    if result.returncode == 0:
        return f"사용자 계정 삭제됨: {username}"
    return f"사용자 삭제 실패: {result.stderr}"