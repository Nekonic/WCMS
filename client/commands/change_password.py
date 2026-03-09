import subprocess
from typing import Any


def execute(data: dict[str, Any]) -> str:
    username = data.get('username', '')
    new_password = data.get('new_password', '')
    if not username or not new_password:
        return "오류: username, new_password가 필요합니다."
    result = subprocess.run(['net', 'user', username, new_password], capture_output=True, text=True)
    if result.returncode == 0:
        return f"비밀번호 변경됨: {username}"
    return f"비밀번호 변경 실패: {result.stderr}"