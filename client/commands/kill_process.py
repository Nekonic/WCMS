import subprocess
from typing import Any


def execute(data: dict[str, Any]) -> str:
    process_name = data.get('process_name', '')
    if not process_name:
        return "프로세스 이름이 지정되지 않음"
    if not process_name.lower().endswith('.exe'):
        process_name += '.exe'
    result = subprocess.run(
        ['taskkill', '/F', '/IM', process_name],
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode == 0:
        return f"프로세스 종료됨: {process_name}"
    if "찾을 수 없습니다" in result.stderr or "not found" in result.stderr.lower():
        return f"프로세스를 찾을 수 없음: {process_name}"
    return f"프로세스 종료 실패: {result.stderr}"