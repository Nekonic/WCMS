"""Windows 계정 생성 명령.

언어 설정 흐름:
1. Install-Language cmdlet으로 LXP 설치 (Windows 11 전용, 30분 소요 가능)
2. LogonUser + LoadUserProfile로 프로필 강제 생성
3. NTUSER.DAT reg load 후 레지스트리 직접 설정
   - PreferredUILanguageOverride 키 누락 시 비영어 언어 적용 안 됨 (v0.9.8 hotfix)
"""
import subprocess
import tempfile
import os
import logging
from typing import Any

logger = logging.getLogger('wcms')

_LANG_PACK_SCRIPT = r"""param($Language)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$hasCmd = $null -ne (Get-Command Install-Language -ErrorAction SilentlyContinue)
if (-not $hasCmd) { Write-Output "SKIP:Install-Language cmdlet 없음 (Windows 10 또는 모듈 없음)"; exit 0 }

$lxp = Get-InstalledLanguage | Where-Object { $_.LanguageId -like "$Language*" }
if ($lxp) { Write-Output "ALREADY:$($lxp.LanguageId)"; exit 0 }

Write-Output "START:$Language 설치 시작"
$jobStart = Get-Date
$job = Start-Job -ScriptBlock { param($l); Install-Language -Language $l -ErrorAction Stop } -ArgumentList $Language

while ($job.State -eq 'Running') {
    Start-Sleep -Seconds 60
    $elapsed = [int]((Get-Date) - $jobStart).TotalSeconds
    Receive-Job $job | ForEach-Object { Write-Output "LOG:$_" }
    Write-Output "STATUS:${elapsed}초 경과 (State=$($job.State))"
}
Receive-Job $job | ForEach-Object { Write-Output "LOG:$_" }

if ($job.State -eq 'Completed') {
    $lxp2 = Get-InstalledLanguage | Where-Object { $_.LanguageId -like "$Language*" }
    Remove-Job $job -Force
    if ($lxp2) { Write-Output "OK:$($lxp2.LanguageId)"; exit 0 }
    else { Write-Output "FAIL:설치 완료 but LXP 없음"; exit 1 }
} else {
    $err = $job.ChildJobs[0].JobStateInfo.Reason
    Remove-Job $job -Force
    Write-Output "FAIL:$err"; exit 1
}
"""

