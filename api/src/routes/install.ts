import { Hono } from 'hono'
import { desc } from 'drizzle-orm'
import { db } from '../db/index.js'
import { clientVersions } from '../db/schema.js'

export const installRouter = new Hono()

const SERVER_URL = process.env.WCMS_SERVER_URL ?? 'http://localhost:3000'

// Windows Batch 설치 스크립트
installRouter.get('/install.cmd', (c) => {
  const script = `@echo off
chcp 65001 >nul
echo WCMS Client Installer
echo ====================

set SERVER_URL=${SERVER_URL}
set INSTALL_DIR=C:\\Program Files\\WCMS
set CONFIG_DIR=C:\\ProgramData\\WCMS

:: 관리자 권한 확인
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] 관리자 권한으로 실행해주세요.
    pause & exit /b 1
)

:: 설치 디렉토리 생성
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
if not exist "%CONFIG_DIR%\\logs" mkdir "%CONFIG_DIR%\\logs"

:: 최신 버전 다운로드
echo [*] WCMS-Client.exe 다운로드 중...
curl -fsSL "%SERVER_URL%/api/client/version" -o "%TEMP%\\wcms_version.json"
for /f "tokens=2 delims=:, " %%a in ('findstr "download_url" "%TEMP%\\wcms_version.json"') do set DOWNLOAD_URL=%%~a

if "%DOWNLOAD_URL%"=="" (
    echo [ERROR] 다운로드 URL을 가져올 수 없습니다.
    pause & exit /b 1
)

curl -fsSL "%DOWNLOAD_URL%" -o "%INSTALL_DIR%\\WCMS-Client.exe"

:: 서비스 설치
echo [*] 서비스 설치 중...
"%INSTALL_DIR%\\WCMS-Client.exe" install

echo.
echo [완료] WCMS 클라이언트가 설치되었습니다.
echo config: %CONFIG_DIR%\\config.json 에 PIN을 입력하세요.
pause
`
  c.header('Content-Type', 'text/plain; charset=utf-8')
  c.header('Content-Disposition', 'attachment; filename="install.cmd"')
  return c.text(script)
})

// PowerShell 설치 스크립트
installRouter.get('/install.ps1', (c) => {
  const script = `#Requires -RunAsAdministrator
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

$ServerUrl = '${SERVER_URL}'
$InstallDir = 'C:\\Program Files\\WCMS'
$ConfigDir  = 'C:\\ProgramData\\WCMS'

Write-Host 'WCMS Client Installer' -ForegroundColor Cyan

# 디렉토리 생성
@($InstallDir, "$ConfigDir\\logs") | ForEach-Object {
    if (-not (Test-Path $_)) { New-Item -ItemType Directory -Path $_ -Force | Out-Null }
}

# 최신 버전 정보 조회
Write-Host '[*] 버전 정보 조회 중...'
$versionInfo = Invoke-RestMethod -Uri "$ServerUrl/api/client/version"
if (-not $versionInfo.download_url) { throw '다운로드 URL을 가져올 수 없습니다.' }

# 다운로드
Write-Host "[*] WCMS-Client.exe 다운로드: $($versionInfo.version)"
Invoke-WebRequest -Uri $versionInfo.download_url -OutFile "$InstallDir\\WCMS-Client.exe"

# 서비스 설치
Write-Host '[*] 서비스 설치 중...'
& "$InstallDir\\WCMS-Client.exe" install

Write-Host '[완료] WCMS 클라이언트가 설치되었습니다.' -ForegroundColor Green
Write-Host "config: $ConfigDir\\config.json 에 PIN을 입력하세요."
`
  c.header('Content-Type', 'text/plain; charset=utf-8')
  c.header('Content-Disposition', 'attachment; filename="install.ps1"')
  return c.text(script)
})

// 버전 조회 (하위 호환)
installRouter.get('/version', (c) => {
  return c.redirect('/api/client/version', 302)
})