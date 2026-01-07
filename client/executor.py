"""
명령 실행 모듈
서버에서 수신한 명령(종료, 재시작, 설치, 계정 관리 등)을 실행합니다.
"""
import subprocess
import logging
from typing import Dict, Any

logger = logging.getLogger('wcms')


class CommandExecutor:
    """Windows 명령 실행 클래스"""

    @staticmethod
    def execute_command(command_type: str, command_data: Dict[str, Any]) -> str:
        """
        명령 타입에 따라 적절한 명령 실행

        Args:
            command_type: 명령 타입 (shutdown, reboot, execute, etc)
            command_data: 명령 데이터

        Returns:
            실행 결과 메시지
        """
        handlers = {
            'shutdown': CommandExecutor.shutdown,
            'reboot': CommandExecutor.reboot,
            'execute': CommandExecutor.execute,
            'install': lambda: CommandExecutor.install(command_data.get('app_name', '')),
            'download': lambda: CommandExecutor.download(command_data.get('url', '')),
            'create_user': lambda: CommandExecutor.create_user(**command_data),
            'delete_user': lambda: CommandExecutor.delete_user(command_data.get('username', '')),
            'change_password': lambda: CommandExecutor.change_password(**command_data),
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
    def shutdown() -> str:
        """PC 종료"""
        try:
            subprocess.run("shutdown /s /t 3", shell=True)
            return "종료 명령 실행됨"
        except Exception as e:
            return f"종료 실패: {str(e)}"

    @staticmethod
    def reboot() -> str:
        """PC 재시작"""
        try:
            subprocess.run("shutdown /r /t 3", shell=True)
            return "재시작 명령 실행됨"
        except Exception as e:
            return f"재시작 실패: {str(e)}"

    @staticmethod
    def execute(command: str) -> str:
        """CMD 명령 실행"""
        try:
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
    def install(app_name: str) -> str:
        """프로그램 설치 (winget)"""
        try:
            # winget이 설치되어 있는지 확인
            check_result = subprocess.run(
                'winget --version',
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )

            if check_result.returncode != 0:
                return "오류: winget이 설치되어 있지 않습니다. Windows 11 또는 최신 Windows 10이 필요합니다."

            # winget으로 설치 (자동 동의 옵션 포함)
            result = subprocess.run(
                f'winget install -e --id {app_name} --silent --accept-package-agreements --accept-source-agreements',
                shell=True,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                return f"설치 완료: {app_name}"
            else:
                return f"설치 실패: {app_name} (반환 코드: {result.returncode})"
        except subprocess.TimeoutExpired:
            return f"설치 타임아웃: {app_name} (5분 초과)"
        except Exception as e:
            return f"설치 실패: {str(e)}"

    @staticmethod
    def download(url: str) -> str:
        """파일 다운로드"""
        try:
            import requests
            import os

            # 파일명 추출
            filename = url.split('/')[-1] or 'downloaded_file'
            save_path = os.path.join(os.path.expanduser('~'), 'Downloads', filename)

            # Downloads 디렉토리 생성
            os.makedirs(os.path.dirname(save_path), exist_ok=True)

            response = requests.get(url, stream=True, timeout=60)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

            actual_size = os.path.getsize(save_path)
            return f"다운로드 완료: {save_path} ({actual_size:,} bytes)"
        except Exception as e:
            return f"다운로드 실패: {str(e)}"

    @staticmethod
    def create_user(username, password, full_name=None, comment=None):
        """Windows 사용자 계정 생성 (하위 호환성)"""
        return CommandExecutor.manage_account('create', username, password, full_name, comment)

    @staticmethod
    def delete_user(username):
        """Windows 사용자 계정 삭제 (하위 호환성)"""
        return CommandExecutor.manage_account('delete', username)

    @staticmethod
    def change_password(username, new_password):
        """Windows 사용자 비밀번호 변경 (하위 호환성)"""
        return CommandExecutor.manage_account('change_password', username, new_password)

    @staticmethod
    def execute_command(cmd_type, cmd_data):
        """통합 명령 실행"""
        if cmd_type == 'power':
            # 전원 관리
            action = cmd_data.get('action')
            if action == 'shutdown':
                return CommandExecutor.shutdown()
            elif action == 'restart':
                return CommandExecutor.reboot()
            elif action == 'logout':
                return CommandExecutor.execute('shutdown /l')
            else:
                return f"알 수 없는 전원 관리 작업: {action}"

        elif cmd_type == 'shutdown':  # 하위 호환성
            return CommandExecutor.shutdown()

        elif cmd_type == 'reboot':  # 하위 호환성
            return CommandExecutor.reboot()

        elif cmd_type == 'install':
            # winget 설치
            app_id = cmd_data.get('app_id') or cmd_data.get('app_name')
            return CommandExecutor.install(app_id)

        elif cmd_type == 'execute':
            # CMD 명령 실행
            return CommandExecutor.execute(cmd_data.get('command'))

        elif cmd_type == 'download':
            # 파일 다운로드
            return CommandExecutor.download_file(
                cmd_data.get('url'),
                cmd_data.get('destination') or cmd_data.get('path')
            )

        elif cmd_type == 'account':
            # 계정 관리
            return CommandExecutor.manage_account(
                cmd_data.get('action'),
                cmd_data.get('username'),
                cmd_data.get('password'),
                cmd_data.get('full_name'),
                cmd_data.get('comment')
            )

        elif cmd_type == 'create_user':  # 하위 호환성
            return CommandExecutor.create_user(
                cmd_data.get('username'),
                cmd_data.get('password'),
                cmd_data.get('full_name'),
                cmd_data.get('comment')
            )

        elif cmd_type == 'delete_user':  # 하위 호환성
            return CommandExecutor.delete_user(cmd_data.get('username'))

        elif cmd_type == 'change_password':  # 하위 호환성
            return CommandExecutor.change_password(
                cmd_data.get('username'),
                cmd_data.get('new_password') or cmd_data.get('password')
            )

        else:
            return f"알 수 없는 명령 타입: {cmd_type}"
