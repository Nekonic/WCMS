import subprocess
from typing import Any


def execute(data: dict[str, Any]) -> str:
    delay = max(0, data.get('delay', 0))
    message = data.get('message', '')
    cmd = ['shutdown', '/r', '/t', str(delay)]
    if message:
        cmd += ['/c', message]
    subprocess.run(cmd)
    return f"재시작 명령 실행됨 (지연: {delay}초)"