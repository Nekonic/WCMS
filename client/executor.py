"""
명령 실행 모듈
서버에서 수신한 명령(종료, 재시작, 설치, 계정 관리 등)을 실행합니다.
"""
import subprocess
import logging
import os
import glob
import tempfile
from typing import Dict, Any

logger = logging.getLogger('wcms')


class CommandExecutor:
    """Windows 명령 실행 클래스"""

    @staticmethod
    def execute_command(command_type: str, command_data: Dict[str, Any]) -> str:
        """
        명령 타입에 따라 적절한 명령 실행

        Args:
            command_type: 명령 타입 (shutdown, restart, execute, etc)
            command_data: 명령 데이터 (parameters)

        Returns:
            실행 결과 메시지
        """
        # v0.8.0: 'reboot' → 'restart'로 통일
        if command_type == 'reboot':
            command_type = 'restart'

        handlers = {
            'shutdown': lambda: CommandExecutor.shutdown(
                command_data.get('delay', 0),
                command_data.get('message', '')
            ),
            'restart': lambda: CommandExecutor.reboot(
                command_data.get('delay', 0),
                command_data.get('message', '')
            ),
            'execute': lambda: CommandExecutor.execute(
                command_data.get('command', '')
            ),
            'install': lambda: CommandExecutor.install(
                command_data.get('app_id', '')
            ),
            'uninstall': lambda: CommandExecutor.uninstall(
                command_data.get('app_id', '')
            ),
            'download': lambda: CommandExecutor.download(
                command_data.get('url', ''),
                command_data.get('destination')
            ),
            'create_user': lambda: CommandExecutor.create_user(**command_data),
            'delete_user': lambda: CommandExecutor.delete_user(
                command_data.get('username', '')
            ),
            'change_password': lambda: CommandExecutor.change_password(**command_data),
            'message': lambda: CommandExecutor.show_message(
                command_data.get('message', ''),
                command_data.get('duration', 10)
            ),
            'kill_process': lambda: CommandExecutor.kill_process(
                command_data.get('process_name', '')
            ),
        }

        handler = handlers.get(command_type)
        if handler:
            try:
                return handler()
            except Exception as e:
                logger.error(f"명령 실행 오류 ({command_type}): {e}")
                return f"오류: {str(e)}"
        else:
            return f"알 수 없는 명령 타입: {command_type}"

    @staticmethod
    def shutdown(delay: int = 0, message: str = '') -> str:
        """PC 종료"""
        try:
            delay = max(0, delay)
            cmd = ['shutdown', '/s', '/t', str(delay)]
            if message:
                cmd += ['/c', message]
            subprocess.run(cmd)
            return f"종료 명령 실행됨 (지연: {delay}초)"
        except Exception as e:
            return f"종료 실패: {str(e)}"

    @staticmethod
    def reboot(delay: int = 0, message: str = '') -> str:
        """PC 재시작"""
        try:
            delay = max(0, delay)
            cmd = ['shutdown', '/r', '/t', str(delay)]
            if message:
                cmd += ['/c', message]
            subprocess.run(cmd)
            return f"재시작 명령 실행됨 (지연: {delay}초)"
        except Exception as e:
            return f"재시작 실패: {str(e)}"

    @staticmethod
    def execute(command: str) -> str:
        """CMD 명령 실행"""
        if not command:
            return "오류: 실행할 명령어가 없습니다."
        try:
            # PowerShell을 통해 실행하여 경로 문제 완화 시도
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.stdout or result.stderr or "실행 완료"
        except subprocess.TimeoutExpired:
            return "명령 실행 타임아웃 (30초)"
        except Exception as e:
            return f"실행 실패: {str(e)}"

    @staticmethod
    def _ensure_chocolatey_installed() -> bool:
        """Chocolatey 설치 확인 및 설치"""
        # choco 명령 확인
        try:
            result = subprocess.run(['choco', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                return True
        except:
            pass

        # 설치 시도
        logger.info("Chocolatey가 설치되어 있지 않습니다. 설치를 시도합니다...")
        try:
            install_cmd = "Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))"
            result = subprocess.run(
                f'powershell -NoProfile -InputFormat None -ExecutionPolicy Bypass -Command "{install_cmd}"',
                shell=True,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                logger.info("Chocolatey 설치 성공")
                return True
            else:
                logger.error(f"Chocolatey 설치 실패: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Chocolatey 설치 중 오류: {e}")
            return False

    @staticmethod
    def install(app_id: str) -> str:
        """프로그램 설치 (Chocolatey)"""
        if not app_id:
            return "오류: 설치할 프로그램의 패키지 ID가 필요합니다."
        
        # Chocolatey 확인 및 설치
        if not CommandExecutor._ensure_chocolatey_installed():
            return "오류: Chocolatey를 설치할 수 없어 프로그램을 설치할 수 없습니다."

        try:
            # choco.exe는 보통 C:\ProgramData\chocolatey\bin\choco.exe에 있음
            choco_path = r"C:\ProgramData\chocolatey\bin\choco.exe"
            choco_exe = choco_path if os.path.exists(choco_path) else 'choco'
            cmd = [choco_exe, 'install', app_id, '-y', '--force']

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600 # 설치는 시간이 걸릴 수 있음
            )

            if result.returncode == 0:
                return f"설치 완료: {app_id}"
            else:
                error_msg = result.stderr.strip() or result.stdout.strip()
                return f"설치 실패: {app_id} (반환 코드: {result.returncode})\n출력: {error_msg}"

        except subprocess.TimeoutExpired:
            return f"설치 타임아웃: {app_id} (10분 초과)"
        except Exception as e:
            return f"설치 실패: {str(e)}"

    @staticmethod
    def uninstall(app_id: str) -> str:
        """프로그램 삭제 (Chocolatey)"""
        if not app_id:
            return "오류: 삭제할 프로그램의 패키지 ID가 필요합니다."
        
        # Chocolatey 확인 및 설치
        if not CommandExecutor._ensure_chocolatey_installed():
            return "오류: Chocolatey를 설치할 수 없어 프로그램을 삭제할 수 없습니다."

        try:
            choco_path = r"C:\ProgramData\chocolatey\bin\choco.exe"
            choco_exe = choco_path if os.path.exists(choco_path) else 'choco'
            cmd = [choco_exe, 'uninstall', app_id, '-y', '--remove-dependencies']

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600 # 삭제는 시간이 걸릴 수 있음
            )

            if result.returncode == 0:
                return f"삭제 완료: {app_id}"
            else:
                error_msg = result.stderr.strip() or result.stdout.strip()
                return f"삭제 실패: {app_id} (반환 코드: {result.returncode})\n출력: {error_msg}"

        except subprocess.TimeoutExpired:
            return f"삭제 타임아웃: {app_id} (10분 초과)"
        except Exception as e:
            return f"삭제 실패: {str(e)}"

    @staticmethod
    def download(url: str, destination: str = None) -> str:
        """파일 다운로드"""
        if not url:
            return "오류: 다운로드할 파일의 URL이 필요합니다."
        try:
            import requests

            # 저장 경로 설정
            if destination:
                save_path = destination
                # 디렉토리 생성
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
            else:
                # 파일명 추출
                filename = url.split('/')[-1] or 'downloaded_file'
                downloads_folder = os.path.join(os.path.expanduser('~'), 'Downloads')
                os.makedirs(downloads_folder, exist_ok=True)
                save_path = os.path.join(downloads_folder, filename)

            response = requests.get(url, stream=True, timeout=60)
            response.raise_for_status()

            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            actual_size = os.path.getsize(save_path)
            return f"다운로드 완료: {save_path} ({actual_size:,} bytes)"
        except Exception as e:
            return f"다운로드 실패: {str(e)}"

    @staticmethod
    def _install_language_pack(language_code: str) -> bool:
        """LXP(Language Experience Pack) 설치 - Windows 표시 언어에 필요.
        Start-Job으로 Install-Language 실행: NonInteractive의 ShouldProcess 억제 우회.
        lang_test.ps1에서 검증된 방식.
        """
        ps_script = r"""param($Language)
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
    else { Write-Output "FAIL:설치 완료 but LXP 없음 (해당 언어팩이 지원되지 않을 수 있음)"; exit 1 }
} else {
    $err = $job.ChildJobs[0].JobStateInfo.Reason
    Remove-Job $job -Force
    Write-Output "FAIL:$err"; exit 1
}
"""
        script_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode='w', suffix='.ps1', delete=False, encoding='utf-8'
            ) as f:
                f.write(ps_script)
                script_path = f.name

            result = subprocess.run(
                ['powershell', '-NoProfile', '-NonInteractive',
                 '-ExecutionPolicy', 'Bypass', '-File', script_path, language_code],
                capture_output=True, text=True, timeout=1800
            )
            success = False
            for line in result.stdout.splitlines():
                if line.startswith('OK:') or line.startswith('ALREADY:'):
                    logger.info(f"언어 팩 준비 완료: {line}")
                    success = True
                elif line.startswith('SKIP:'):
                    logger.warning(f"언어 팩: {line[5:]}")
                    success = True
                elif line.startswith('FAIL:'):
                    logger.error(f"언어 팩 설치 실패: {line[5:]}")
                elif line.startswith('START:') or line.startswith('STATUS:') or line.startswith('LOG:'):
                    logger.info(f"언어 팩: {line}")
            if result.stderr:
                logger.error(f"언어 팩 stderr: {result.stderr.strip()}")
            return success
        except subprocess.TimeoutExpired:
            logger.error(f"언어 팩 설치 타임아웃 (30분): {language_code}")
            return False
        except Exception as e:
            logger.error(f"언어 팩 설치 오류: {e}")
            return False
        finally:
            if script_path and os.path.exists(script_path):
                try:
                    os.unlink(script_path)
                except Exception:
                    pass

    @staticmethod
    def _setup_user_language(username: str, password: str, language: str) -> bool:
        """계정 프로필 강제 생성 후 NTUSER.DAT에 언어 레지스트리 직접 설정.
        lang_test.ps1 에서 검증된 방식: LogonUser + LoadUserProfile + reg load/add/unload
        """
        ps_script = r"""param($Username, $Password, $Language)

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
        script_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode='w', suffix='.ps1', delete=False, encoding='utf-8'
            ) as f:
                f.write(ps_script)
                script_path = f.name

            result = subprocess.run(
                ['powershell', '-NoProfile', '-NonInteractive',
                 '-ExecutionPolicy', 'Bypass', '-File', script_path,
                 username, password, language],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                logger.info(f"언어 레지스트리 설정 완료: {username} -> {language}")
                return True
            else:
                logger.error(f"언어 레지스트리 설정 실패 (rc={result.returncode}): {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"언어 레지스트리 설정 오류: {e}")
            return False
        finally:
            if script_path and os.path.exists(script_path):
                try:
                    os.unlink(script_path)
                except Exception:
                    pass

    @staticmethod
    def create_user(username, password, full_name=None, comment=None, language=None):
        """Windows 사용자 계정 생성"""
        return CommandExecutor.manage_account('create', username, password, full_name, comment, language)

    @staticmethod
    def delete_user(username):
        """Windows 사용자 계정 삭제"""
        return CommandExecutor.manage_account('delete', username)

    @staticmethod
    def change_password(username, new_password):
        """Windows 사용자 비밀번호 변경"""
        return CommandExecutor.manage_account('change_password', username, new_password)

    @staticmethod
    def manage_account(action: str, username: str, password: str = None,
                      full_name: str = None, comment: str = None,
                      language: str = None) -> str:
        """Windows 계정 관리 통합 함수"""
        try:
            if action == 'create':
                if not password:
                    return "오류: 비밀번호가 필요합니다"

                # 1. 언어 팩 설치 (계정 생성 전)
                lang_pack_ok = True
                if language:
                    lang_pack_ok = CommandExecutor._install_language_pack(language)
                    if not lang_pack_ok:
                        logger.warning(f"언어 팩 설치 실패 ({language}), 계정 생성은 계속 진행")

                # 2. 계정 생성
                result = subprocess.run(
                    ['net', 'user', username, password, '/add'],
                    capture_output=True, text=True
                )

                if result.returncode == 0:
                    msg = f"사용자 계정 생성됨: {username}"

                    if full_name:
                        subprocess.run(
                            ['wmic', 'useraccount', f'where name="{username}"', 'set', f'fullname="{full_name}"'],
                            capture_output=True
                        )
                    
                    # 3. 언어 설정 (프로필 강제 생성 + NTUSER.DAT 레지스트리 직접 설정)
                    if language:
                        if not lang_pack_ok:
                            msg += f" (언어 팩 없음: {language})"
                        elif CommandExecutor._setup_user_language(username, password, language):
                            msg += f" (언어: {language})"
                        else:
                            msg += f" (언어 설정 실패: {language})"

                    return msg
                else:
                    return f"사용자 생성 실패: {result.stderr}"

            elif action == 'delete':
                result = subprocess.run(
                    ['net', 'user', username, '/delete'],
                    capture_output=True, text=True
                )

                if result.returncode == 0:
                    return f"사용자 계정 삭제됨: {username}"
                else:
                    return f"사용자 삭제 실패: {result.stderr}"

            elif action == 'change_password':
                if not password:
                    return "오류: 새 비밀번호가 필요합니다"

                result = subprocess.run(
                    ['net', 'user', username, password],
                    capture_output=True, text=True
                )

                if result.returncode == 0:
                    return f"비밀번호 변경됨: {username}"
                else:
                    return f"비밀번호 변경 실패: {result.stderr}"

            else:
                return f"알 수 없는 계정 작업: {action}"

        except Exception as e:
            return f"계정 관리 오류: {str(e)}"


    @staticmethod
    def show_message(message: str, duration: int = 10) -> str:
        """사용자에게 메시지 표시"""
        try:
            msg_exe = r'C:\Windows\System32\msg.exe'
            if not os.path.exists(msg_exe):
                msg_exe = 'msg'
            result = subprocess.run([msg_exe, '*', message], capture_output=True, text=True, timeout=5)

            if result.returncode == 0:
                return f"메시지 표시됨: {message}"
            else:
                return f"메시지 표시 실패: {result.stderr}"
        except Exception as e:
            return f"메시지 표시 오류: {str(e)}"

    @staticmethod
    def kill_process(process_name: str) -> str:
        """프로세스 강제 종료"""
        try:
            if not process_name:
                return "프로세스 이름이 지정되지 않음"

            if not process_name.lower().endswith('.exe'):
                process_name += '.exe'

            result = subprocess.run(
                ['taskkill', '/F', '/IM', process_name],
                capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0:
                return f"프로세스 종료됨: {process_name}"
            elif "찾을 수 없습니다" in result.stderr or "not found" in result.stderr.lower():
                return f"프로세스를 찾을 수 없음: {process_name}"
            else:
                return f"프로세스 종료 실패: {result.stderr}"
        except Exception as e:
            return f"프로세스 종료 오류: {str(e)}"
