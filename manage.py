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
    print_step("서버 의존성 동기화 중 (uv sync)...")
    subprocess.run(["uv", "sync", "--project", "server"], check=True)
    
    if platform.system() == "Windows":
        print_step("클라이언트 의존성 동기화 중 (uv sync)...")
        subprocess.run(["uv", "sync", "--project", "client"], check=True)
    else:
        print_step("클라이언트 의존성 설치 건너뛰기 (Windows 전용)")

def run_server(host="0.0.0.0", port=5050, mode="development"):
    """서버 실행"""
    print_step(f"서버 시작 ({mode} 모드)...")
    
    env = os.environ.copy()
    env["FLASK_ENV"] = mode
    # PYTHONPATH에 server 디렉토리 추가
    env["PYTHONPATH"] = os.path.join(os.getcwd(), "server")
    
    cmd = ["uv", "run", "--project", "server", "python", "server/app.py"]
    
    print(f"접속 주소: http://{host}:{port}")
    try:
        subprocess.run(cmd, env=env, check=True)
    except KeyboardInterrupt:
        print("\n서버가 종료되었습니다.")

def run_tests(target="all"):
    """테스트 실행"""
    
    if target in ["all", "server"]:
        print_step("서버 테스트 실행...")
        env = os.environ.copy()
        # PYTHONPATH에 server 디렉토리 추가
        env["PYTHONPATH"] = os.path.join(os.getcwd(), "server")
        
        try:
            subprocess.run(["uv", "run", "--project", "server", "pytest", "tests/server"], env=env, check=True)
        except subprocess.CalledProcessError:
            print("서버 테스트 실패")
            if target == "server":
                sys.exit(1)

    if target in ["all", "client"]:
        if platform.system() != "Windows":
            print_step("클라이언트 테스트 건너뛰기 (Windows 전용)")
            return
            
        print_step("클라이언트 테스트 실행...")
        env = os.environ.copy()
        env["PYTHONPATH"] = os.path.join(os.getcwd(), "client")
        
        try:
            subprocess.run(["uv", "run", "--project", "client", "pytest", "tests/client"], env=env, check=True)
        except subprocess.CalledProcessError:
            print("클라이언트 테스트 실패")
            if target == "client":
                sys.exit(1)

def main():
    if len(sys.argv) < 2:
        command = "run"
    else:
        command = sys.argv[1]

    check_uv()
    
    if command == "install":
        install_dependencies()
    elif command == "run":
        run_server()
    elif command == "test":
        target = sys.argv[2] if len(sys.argv) > 2 else "all"
        run_tests(target)
    elif command == "help":
        print("사용법: python manage.py [command]")
        print("Commands:")
        print("  run           : 서버 실행 (기본값)")
        print("  test [target] : 테스트 실행 (target: all, server, client)")
        print("  install       : 의존성 설치")
    else:
        print(f"알 수 없는 명령: {command}")
        print("사용 가능한 명령: run, test, install")

if __name__ == "__main__":
    main()
