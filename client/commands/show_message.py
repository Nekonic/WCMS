import os
import subprocess
from typing import Any


def execute(data: dict[str, Any]) -> str:
    message = data.get('message', '')
    if not message:
        return "오류: 메시지가 없습니다."
    system_root = os.environ.get('SystemRoot', r'C:\Windows')
    msg_exe = os.path.join(system_root, 'System32', 'msg.exe')
    if not os.path.exists(msg_exe):
        # 32비트 프로세스(WOW64)에서 64비트 System32 접근용 alias
        msg_exe = os.path.join(system_root, 'Sysnative', 'msg.exe')
    if not os.path.exists(msg_exe):
        return "메시지 표시 실패: msg.exe를 찾을 수 없습니다 (Windows Home 미지원)"
    result = subprocess.run([msg_exe, '*', message], capture_output=True, text=True, timeout=5)
    if result.returncode == 0:
        return f"메시지 표시됨: {message}"
    return f"메시지 표시 실패: {result.stderr}"