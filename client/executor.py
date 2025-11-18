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
                return f"✅ 설치 완료: {app_name}\n{result.stdout}"
            else:
                return f"❌ 설치 실패: {app_name}\n반환 코드: {result.returncode}\n{result.stderr}"
        except subprocess.TimeoutExpired:
            return f"⏱️ 설치 타임아웃: {app_name} (5분 초과)"
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

            output = ""
            if result.stdout:
                output += result.stdout
            if result.stderr:
                output += f"\n[STDERR]\n{result.stderr}"

            if result.returncode != 0:
                output = f"⚠️ 명령 실행 완료 (종료 코드: {result.returncode})\n{output}"
            else:
                output = f"✅ 명령 실행 성공\n{output}" if output else "✅ 명령 실행 성공 (출력 없음)"

            return output
        except subprocess.TimeoutExpired:
            return f"⏱️ 명령 실행 타임아웃 (30초 초과): {command}"
        except Exception as e:
            return f"실행 실패: {str(e)}"

    @staticmethod
    def download_file(file_url, save_path):
        """파일 다운로드"""
        try:
            import requests
            import os

            # 디렉토리 생성
            directory = os.path.dirname(save_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
                print(f"[*] 디렉토리 생성: {directory}")

            # 다운로드 시작
            print(f"[*] 다운로드 시작: {file_url}")
            response = requests.get(file_url, stream=True, timeout=60)
            response.raise_for_status()

            # 파일 크기 확인
            total_size = int(response.headers.get('content-length', 0))

            # 스트리밍 다운로드
            downloaded = 0
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

            # 파일 크기 확인
            actual_size = os.path.getsize(save_path)

            result = f"✅ 다운로드 완료: {save_path}\n"
            result += f"   파일 크기: {actual_size:,} bytes"
            if total_size > 0:
                result += f" ({actual_size/total_size*100:.1f}%)"

            return result
        except requests.exceptions.RequestException as e:
            return f"❌ 다운로드 실패 (네트워크 오류): {str(e)}"
        except Exception as e:
            return f"❌ 다운로드 실패: {str(e)}"

    @staticmethod
    def manage_account(action, username, password=None, full_name=None, comment=None):
        """Windows 계정 관리 통합 함수"""
        try:
            if action == 'create':
                # 계정 생성
                cmd = f'net user "{username}" "{password}" /add'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)

                if result.returncode != 0:
                    return f"❌ 계정 생성 실패: {result.stderr}"

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

                return f"✅ 계정 생성 완료: {username}"

            elif action == 'delete':
                # 계정 삭제
                cmd = f'net user "{username}" /delete'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)

                if result.returncode != 0:
                    return f"❌ 계정 삭제 실패: {result.stderr}"

                return f"✅ 계정 삭제 완료: {username}"

            elif action == 'change_password':
                # 비밀번호 변경
                cmd = f'net user "{username}" "{password}"'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)

                if result.returncode != 0:
                    return f"❌ 비밀번호 변경 실패: {result.stderr}"

                return f"✅ 비밀번호 변경 완료: {username}"

            else:
                return f"❌ 알 수 없는 계정 관리 작업: {action}"

        except Exception as e:
            return f"❌ 계정 관리 실패: {str(e)}"

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
                return f"❌ 알 수 없는 전원 관리 작업: {action}"

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
            return f"❌ 알 수 없는 명령 타입: {cmd_type}"
