"""
명령 실행 모듈
서버에서 수신한 명령(종료, 재시작, 설치, 계정 관리 등)을 실행합니다.
"""
import subprocess
import logging
import os
import glob
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
        """언어 팩 설치 (PowerShell)"""
        try:
            # 1. 이미 설치되어 있는지 확인
            check_cmd = f"Get-InstalledLanguage -Language {language_code}"
            result = subprocess.run(
                f'powershell -NoProfile -Command "{check_cmd}"',
                shell=True, capture_output=True, text=True
            )
            
            if result.returncode == 0 and language_code in result.stdout:
                logger.info(f"언어 팩 이미 설치됨: {language_code}")
                return True
                
            # 2. 설치 시도 (Install-Language)
            # -CopyToSettings: 시스템 설정 복사 (선택 사항, 여기선 생략)
            logger.info(f"언어 팩 설치 시작: {language_code}")
            install_cmd = f"Install-Language -Language {language_code}"
            
            result = subprocess.run(
                f'powershell -NoProfile -Command "{install_cmd}"',
                shell=True, capture_output=True, text=True, timeout=1800 # 설치 시간 고려 (30분)
            )
            
            if result.returncode == 0:
                logger.info(f"언어 팩 설치 성공: {language_code}")
                return True
            else:
                logger.error(f"언어 팩 설치 실패: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"언어 팩 설치 중 오류: {e}")
            return False

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
                if language:
                    CommandExecutor._install_language_pack(language)

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
                    
                    # 3. 언어 설정 (RunOnce 레지스트리 활용)
                    if language:
                        try:
                            # RunOnce 키에 등록할 명령어 생성
                            # 로그 기록 추가: >> C:\Temp\lang_log.txt
                            log_path = r"C:\ProgramData\WCMS\logs\lang_setup.log"
                            
                            # PowerShell 명령어 구성
                            # 1. 로그 기록
                            # 2. 언어 목록 설정 (입력기)
                            # 3. 표시 언어(UI) 강제 설정 (Set-WinUILanguageOverride)
                            # 4. 지역/문화권 설정 (Set-Culture)
                            ps_script = f"""
                            $log = '{log_path}';
                            $lang = '{language}';
                            Add-Content -Path $log -Value ('[' + (Get-Date) + '] Starting language setup for {username} to ' + $lang);
                            try {{
                                # 1. 언어 목록 및 입력기 설정
                                Set-WinUserLanguageList -LanguageList $lang -Force -ErrorAction Stop;
                                Add-Content -Path $log -Value 'Success: Set-WinUserLanguageList';
                                
                                # 2. Windows 표시 언어(UI) 설정
                                Set-WinUILanguageOverride -Language $lang -ErrorAction Stop;
                                Add-Content -Path $log -Value 'Success: Set-WinUILanguageOverride';
                                
                                # 3. 지역/문화권 설정 (날짜, 시간 형식 등)
                                Set-Culture -CultureInfo $lang -ErrorAction Stop;
                                Add-Content -Path $log -Value 'Success: Set-Culture';

                            }} catch {{
                                Add-Content -Path $log -Value ('Error: ' + $_.Exception.Message);
                            }}
                            """
                            
                            # 한 줄로 변환 (공백 제거)
                            ps_cmd = ps_script.replace('\n', ' ').replace('    ', '')
                            
                            # cmd에서 실행할 전체 명령
                            reg_cmd = f'cmd /c if /i "%USERNAME%"=="{username}" powershell -WindowStyle Hidden -Command "{ps_cmd}"'
                            
                            # reg add 명령 실행
                            reg_key = r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce"
                            reg_value = f"SetLang_{username}"
                            
                            subprocess.run(
                                ['reg', 'add', reg_key, '/v', reg_value, '/t', 'REG_SZ', '/d', reg_cmd, '/f'],
                                check=True, capture_output=True
                            )
                            
                            msg += f" (언어 설정 예약됨: {language})"
                            logger.info(f"RunOnce 등록 성공: {reg_value} -> {language}")
                            
                        except Exception as e:
                            logger.error(f"RunOnce 등록 실패: {e}")
                            msg += " (언어 설정 예약 실패)"
                        
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
            result = subprocess.run(['msg', '*', message], capture_output=True, text=True, timeout=5)

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