_LANG_REG_SCRIPT = r"""param($Username, $Password, $Language)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public class WcmsUserEnv {
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    public static extern bool LogonUser(string user, string domain, string pass, int type, int provider, out IntPtr token);

    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Auto)]
    public struct PROFILEINFO {
        public int    dwSize;
        public int    dwFlags;
        public string lpUserName;
        public string lpProfilePath;
        public string lpDefaultPath;
        public string lpServerName;
        public string lpPolicyPath;
        public IntPtr hProfile;
    }
    [DllImport("userenv.dll", CharSet=CharSet.Auto, SetLastError=true)]
    public static extern bool LoadUserProfile(IntPtr hToken, ref PROFILEINFO lpPI);
    [DllImport("userenv.dll", CharSet=CharSet.Auto, SetLastError=true)]
    public static extern bool UnloadUserProfile(IntPtr hToken, IntPtr hProfile);
    [DllImport("kernel32.dll")]
    public static extern bool CloseHandle(IntPtr h);
}
'@

$token = [IntPtr]::Zero
$ok = [WcmsUserEnv]::LogonUser($Username, '.', $Password, 2, 0, [ref]$token)
if ($ok -and $token -ne [IntPtr]::Zero) {
    $pi = New-Object WcmsUserEnv+PROFILEINFO
    $pi.dwSize     = [System.Runtime.InteropServices.Marshal]::SizeOf($pi)
    $pi.dwFlags    = 1
    $pi.lpUserName = $Username
    $loaded = [WcmsUserEnv]::LoadUserProfile($token, [ref]$pi)
    if ($loaded) { [WcmsUserEnv]::UnloadUserProfile($token, $pi.hProfile) | Out-Null }
    [WcmsUserEnv]::CloseHandle($token) | Out-Null
}

Start-Sleep -Seconds 2

$ntuser = "C:\Users\$Username\NTUSER.DAT"
if (-not (Test-Path $ntuser)) { exit 1 }

$hive = "HKU\WCMS_$Username"
reg load $hive $ntuser | Out-Null

$sets = @(
    @("$hive\Control Panel\International",                            "LocaleName",                        "REG_SZ",       $Language),
    @("$hive\Control Panel\Desktop",                                  "PreferredUILanguages",               "REG_MULTI_SZ", $Language),
    @("$hive\Control Panel\Desktop",                                  "PreferredUILanguagesPending",        "REG_MULTI_SZ", $Language),
    @("$hive\Control Panel\Desktop",                                  "PreferredUILanguageOverride",        "REG_MULTI_SZ", $Language),
    @("$hive\Control Panel\Desktop",                                  "MultilingualUserInterfaceLanguages", "REG_MULTI_SZ", $Language),
    @("$hive\Control Panel\International\User Profile",               "Languages",                         "REG_MULTI_SZ", $Language),
    @("$hive\Control Panel\International\User Profile System Backup", "Languages",                         "REG_MULTI_SZ", $Language)
)
foreach ($s in $sets) {
    reg add $s[0] /v $s[1] /t $s[2] /d $s[3] /f | Out-Null
}

[GC]::Collect()
Start-Sleep -Seconds 2
reg unload $hive | Out-Null
"""


def _run_ps(script: str, args: list[str], timeout: int) -> subprocess.CompletedProcess:
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ps1', delete=False, encoding='utf-8') as f:
        f.write(script)
        path = f.name
    try:
        return subprocess.run(
            ['powershell', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', path] + args,
            capture_output=True, text=True, encoding='utf-8', timeout=timeout,
        )
    finally:
        try:
            os.unlink(path)
        except Exception:
            pass


def _install_language_pack(language: str) -> bool:
    logger.info(f"언어 팩 설치 시작: {language}")
    result = _run_ps(_LANG_PACK_SCRIPT, [language], timeout=1800)
    success = False
    for line in result.stdout.splitlines():
        if line.startswith(('OK:', 'ALREADY:', 'SKIP:')):
            logger.info(f"언어 팩: {line}")
            success = True
        elif line.startswith('FAIL:'):
            logger.error(f"언어 팩 설치 실패: {line[5:]}")
        else:
            logger.info(f"언어 팩: {line}")
    return success


def _setup_user_language(username: str, password: str, language: str) -> bool:
    result = _run_ps(_LANG_REG_SCRIPT, [username, password, language], timeout=60)
    if result.returncode == 0:
        logger.info(f"언어 레지스트리 설정 완료: {username} -> {language}")
        return True
    logger.error(f"언어 레지스트리 설정 실패 (rc={result.returncode}): {result.stderr}")
    return False


def execute(data: dict[str, Any]) -> str:
    username = data.get('username', '')
    password = data.get('password', '')
    language = data.get('language')
    if not username or not password:
        return "오류: username, password가 필요합니다."

    lang_ok = True
    if language:
        lang_ok = _install_language_pack(language)
        if not lang_ok:
            logger.warning(f"언어 팩 설치 실패 ({language}), 계정 생성은 계속 진행")

    result = subprocess.run(['net', 'user', username, password, '/add'], capture_output=True, text=True)
    if result.returncode != 0:
        return f"사용자 생성 실패: {result.stderr}"

    msg = f"사용자 계정 생성됨: {username}"
    if language:
        if not lang_ok:
            msg += f" (언어 팩 없음: {language})"
        elif _setup_user_language(username, password, language):
            msg += f" (언어: {language})"
        else:
            msg += f" (언어 설정 실패: {language})"
    return msg