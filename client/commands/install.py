import os
import subprocess
import logging
from typing import Any

logger = logging.getLogger('wcms')


def _ensure_chocolatey() -> bool:
    try:
        result = subprocess.run(['choco', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            return True
    except Exception:
        pass
    logger.info("Chocolatey 미설치 — 설치 시도 중...")
    install_cmd = (
        "Set-ExecutionPolicy Bypass -Scope Process -Force; "
        "[System.Net.ServicePointManager]::SecurityProtocol = "
        "[System.Net.ServicePointManager]::SecurityProtocol -bor 3072; "
        "iex ((New-Object System.Net.WebClient).DownloadString("
        "'https://community.chocolatey.org/install.ps1'))"
    )
    result = subprocess.run(
        f'powershell -NoProfile -InputFormat None -ExecutionPolicy Bypass -Command "{install_cmd}"',
        shell=True, capture_output=True, text=True, timeout=300,
    )
    if result.returncode == 0:
        return True
    logger.error(f"Chocolatey 설치 실패: {result.stderr}")
    return False


def execute(data: dict[str, Any]) -> str:
    app_id = data.get('package_name', '') or data.get('app_id', '')
    if not app_id:
        return "오류: 패키지 이름이 필요합니다."
    if not _ensure_chocolatey():
        return "오류: Chocolatey를 설치할 수 없습니다."
    choco_path = r"C:\ProgramData\chocolatey\bin\choco.exe"
    choco_exe = choco_path if os.path.exists(choco_path) else 'choco'
    result = subprocess.run(
        [choco_exe, 'install', app_id, '-y', '--force'],
        capture_output=True, text=True, timeout=600,
    )
    if result.returncode == 0:
        return f"설치 완료: {app_id}"
    error_msg = result.stderr.strip() or result.stdout.strip()
    return f"설치 실패: {app_id}\n{error_msg}"