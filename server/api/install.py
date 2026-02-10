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
    install.cmd 스크립트 생성 (v0.8.0 - PIN 인증 포함)

    Args:
        server_url: 서버 URL (예: http://localhost:5050)

    Returns:
        Windows Batch 스크립트 문자열
    """
    # SERVER_URL 정규화 (끝에 슬래시 보장)
    if not server_url.endswith('/'):
        server_url = server_url + '/'

    return f'''@echo off
chcp 65001 >nul
REM WCMS Client Auto-Install Script (v0.8.2)
REM GitHub: https://github.com/{GITHUB_REPO}

SETLOCAL EnableDelayedExpansion

echo ========================================
echo  WCMS Client Auto-Install (v0.8.2)
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
REM 2. PIN Input (v0.8.0)
REM ====================================
:ASK_PIN
echo.
echo Please enter the 6-digit registration PIN.
echo (Ask your administrator for the PIN)
echo.
set /p PIN="Registration PIN (6 digits): "

REM PIN Format Validation
echo %PIN%| findstr /r "^[0-9][0-9][0-9][0-9][0-9][0-9]$" >nul
if %errorLevel% neq 0 (
    echo [ERROR] PIN must be exactly 6 digits.
    goto ASK_PIN
)

echo [OK] PIN format valid: %PIN%

REM ====================================
REM 3. Connect to Server and Get Latest Version
REM ====================================
echo [INFO] Checking latest version from server...
SET "SERVER_URL={server_url}"

REM Remove trailing slash if exists (will be added in API calls)
if "%SERVER_URL:~-1%"=="/" SET "SERVER_URL=%SERVER_URL:~0,-1%"

echo [INFO] Server URL: %SERVER_URL%

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
REM 4. Download Client
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
REM 5. Create Installation Directories
REM ====================================
echo [INFO] Creating installation directories...
SET INSTALL_DIR=C:\\Program Files\\WCMS
SET CONFIG_DIR=C:\\ProgramData\\WCMS

if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
if not exist "%CONFIG_DIR%" mkdir "%CONFIG_DIR%"

REM ====================================
REM 6. Copy Files
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
REM 7. Create config.json (v0.8.0 with PIN)
REM ====================================
echo [INFO] Creating configuration file...

REM Ensure SERVER_URL ends with / for config.json
SET "CONFIG_URL=%SERVER_URL%/"

(
    echo {{
    echo   "SERVER_URL": "%CONFIG_URL%",
    echo   "REGISTRATION_PIN": "%PIN%",
    echo   "HEARTBEAT_INTERVAL": 300,
    echo   "COMMAND_POLL_INTERVAL": 2,
    echo   "LOG_LEVEL": "INFO"
    echo }}
) > "%CONFIG_DIR%\\config.json"

if %errorLevel% neq 0 (
    echo [ERROR] Failed to create config.json
    pause
    exit /b 1
)
echo [OK] Configuration file created with PIN

REM ====================================
REM 8. Install Service
REM ====================================
echo [INFO] Installing Windows service...

REM Check and stop existing service
sc query WCMS-Client >nul 2>&1
if %errorLevel% equ 0 (
    echo [INFO] Existing service detected. Stopping and removing...
    net stop WCMS-Client >nul 2>&1
    timeout /t 2 >nul
    sc delete WCMS-Client >nul 2>&1
    echo [INFO] Waiting for service cleanup...
    timeout /t 5 >nul
)

REM Install service (pywin32 service)
echo [INFO] Installing Windows service...
echo [DEBUG] Executing: "%INSTALL_DIR%\\WCMS-Client.exe" install
echo [INFO] Maximum wait time: 10 seconds
echo.

REM Create logs directory
if not exist "%CONFIG_DIR%\\logs" mkdir "%CONFIG_DIR%\\logs"

REM Use PowerShell to run with timeout and kill if hung
powershell -Command "& {{ $job = Start-Job -ScriptBlock {{ & '%INSTALL_DIR%\\WCMS-Client.exe' install 2>&1 }}; $completed = Wait-Job $job -Timeout 10; if ($completed) {{ Receive-Job $job; Remove-Job $job }} else {{ Write-Host '[WARN] Installation timed out after 10 seconds, stopping process...'; Stop-Job $job; Remove-Job $job; Get-Process 'WCMS-Client' -ErrorAction SilentlyContinue | Stop-Process -Force }}}}"

echo.
echo [INFO] Installation command completed or timed out
echo [INFO] Waiting for service registration...
timeout /t 2 >nul

REM Check if service was actually registered
echo [INFO] Checking service registration...
sc query WCMS-Client >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] Service not registered
    echo.
    echo The installation command above should show the actual error.
    echo If you see "ModuleNotFoundError" or "ImportError", the EXE
    echo was not built correctly with pywin32 dependencies.
    echo.
    echo Please check:
    echo   1. Install log: %CONFIG_DIR%\\logs\\install.log
    echo   2. Rebuild with: python manage.py build
    echo.
    pause
    exit /b 1
)

echo [OK] Service successfully registered!
echo.
echo [INFO] Configuring auto-start...
sc config WCMS-Client start= auto
if %errorLevel% neq 0 (
    echo [WARN] Failed to configure auto-start
)

REM Verify service was installed
echo [INFO] Checking service registration...
sc query WCMS-Client >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] Service installation failed - service not found
    echo.
    echo The executable ran but service was not registered.
    echo Check logs at: %CONFIG_DIR%\\logs\\
    echo.
    pause
    exit /b 1
)
echo [OK] Service installed and registered (auto-start enabled)

REM ====================================
REM 9. Start Service
REM ====================================
echo [INFO] Starting service...
net start WCMS-Client >nul 2>&1
set START_EXIT=%errorLevel%

if %START_EXIT% neq 0 (
    echo [WARN] Service start failed ^(exit code: %START_EXIT%^)
    echo.
    echo This is OK - the service will start automatically on next boot.
    echo The service is configured to auto-start.
    echo.
    echo To manually start now:
    echo   net start WCMS-Client
    echo.
    echo To check service status:
    echo   sc query WCMS-Client
    echo.
    echo Installation will continue...
    timeout /t 3 >nul
) else (
    echo [OK] Service started successfully
)

REM ====================================
REM 10. Installation Complete
REM ====================================
echo.
echo ========================================
echo  Installation Complete!
echo ========================================
echo.
echo Installation Directory: %INSTALL_DIR%
echo Configuration Directory: %CONFIG_DIR%
echo Service Name: WCMS-Client
echo Server URL: %CONFIG_URL%
echo Registration PIN: %PIN%
echo Polling Interval: 2 seconds
echo.

REM Show log files for troubleshooting
echo ========== Log Files ==========
if exist "%CONFIG_DIR%\\logs\\install.log" (
    echo.
    echo [install.log]
    powershell -Command "Get-Content '%CONFIG_DIR%\\logs\\install.log' -Encoding UTF8 -ErrorAction SilentlyContinue"
)
if exist "%CONFIG_DIR%\\logs\\installer.log" (
    echo.
    echo [installer.log]
    powershell -Command "Get-Content '%CONFIG_DIR%\\logs\\installer.log' -Encoding UTF8 -ErrorAction SilentlyContinue"
)
if exist "%CONFIG_DIR%\\logs\\client.log" (
    echo.
    echo [client.log - last 30 lines]
    powershell -Command "Get-Content '%CONFIG_DIR%\\logs\\client.log' -Encoding UTF8 -Tail 30 -ErrorAction SilentlyContinue"
)
echo ==============================
echo.

echo The service is now running and will:
echo   - Register with server using PIN
echo   - Send heartbeat every 5 minutes
echo   - Poll for commands every 2 seconds
echo   - Automatically start on system boot
echo.
echo To check service status:
echo   sc query WCMS-Client
echo.
echo To view logs:
echo   type "%CONFIG_DIR%\\logs\\client.log"
echo.
pause

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
# 2. PIN 입력 (v0.8.0)
# ====================================
Write-Host ""
Write-Host "등록 PIN을 입력하세요." -ForegroundColor $InfoColor
Write-Host "(관리자에게 6자리 PIN을 문의하세요)" -ForegroundColor $InfoColor
Write-Host ""

do {{
    $Pin = Read-Host "Registration PIN (6 digits)"
    
    if ($Pin -notmatch '^[0-9]{{6}}$') {{
        Write-Host "[ERROR] PIN은 정확히 6자리 숫자여야 합니다." -ForegroundColor $ErrorColor
        Write-Host ""
    }}
}} while ($Pin -notmatch '^[0-9]{{6}}$')

Write-Host "[OK] PIN 형식 확인: $Pin" -ForegroundColor $SuccessColor

# ====================================
# 3. 서버 연결 및 최신 버전 조회
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
# 6. config.json 생성 (v0.8.0 - PIN 포함)
# ====================================
Write-Host "[INFO] 설정 파일 생성 중..." -ForegroundColor $InfoColor

# SERVER_URL 정규화 (끝에 / 추가)
if (-not $ServerUrl.EndsWith('/')) {{
    $ServerUrl = $ServerUrl + '/'
}}

$Config = @{{
    SERVER_URL = $ServerUrl
    REGISTRATION_PIN = $Pin
    HEARTBEAT_INTERVAL = 300
    COMMAND_POLL_INTERVAL = 2
    LOG_LEVEL = "INFO"
}} | ConvertTo-Json -Depth 10

try {{
    Set-Content -Path "$ConfigDir\\config.json" -Value $Config -Encoding UTF8
    Write-Host "[OK] 설정 파일 생성 완료 (PIN 포함)" -ForegroundColor $SuccessColor
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
    Start-Sleep -Seconds 2
    
    # Auto-start 설정
    sc.exe config WCMS-Client start= auto | Out-Null
    
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
