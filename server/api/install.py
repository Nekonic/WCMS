"""
WCMS 설치 API

클라이언트 자동 설치를 위한 스크립트 제공
실제 EXE는 GitHub Releases에서 다운로드
"""
from flask import Blueprint, Response, current_app, jsonify, request
import logging

logger = logging.getLogger('wcms.install')

install_bp = Blueprint('install', __name__, url_prefix='/install')

# GitHub Repository 정보
GITHUB_REPO = "Nekonic/WCMS"
GITHUB_RELEASES_BASE = f"https://github.com/{GITHUB_REPO}/releases/download"


def get_install_cmd_script(server_url: str) -> str:
    """
    install.cmd 스크립트 생성 (동적)

    Args:
        server_url: 서버 URL (예: http://localhost:5050)

    Returns:
        Windows Batch 스크립트 문자열
    """
    return f'''@echo off
REM WCMS Client Auto-Install Script
REM GitHub: https://github.com/{GITHUB_REPO}

SETLOCAL EnableDelayedExpansion

echo ========================================
echo  WCMS Client Auto-Install
echo ========================================
echo.

REM ====================================
REM 1. Check Administrator Privileges
REM ====================================
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] Administrator privileges required.
    echo Please run Command Prompt as Administrator.
    echo.
    pause
    exit /b 1
)
echo [OK] Administrator privileges verified

REM ====================================
REM 2. Connect to Server and Get Latest Version
REM ====================================
echo [INFO] Checking latest version from server...
SET SERVER_URL={server_url}

REM Parse JSON with PowerShell
for /f "delims=" %%i in ('powershell -Command "try {{ $r = Invoke-RestMethod -Uri '%SERVER_URL%/api/client/version' -TimeoutSec 10; Write-Output $r.version }} catch {{ Write-Output 'ERROR' }}"') do set VERSION=%%i

if "%VERSION%"=="ERROR" (
    echo [ERROR] Cannot connect to server: %SERVER_URL%
    echo Please check if the server is running.
    echo.
    pause
    exit /b 1
)
echo [OK] Latest version: %VERSION%

REM Get download URL
for /f "delims=" %%i in ('powershell -Command "try {{ $r = Invoke-RestMethod -Uri '%SERVER_URL%/api/client/version' -TimeoutSec 10; Write-Output $r.download_url }} catch {{ Write-Output 'ERROR' }}"') do set DOWNLOAD_URL=%%i

if "%DOWNLOAD_URL%"=="ERROR" (
    echo [ERROR] Failed to get download URL.
    pause
    exit /b 1
)

echo [INFO] Download URL: %DOWNLOAD_URL%

REM ====================================
REM 3. Download Client
REM ====================================
echo [INFO] Downloading WCMS Client...
SET TEMP_DIR=%TEMP%\\WCMS-Install
SET EXE_PATH=%TEMP_DIR%\\WCMS-Client.exe

if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"

powershell -Command "Invoke-WebRequest -Uri '%DOWNLOAD_URL%' -OutFile '%EXE_PATH%' -UseBasicParsing"
if %errorLevel% neq 0 (
    echo [ERROR] Download failed
    echo.
    pause
    exit /b 1
)
echo [OK] Download complete

REM ====================================
REM 4. Create Installation Directories
REM ====================================
echo [INFO] Creating installation directories...
SET INSTALL_DIR=C:\\Program Files\\WCMS
SET CONFIG_DIR=C:\\ProgramData\\WCMS

if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
if not exist "%CONFIG_DIR%" mkdir "%CONFIG_DIR%"

REM ====================================
REM 5. Copy Files
REM ====================================
echo [INFO] Copying files...
copy /Y "%EXE_PATH%" "%INSTALL_DIR%\\WCMS-Client.exe" >nul
if %errorLevel% neq 0 (
    echo [ERROR] File copy failed
    echo.
    pause
    exit /b 1
)
echo [OK] File copy complete

REM ====================================
REM 6. Create config.json
REM ====================================
echo [INFO] Creating configuration file...
(
    echo {{
    echo   "SERVER_URL": "%SERVER_URL%",
    echo   "HEARTBEAT_INTERVAL": 300,
    echo   "POLL_TIMEOUT": 10,
    echo   "LOG_LEVEL": "INFO"
    echo }}
) > "%CONFIG_DIR%\\config.json"
echo [OK] Configuration file created

REM ====================================
REM 7. Install Service
REM ====================================
echo [INFO] Installing Windows service...

REM Check and stop existing service
sc query WCMS-Client >nul 2>&1
if %errorLevel% equ 0 (
    echo [INFO] Existing service detected. Stopping and removing...
    net stop WCMS-Client >nul 2>&1
    "%INSTALL_DIR%\\WCMS-Client.exe" remove >nul 2>&1
    timeout /t 2 >nul
)

REM Install new service
"%INSTALL_DIR%\\WCMS-Client.exe" install
if %errorLevel% neq 0 (
    echo [ERROR] Service installation failed
    echo.
    pause
    exit /b 1
)
echo [OK] Service installed

REM ====================================
REM 8. Start Service
REM ====================================
echo [INFO] Starting service...
net start WCMS-Client >nul 2>&1
if %errorLevel% neq 0 (
    echo [WARN] Service start failed
    echo To start manually: net start WCMS-Client
    echo.
) else (
    echo [OK] Service started
)

REM ====================================
REM 9. Verify Installation
REM ====================================
echo.
echo [INFO] Verifying installation...
timeout /t 2 >nul

sc query WCMS-Client | find "RUNNING" >nul
if %errorLevel% equ 0 (
    echo.
    echo ========================================
    echo  WCMS Client Installation Complete!
    echo ========================================
    echo  Version: %VERSION%
    echo  Server: %SERVER_URL%
    echo  Install Path: %INSTALL_DIR%
    echo  Config File: %CONFIG_DIR%\\config.json
    echo  Service Status: Running
    echo ========================================
    echo.
    echo Management Commands:
    echo   Check status: sc query WCMS-Client
    echo   Stop: net stop WCMS-Client
    echo   Start: net start WCMS-Client
    echo   Remove: "%INSTALL_DIR%\\WCMS-Client.exe" remove
    echo ========================================
    echo.
) else (
    echo.
    echo ========================================
    echo  WCMS Client Installation Complete (Warning)
    echo ========================================
    echo  Version: %VERSION%
    echo  Server: %SERVER_URL%
    echo  Install Path: %INSTALL_DIR%
    echo  Service Status: Stopped
    echo ========================================
    echo.
    echo [WARN] Service is not running.
    echo To start manually:
    echo   net start WCMS-Client
    echo.
    echo Check logs: %CONFIG_DIR%\\logs\\
    echo ========================================
    echo.
)

REM ====================================
REM 10. Cleanup
REM ====================================
if exist "%TEMP_DIR%" rmdir /S /Q "%TEMP_DIR%"

ENDLOCAL
exit /b 0
'''


