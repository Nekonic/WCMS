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

def init_db():
    """데이터베이스 초기화"""
    print_step("데이터베이스 초기화 중...")
    
    db_path = os.path.join("server", "db.sqlite3")
    schema_path = os.path.join("server", "migrations", "schema.sql")
    
    if os.path.exists(db_path):
        response = input(f"기존 데이터베이스({db_path})를 삭제하고 재설정하시겠습니까? (y/n): ")
        if response.lower() == 'y':
            os.remove(db_path)
            print(f"기존 {db_path} 삭제됨.")
        else:
            print("초기화 취소.")
            return

    # 스키마 적용
    if not os.path.exists(schema_path):
        print(f"오류: 스키마 파일({schema_path})을 찾을 수 없습니다.")
        return

    import sqlite3
    
    try:
        conn = sqlite3.connect(db_path)
        with open(schema_path, 'r') as f:
            schema = f.read()
        conn.executescript(schema)
        conn.close()
        print(f"[✓] {schema_path} 적용 완료.")
    except Exception as e:
        print(f"오류: DB 생성 실패 - {e}")
        return

    # 관리자 생성
    print_step("관리자 계정 생성 중 (기본값: admin / admin)...")
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.join(os.getcwd(), "server")
    
    try:
        # uv run을 통해 create_admin.py 실행 (의존성 문제 해결)
        subprocess.run(["uv", "run", "--project", "server", "python", "server/create_admin.py"], env=env, check=True)
    except subprocess.CalledProcessError:
        print("[!] 관리자 계정 생성 스크립트 실행 실패.")
        print("    'python manage.py install'을 실행하여 의존성을 먼저 설치해주세요.")
        return

    # 관리자 생성 확인
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) FROM admins")
        count = cursor.fetchone()[0]
        conn.close()
        if count > 0:
            print(f"[✓] 관리자 계정 생성 확인됨 (총 {count}명).")
        else:
            print("[!] 경고: 관리자 계정이 DB에 생성되지 않았습니다.")
    except Exception as e:
        print(f"[!] 관리자 계정 확인 중 오류: {e}")

    # 좌석 생성
    print_step("좌석 배치 생성 중...")
    try:
        subprocess.run(["uv", "run", "--project", "server", "python", "server/create_seats.py"], env=env, check=True)
    except subprocess.CalledProcessError:
        print("[!] 좌석 배치 생성 실패.")

    print("\n 초기화 완료.")
    print("    관리자 ID: admin")
    print("    비밀번호 : admin")

def run_server(host="0.0.0.0", port=5050, mode="development", use_gunicorn=False):
    """서버 실행"""
    print_step(f"서버 시작 ({mode} 모드)...")
    
    env = os.environ.copy()
    env["FLASK_ENV"] = mode
    # PYTHONPATH에 server 디렉토리 추가
    env["PYTHONPATH"] = os.path.join(os.getcwd(), "server")
    
    if use_gunicorn:
        print_step("Gunicorn으로 서버 실행 중...")
        # Gunicorn 실행 명령
        # -k gevent: 비동기 워커 사용 (SocketIO 지원)
        # -w 1: 워커 수 (SocketIO 사용 시 1개 권장, 여러 개 사용 시 Redis 등 메시지 큐 필요)
        # --worker-connections 1000: 동시 접속 수
        # -b host:port: 바인딩 주소
        cmd = [
            "uv", "run", "--project", "server", "gunicorn",
            "-k", "gevent",
            "-w", "1", 
            "--worker-connections", "1000",
            "-b", f"{host}:{port}",
            "server.app:app"
        ]
    else:
        cmd = ["uv", "run", "--project", "server", "python", "server/app.py"]
    
    print(f"접속 주소: http://{host}:{port}")
    try:
        subprocess.run(cmd, env=env, check=True)
    except KeyboardInterrupt:
        print("\n서버가 종료되었습니다.")

def run_tests(target="all"):
    """테스트 실행"""
    
    if target == "archive":
        print_step("아카이브 서버 테스트 실행 (app.py 검증)...")
        env = os.environ.copy()
        # PYTHONPATH에 archive/code 디렉토리 추가
        env["PYTHONPATH"] = os.path.join(os.getcwd(), "archive", "code")
        
        try:
            # archive/code/test_server.py 실행
            subprocess.run(["uv", "run", "--project", "server", "python", "archive/code/test_server.py"], env=env, check=True)
        except subprocess.CalledProcessError:
            print("아카이브 서버 테스트 실패")
            sys.exit(1)
        return

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

def build_client():
    """클라이언트 EXE 빌드"""
    if platform.system() != "Windows":
        print_step("오류: 클라이언트 빌드는 Windows 환경에서만 가능합니다.")
        return

    print_step("클라이언트 EXE 빌드 시작...")
    
    # PyInstaller 설치 확인
    try:
        subprocess.run(["uv", "run", "--project", "client", "pyinstaller", "--version"], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        print("PyInstaller가 설치되어 있지 않습니다. 설치를 시도합니다...")
        subprocess.run(["uv", "add", "--project", "client", "pyinstaller"], check=True)

    # 빌드 실행
    try:
        # client 디렉토리로 이동하여 빌드 수행 (경로 문제 방지)
        cwd = os.getcwd()
        os.chdir("client")
        
        cmd = ["uv", "run", "pyinstaller", "--clean", "--noconfirm", "build.spec"]
        subprocess.run(cmd, check=True)
        
        os.chdir(cwd)
        
        dist_path = os.path.join("client", "dist", "WCMS-Client.exe")
        if os.path.exists(dist_path):
            print_step(f"빌드 성공! 파일 위치: {dist_path}")
        else:
            print_step("빌드 완료되었으나 결과 파일을 찾을 수 없습니다.")
            
    except subprocess.CalledProcessError as e:
        print(f"빌드 실패: {e}")
        os.chdir(cwd) # 에러 발생 시에도 원래 디렉토리로 복귀

def main():
    if len(sys.argv) < 2:
        command = "run"
    else:
        command = sys.argv[1]

    check_uv()
    
    if command == "install":
        install_dependencies()
    elif command == "init-db":
        init_db()
    elif command == "run":
        # 옵션 파싱 (간단하게)
        use_gunicorn = "--prod" in sys.argv
        mode = "production" if use_gunicorn else "development"
        run_server(mode=mode, use_gunicorn=use_gunicorn)
    elif command == "test":
        target = sys.argv[2] if len(sys.argv) > 2 else "all"
        run_tests(target)
    elif command == "build":
        build_client()
    elif command == "help":
        print("사용법: python manage.py [command] [options]")
        print("Commands:")
        print("  run           : 서버 실행 (기본값)")
        print("    --prod      : Gunicorn으로 프로덕션 모드 실행")
        print("  test [target] : 테스트 실행 (target: all, server, client, archive)")
        print("  init-db       : 데이터베이스 초기화")
        print("  install       : 의존성 설치")
        print("  build         : 클라이언트 EXE 빌드 (Windows 전용)")
    else:
        print(f"알 수 없는 명령: {command}")
        print("사용 가능한 명령: run, test, init-db, install, build")

if __name__ == "__main__":
    main()
