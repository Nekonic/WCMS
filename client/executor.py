"""
명령 실행 모듈
서버에서 수신한 명령(종료, 재시작, 설치, 계정 관리 등)을 실행합니다.
"""
import subprocess
import logging
import os
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
            cmd = f'shutdown /s /t {delay}'
            if message:
                cmd += f' /c "{message}"'

            subprocess.run(cmd, shell=True)
            return f"종료 명령 실행됨 (지연: {delay}초)"
        except Exception as e:
            return f"종료 실패: {str(e)}"

    @staticmethod
    def reboot(delay: int = 0, message: str = '') -> str:
        """PC 재시작"""
        try:
            delay = max(0, delay)
            cmd = f'shutdown /r /t {delay}'
            if message:
                cmd += f' /c "{message}"'

            subprocess.run(cmd, shell=True)
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
            # cmd /c로 실행하되, winget 같은 명령은 powershell로 감싸서 시도해볼 수도 있음
            # 하지만 일반적인 execute 명령은 cmd가 기본
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
    def install(app_id: str) -> str:
        """프로그램 설치 (winget)"""
        if not app_id:
            return "오류: 설치할 프로그램의 App ID가 필요합니다."
        
        try:
            # 1. winget 직접 실행 시도
            # 2. 실패 시 PowerShell을 통해 실행 시도 (경로 문제 해결)
            
            # winget 명령 구성
            winget_cmd = f'winget install -e --id {app_id} --silent --accept-package-agreements --accept-source-agreements'
            
            # PowerShell을 통해 실행 (LocalSystem 계정에서 winget 경로 찾기 위해)
            # -NoProfile -ExecutionPolicy Bypass 옵션 추가
            ps_cmd = f'powershell -NoProfile -ExecutionPolicy Bypass -Command "{winget_cmd}"'
            
            result = subprocess.run(
                ps_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                return f"설치 완료: {app_id}"
            else:
                # PowerShell 실패 시 에러 메시지 반환
                error_msg = result.stderr.strip() or result.stdout.strip()
                return f"설치 실패: {app_id} (반환 코드: {result.returncode})\n출력: {error_msg}"

        except subprocess.TimeoutExpired:
            return f"설치 타임아웃: {app_id} (5분 초과)"
        except Exception as e:
            return f"설치 실패: {str(e)}"

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
    def create_user(username, password, full_name=None, comment=None):
        """Windows 사용자 계정 생성"""
        return CommandExecutor.manage_account('create', username, password, full_name, comment)

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
                      full_name: str = None, comment: str = None) -> str:
        """Windows 계정 관리 통합 함수"""
        try:
            if action == 'create':
                if not password:
                    return "오류: 비밀번호가 필요합니다"

                cmd = f'net user {username} {password} /add'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

                if result.returncode == 0:
                    if full_name:
                        subprocess.run(
                            f'wmic useraccount where name="{username}" set fullname="{full_name}"',
                            shell=True, capture_output=True
                        )
                    return f"사용자 계정 생성됨: {username}"
                else:
                    return f"사용자 생성 실패: {result.stderr}"

            elif action == 'delete':
                cmd = f'net user {username} /delete'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

                if result.returncode == 0:
                    return f"사용자 계정 삭제됨: {username}"
                else:
                    return f"사용자 삭제 실패: {result.stderr}"

            elif action == 'change_password':
                if not password:
                    return "오류: 새 비밀번호가 필요합니다"

                cmd = f'net user {username} {password}'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

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
            cmd = f'msg * "{message}"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)

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

            cmd = f'taskkill /F /IM "{process_name}"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                return f"프로세스 종료됨: {process_name}"
            elif "찾을 수 없습니다" in result.stderr or "not found" in result.stderr.lower():
                return f"프로세스를 찾을 수 없음: {process_name}"
            else:
                return f"프로세스 종료 실패: {result.stderr}"
        except Exception as e:
            return f"프로세스 종료 오류: {str(e)}"
