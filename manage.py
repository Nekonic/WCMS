#!/usr/bin/env python3
"""
WCMS 통합 관리 스크립트
서버 실행, 테스트, 데이터베이스 초기화 등을 수행합니다.
"""
import os
import sys
import subprocess
import platform
import shutil

def print_step(message):
    print(f"\n\033[1;34m[WCMS] {message}\033[0m")

def check_uv():
    """uv 설치 확인 및 안내"""
    if shutil.which("uv") is None:
        print_step("uv가 설치되어 있지 않습니다.")
        print("uv는 Python 패키지 관리자입니다. 설치가 필요합니다.")
        
        system = platform.system()
        if system == "Darwin" or system == "Linux":
            print("설치 명령: curl -LsSf https://astral.sh/uv/install.sh | sh")
        elif system == "Windows":
            print('설치 명령: powershell -Command "irm https://astral.sh/uv/install.ps1 | iex"')
        
        response = input("지금 설치하시겠습니까? (y/n): ")
        if response.lower() == 'y':
            if system == "Darwin" or system == "Linux":
                os.system("curl -LsSf https://astral.sh/uv/install.sh | sh")
            elif system == "Windows":
                os.system('powershell -Command "irm https://astral.sh/uv/install.ps1 | iex"')
            
            # PATH 갱신을 위해 안내
            print("\n설치가 완료되었습니다. 터미널을 재시작하거나 PATH를 갱신해주세요.")
            sys.exit(0)
        else:
            print("uv 설치 후 다시 실행해주세요.")
            sys.exit(1)

def install_dependencies():
    """의존성 설치"""
    print_step("의존성 동기화 중 (uv sync)...")
    # 루트 pyproject.toml에는 의존성이 없으므로 server/pyproject.toml을 기준으로 설치해야 함
    # 하지만 uv는 작업 디렉토리의 pyproject.toml을 우선하므로, 
    # server 디렉토리의 의존성을 루트 가상환경에 설치하도록 유도해야 합니다.
    
    # 방법 1: server/pyproject.toml을 사용하여 동기화 (가상환경은 루트에 생성됨)
    # --project 옵션을 사용하여 server 디렉토리의 설정을 사용
    subprocess.run(["uv", "sync", "--project", "server"], check=True)

def run_server(host="0.0.0.0", port=5050, mode="development"):
    """서버 실행"""
    print_step(f"서버 시작 ({mode} 모드)...")
    
    env = os.environ.copy()
    env["FLASK_ENV"] = mode
    
    # uv run을 실행할 때도 --project server 옵션을 주어 server의 의존성을 사용하도록 함
    cmd = ["uv", "run", "--project", "server", "python", "server/app.py"]
    
    print(f"접속 주소: http://{host}:{port}")
    try:
        subprocess.run(cmd, env=env, check=True)
    except KeyboardInterrupt:
        print("\n서버가 종료되었습니다.")

def run_tests():
    """테스트 실행"""
    print_step("테스트 실행...")
    # 테스트 실행 시에도 server 프로젝트 컨텍스트 사용
    subprocess.run(["uv", "run", "--project", "server", "pytest"], check=True)

def main():
    if len(sys.argv) < 2:
        command = "run"
    else:
        command = sys.argv[1]

    check_uv()
    install_dependencies()

    if command == "run":
        run_server()
    elif command == "test":
        run_tests()
    elif command == "help":
        print("사용법: python manage.py [command]")
        print("Commands:")
        print("  run   : 서버 실행 (기본값)")
        print("  test  : 단위 테스트 실행")
    else:
        print(f"알 수 없는 명령: {command}")
        print("사용 가능한 명령: run, test")

if __name__ == "__main__":
    main()