def get_install_ps1_script(server_url: str) -> str:
    """
    install.ps1 스크립트 생성 (동적)

    Args:
        server_url: 서버 URL (예: http://localhost:5050)

    Returns:
        PowerShell 스크립트 문자열
    """
    return f'''# WCMS 클라이언트 자동 설치 스크립트 (PowerShell)
# GitHub: https://github.com/{GITHUB_REPO}

param(
    [string]$ServerUrl = "{server_url}"
)

# 색상 설정
$InfoColor = "Cyan"
$SuccessColor = "Green"
$WarnColor = "Yellow"
$ErrorColor = "Red"

Write-Host ""
Write-Host "========================================" -ForegroundColor $InfoColor
Write-Host " WCMS 클라이언트 자동 설치" -ForegroundColor $InfoColor
Write-Host "========================================" -ForegroundColor $InfoColor
Write-Host ""

# ====================================
# 1. 관리자 권한 확인
# ====================================
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {{
    Write-Host "[ERROR] 관리자 권한이 필요합니다." -ForegroundColor $ErrorColor
    Write-Host "PowerShell을 관리자로 실행하고 다시 시도하세요." -ForegroundColor $ErrorColor
    Write-Host ""
    Read-Host "종료하려면 Enter 키를 누르세요"
    exit 1
}}
Write-Host "[OK] 관리자 권한 확인" -ForegroundColor $SuccessColor

# ====================================
# 2. 서버 연결 및 최신 버전 조회
# ====================================
Write-Host "[INFO] 서버에서 최신 버전 확인 중..." -ForegroundColor $InfoColor

try {{
    $versionInfo = Invoke-RestMethod -Uri "$ServerUrl/api/client/version" -TimeoutSec 10
    $Version = $versionInfo.version
    $DownloadUrl = $versionInfo.download_url
    Write-Host "[OK] 최신 버전: $Version" -ForegroundColor $SuccessColor
    Write-Host "[INFO] 다운로드 URL: $DownloadUrl" -ForegroundColor $InfoColor
}} catch {{
    Write-Host "[ERROR] 서버에 연결할 수 없습니다: $ServerUrl" -ForegroundColor $ErrorColor
    Write-Host "서버가 실행 중인지 확인하세요." -ForegroundColor $ErrorColor
    Write-Host "오류 상세: $_" -ForegroundColor $ErrorColor
    Write-Host ""
    Read-Host "종료하려면 Enter 키를 누르세요"
    exit 1
}}

# ====================================
# 3. 다운로드
# ====================================
$TempDir = "$env:TEMP\\WCMS-Install"
$ExePath = "$TempDir\\WCMS-Client.exe"

Write-Host "[INFO] WCMS 클라이언트 다운로드 중..." -ForegroundColor $InfoColor

if (-not (Test-Path $TempDir)) {{
    New-Item -ItemType Directory -Path $TempDir -Force | Out-Null
}}

try {{
    Invoke-WebRequest -Uri $DownloadUrl -OutFile $ExePath -UseBasicParsing
    Write-Host "[OK] 다운로드 완료" -ForegroundColor $SuccessColor
}} catch {{
    Write-Host "[ERROR] 다운로드 실패" -ForegroundColor $ErrorColor
    Write-Host "오류 상세: $_" -ForegroundColor $ErrorColor
    Write-Host ""
    Read-Host "종료하려면 Enter 키를 누르세요"
    exit 1
}}

# ====================================
# 4. 설치 디렉토리 생성
# ====================================
$InstallDir = "C:\\Program Files\\WCMS"
$ConfigDir = "C:\\ProgramData\\WCMS"

Write-Host "[INFO] 설치 디렉토리 생성 중..." -ForegroundColor $InfoColor
New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
New-Item -ItemType Directory -Path $ConfigDir -Force | Out-Null

# ====================================
# 5. 파일 복사
# ====================================
Write-Host "[INFO] 파일 복사 중..." -ForegroundColor $InfoColor
try {{
    Copy-Item -Path $ExePath -Destination "$InstallDir\\WCMS-Client.exe" -Force
    Write-Host "[OK] 파일 복사 완료" -ForegroundColor $SuccessColor
}} catch {{
    Write-Host "[ERROR] 파일 복사 실패" -ForegroundColor $ErrorColor
    Write-Host "오류 상세: $_" -ForegroundColor $ErrorColor
    Write-Host ""
    Read-Host "종료하려면 Enter 키를 누르세요"
    exit 1
}}

# ====================================
# 6. config.json 생성
# ====================================
Write-Host "[INFO] 설정 파일 생성 중..." -ForegroundColor $InfoColor

$Config = @{{
    SERVER_URL = $ServerUrl
    HEARTBEAT_INTERVAL = 300
    POLL_TIMEOUT = 10
    LOG_LEVEL = "INFO"
}} | ConvertTo-Json -Depth 10

try {{
    Set-Content -Path "$ConfigDir\\config.json" -Value $Config -Encoding UTF8
    Write-Host "[OK] 설정 파일 생성 완료" -ForegroundColor $SuccessColor
}} catch {{
    Write-Host "[ERROR] 설정 파일 생성 실패" -ForegroundColor $ErrorColor
    Write-Host "오류 상세: $_" -ForegroundColor $ErrorColor
    Write-Host ""
    Read-Host "종료하려면 Enter 키를 누르세요"
    exit 1
}}

# ====================================
# 7. 서비스 설치
# ====================================
Write-Host "[INFO] Windows 서비스 설치 중..." -ForegroundColor $InfoColor

# 기존 서비스 확인 및 중지
$existingService = Get-Service -Name "WCMS-Client" -ErrorAction SilentlyContinue
if ($existingService) {{
    Write-Host "[INFO] 기존 서비스 감지. 중지 및 제거 중..." -ForegroundColor $InfoColor
    
    if ($existingService.Status -eq "Running") {{
        Stop-Service -Name "WCMS-Client" -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    }}
    
    & "$InstallDir\\WCMS-Client.exe" remove | Out-Null
    Start-Sleep -Seconds 2
}}

# 새 서비스 설치
try {{
    $installOutput = & "$InstallDir\\WCMS-Client.exe" install 2>&1
    if ($LASTEXITCODE -ne 0) {{
        throw "서비스 설치 실패: $installOutput"
    }}
    Write-Host "[OK] 서비스 설치 완료" -ForegroundColor $SuccessColor
}} catch {{
    Write-Host "[ERROR] 서비스 설치 실패" -ForegroundColor $ErrorColor
    Write-Host "오류 상세: $_" -ForegroundColor $ErrorColor
    Write-Host ""
    Read-Host "종료하려면 Enter 키를 누르세요"
    exit 1
}}

# ====================================
# 8. 서비스 시작
# ====================================
Write-Host "[INFO] 서비스 시작 중..." -ForegroundColor $InfoColor
try {{
    Start-Service -Name "WCMS-Client"
    Write-Host "[OK] 서비스 시작 완료" -ForegroundColor $SuccessColor
}} catch {{
    Write-Host "[WARN] 서비스 시작 실패" -ForegroundColor $WarnColor
    Write-Host "수동으로 시작하려면: Start-Service -Name 'WCMS-Client'" -ForegroundColor $WarnColor
    Write-Host ""
}}

# ====================================
# 9. 상태 확인
# ====================================
Write-Host ""
Write-Host "[INFO] 설치 확인 중..." -ForegroundColor $InfoColor
Start-Sleep -Seconds 2

$Service = Get-Service -Name "WCMS-Client" -ErrorAction SilentlyContinue
if ($Service -and $Service.Status -eq "Running") {{
    Write-Host ""
    Write-Host "========================================" -ForegroundColor $SuccessColor
    Write-Host " WCMS 클라이언트 설치 완료!" -ForegroundColor $SuccessColor
    Write-Host "========================================" -ForegroundColor $SuccessColor
    Write-Host " 버전: $Version"
    Write-Host " 서버: $ServerUrl"
    Write-Host " 설치 위치: $InstallDir"
    Write-Host " 설정 파일: $ConfigDir\\config.json"
    Write-Host " 서비스 상태: 실행 중" -ForegroundColor $SuccessColor
    Write-Host "========================================" -ForegroundColor $SuccessColor
    Write-Host ""
    Write-Host "관리 명령:" -ForegroundColor $InfoColor
    Write-Host "  상태 확인: Get-Service -Name 'WCMS-Client'"
    Write-Host "  중지: Stop-Service -Name 'WCMS-Client'"
    Write-Host "  시작: Start-Service -Name 'WCMS-Client'"
    Write-Host "  제거: & '$InstallDir\\WCMS-Client.exe' remove"
    Write-Host "========================================" -ForegroundColor $InfoColor
    Write-Host ""
}} else {{
    Write-Host ""
    Write-Host "========================================" -ForegroundColor $WarnColor
    Write-Host " WCMS 클라이언트 설치 완료 (경고)" -ForegroundColor $WarnColor
    Write-Host "========================================" -ForegroundColor $WarnColor
    Write-Host " 버전: $Version"
    Write-Host " 서버: $ServerUrl"
    Write-Host " 설치 위치: $InstallDir"
    Write-Host " 서비스 상태: 중지됨" -ForegroundColor $WarnColor
    Write-Host "========================================" -ForegroundColor $WarnColor
    Write-Host ""
    Write-Host "[WARN] 서비스가 실행되지 않았습니다." -ForegroundColor $WarnColor
    Write-Host "다음 명령으로 수동 시작하세요:" -ForegroundColor $WarnColor
    Write-Host "  Start-Service -Name 'WCMS-Client'"
    Write-Host ""
    Write-Host "로그 확인: $ConfigDir\\logs\\" -ForegroundColor $InfoColor
    Write-Host "========================================" -ForegroundColor $WarnColor
    Write-Host ""
}}

# ====================================
# 10. 정리
# ====================================
if (Test-Path $TempDir) {{
    Remove-Item -Path $TempDir -Recurse -Force -ErrorAction SilentlyContinue
}}

Write-Host "설치 프로그램을 종료합니다..." -ForegroundColor $InfoColor
Start-Sleep -Seconds 2
'''


