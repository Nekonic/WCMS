import subprocess
import json
import os


class CommandExecutor:
    @staticmethod
    def shutdown():
        try:
            subprocess.run("shutdown /s /t 30", shell=True)
            return "종료 명령 실행됨"
        except Exception as e:
            return f"종료 실패: {str(e)}"

    @staticmethod
    def reboot():
        try:
            subprocess.run("shutdown /r /t 30", shell=True)
            return "재시작 명령 실행됨"
        except Exception as e:
            return f"재시작 실패: {str(e)}"

    @staticmethod
    def install(app_name):
        """winget 설치"""
        try:
            result = subprocess.run(
                f'winget install -e --id {app_name} -h',
                shell=True,
                capture_output=True,
                text=True,
                timeout=300
            )
            return f"설치 완료: {app_name}\n{result.stdout}"
        except Exception as e:
            return f"설치 실패: {str(e)}"

    @staticmethod
    def execute(command):
        """임의의 명령어 실행"""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.stdout + result.stderr
        except Exception as e:
            return f"실행 실패: {str(e)}"

    @staticmethod
    def download_file(file_url, save_path):
        """파일 다운로드"""
        try:
            import requests
            r = requests.get(file_url, stream=True)
            with open(save_path, 'wb') as f:
                f.write(r.content)
            return f"다운로드 완료: {save_path}"
        except Exception as e:
            return f"다운로드 실패: {str(e)}"

    @staticmethod
    def execute_command(cmd_type, cmd_data):
        """통합 명령 실행"""
        if cmd_type == 'shutdown':
            return CommandExecutor.shutdown()
        elif cmd_type == 'reboot':
            return CommandExecutor.reboot()
        elif cmd_type == 'install':
            return CommandExecutor.install(cmd_data.get('app_name'))
        elif cmd_type == 'execute':
            return CommandExecutor.execute(cmd_data.get('command'))
        elif cmd_type == 'download':
            return CommandExecutor.download_file(
                cmd_data.get('url'),
                cmd_data.get('path')
            )
        else:
            return f"알 수 없는 명령: {cmd_type}"
