import subprocess


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
    def create_user(username, password, full_name=None, comment=None):
        """Windows 사용자 계정 생성"""
        try:
            # 계정 생성
            cmd = f'net user "{username}" "{password}" /add'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                return f"계정 생성 실패: {result.stderr}"

            # 전체 이름 설정 (옵션)
            if full_name:
                subprocess.run(
                    f'wmic useraccount where name="{username}" set fullname="{full_name}"',
                    shell=True, capture_output=True, timeout=30
                )

            # 설명 설정 (옵션)
            if comment:
                subprocess.run(
                    f'net user "{username}" /comment:"{comment}"',
                    shell=True, capture_output=True, timeout=30
                )

            return f"계정 생성 완료: {username}"
        except Exception as e:
            return f"계정 생성 실패: {str(e)}"

    @staticmethod
    def delete_user(username):
        """Windows 사용자 계정 삭제"""
        try:
            cmd = f'net user "{username}" /delete'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                return f"계정 삭제 실패: {result.stderr}"

            return f"계정 삭제 완료: {username}"
        except Exception as e:
            return f"계정 삭제 실패: {str(e)}"

    @staticmethod
    def change_password(username, new_password):
        """Windows 사용자 비밀번호 변경"""
        try:
            cmd = f'net user "{username}" "{new_password}"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                return f"비밀번호 변경 실패: {result.stderr}"

            return f"비밀번호 변경 완료: {username}"
        except Exception as e:
            return f"비밀번호 변경 실패: {str(e)}"

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
        elif cmd_type == 'create_user':
            return CommandExecutor.create_user(
                cmd_data.get('username'),
                cmd_data.get('password'),
                cmd_data.get('full_name'),
                cmd_data.get('comment')
            )
        elif cmd_type == 'delete_user':
            return CommandExecutor.delete_user(cmd_data.get('username'))
        elif cmd_type == 'change_password':
            return CommandExecutor.change_password(
                cmd_data.get('username'),
                cmd_data.get('new_password')
            )
        else:
            return f"알 수 없는 명령: {cmd_type}"
