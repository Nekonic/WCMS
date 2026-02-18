"""
Client Auto-Updater Module
Handles downloading the new version and replacing the running executable.
"""
import os
import sys
import subprocess
import logging
import tempfile
import time
import requests
from typing import Optional

logger = logging.getLogger('wcms')

def download_file(url: str, dest_path: str) -> bool:
    """Download a file from a URL to a destination path."""
    try:
        logger.info(f"Downloading update from {url}...")
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()
        
        with open(dest_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        logger.info(f"Download complete: {dest_path}")
        return True
    except Exception as e:
        logger.error(f"Download failed: {e}")
        return False

def create_update_script(new_exe_path: str, target_exe_path: str, service_name: str = "WCMS-Client") -> str:
    """
    Create a batch script to stop the service, replace the executable, and restart the service.
    Returns the path to the created script.
    """
    script_content = f"""@echo off
echo Waiting for service to stop...
timeout /t 5 /nobreak >nul

echo Stopping service {service_name}...
net stop {service_name}

echo Waiting for process to release lock...
timeout /t 3 /nobreak >nul

echo Replacing executable...
copy /Y "{new_exe_path}" "{target_exe_path}"
if %errorlevel% neq 0 (
    echo Failed to copy file. Retrying in 5 seconds...
    timeout /t 5 /nobreak >nul
    copy /Y "{new_exe_path}" "{target_exe_path}"
)

echo Starting service {service_name}...
net start {service_name}

echo Cleaning up...
del "{new_exe_path}"
del "%~f0"
"""
    
    fd, script_path = tempfile.mkstemp(suffix=".cmd", prefix="wcms_update_", text=True)
    os.close(fd)
    
    with open(script_path, 'w') as f:
        f.write(script_content)
        
    return script_path

def perform_update(download_url: str, version: str):
    """
    Orchestrate the update process.
    """
    logger.info(f"Starting update process to version {version}...")
    
    # 1. Determine paths
    current_exe = sys.executable
    # If running as script (python.exe), we might not want to update python.exe
    # This updater assumes we are running as a frozen executable (PyInstaller)
    if not getattr(sys, 'frozen', False):
        logger.warning("Not running as frozen executable. Skipping self-update.")
        return

    temp_dir = tempfile.gettempdir()
    new_exe_path = os.path.join(temp_dir, f"WCMS-Client-{version}.exe")
    
    # 2. Download new version
    if not download_file(download_url, new_exe_path):
        logger.error("Aborting update due to download failure.")
        return

    # 3. Create update script
    try:
        script_path = create_update_script(new_exe_path, current_exe)
        logger.info(f"Update script created at {script_path}")
    except Exception as e:
        logger.error(f"Failed to create update script: {e}")
        return

    # 4. Execute script and exit
    logger.info("Executing update script and exiting...")
    try:
        # Run detached
        subprocess.Popen(
            [script_path],
            shell=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )
        sys.exit(0)
    except Exception as e:
        logger.error(f"Failed to launch update script: {e}")
