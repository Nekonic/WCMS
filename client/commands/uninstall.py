import os
import subprocess
from typing import Any
from .install import _ensure_chocolatey


def execute(data: dict[str, Any]) -> str:
    app_id = data.get('package_name', '') or data.get('app_id', '')
    if not app_id:
        return "오류: 패키지 이름이 필요합니다."
    if not _ensure_chocolatey():
        return "오류: Chocolatey를 설치할 수 없습니다."
    choco_path = r"C:\ProgramData\chocolatey\bin\choco.exe"
    choco_exe = choco_path if os.path.exists(choco_path) else 'choco'
    result = subprocess.run(
        [choco_exe, 'uninstall', app_id, '-y', '--remove-dependencies'],
        capture_output=True, text=True, timeout=600,
    )
    if result.returncode == 0:
        return f"삭제 완료: {app_id}"
    error_msg = result.stderr.strip() or result.stdout.strip()
    return f"삭제 실패: {app_id}\n{error_msg}"