@install_bp.route('/install.cmd')
def download_install_cmd():
    """
    Windows Batch 설치 스크립트 다운로드 (동적 생성)

    사용법:
        curl -fsSL http://server:5050/install/install.cmd -o install.cmd && install.cmd && del install.cmd

    Query Parameters:
        server: 서버 URL (기본값: request의 host)

    Returns:
        install.cmd 파일 (text/plain)
    """
    # 서버 URL 결정
    server_url = request.args.get('server')
    if not server_url:
        # 기본값: 현재 요청의 호스트 사용
        server_url = f"{request.scheme}://{request.host}"

    logger.info(f"Generating install.cmd for server: {server_url}")

    script_content = get_install_cmd_script(server_url)

    return Response(
        script_content,
        mimetype='text/plain',
        headers={
            'Content-Disposition': 'attachment; filename=install.cmd',
            'Content-Type': 'text/plain; charset=utf-8'
        }
    )


@install_bp.route('/install.ps1')
def download_install_ps1():
    """
    PowerShell 설치 스크립트 다운로드 (동적 생성)

    사용법:
        iwr -Uri "http://server:5050/install/install.ps1" -OutFile install.ps1; .\\install.ps1; del install.ps1

    Query Parameters:
        server: 서버 URL (기본값: request의 host)

    Returns:
        install.ps1 파일 (text/plain)
    """
    # 서버 URL 결정
    server_url = request.args.get('server')
    if not server_url:
        # 기본값: 현재 요청의 호스트 사용
        server_url = f"{request.scheme}://{request.host}"

    logger.info(f"Generating install.ps1 for server: {server_url}")

    script_content = get_install_ps1_script(server_url)

    return Response(
        script_content,
        mimetype='text/plain',
        headers={
            'Content-Disposition': 'attachment; filename=install.ps1',
            'Content-Type': 'text/plain; charset=utf-8'
        }
    )


@install_bp.route('/version')
def get_version():
    """
    클라이언트 버전 정보 조회 (install.cmd/ps1에서 사용)

    Returns:
        JSON: 버전 정보 및 GitHub Releases 다운로드 URL
    """
    # client.py의 /api/client/version으로 리다이렉트
    # (중복 코드 방지)
    from flask import redirect, url_for
    return redirect(url_for('client.get_version'))

