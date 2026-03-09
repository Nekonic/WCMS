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


def get_client_version() -> str:
    """클라이언트 최신 버전 반환.
    1순위: git 태그 (client-v*) 중 가장 높은 버전
    2순위: client/VERSION 파일
    """
    try:
        result = subprocess.run(
            ['git', 'tag', '--list', 'client-v*', '--sort=-version:refname'],
            capture_output=True, text=True
        )
        tags = [t.strip() for t in result.stdout.splitlines() if t.strip().startswith('client-v')]
        if tags:
            return tags[0].replace('client-v', '')
    except Exception:
        pass

    version_file = 'VERSION'
    try:
        with open(version_file, encoding='utf-8') as f:
            return f.readline().strip()
    except Exception:
        pass

    return '0.0.0'

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

def init_db(force=False, username='admin', password='admin'):
    """데이터베이스 초기화 (npm run db:init 호출)

    Args:
        force: True면 기존 DB를 묻지 않고 삭제
        username: 관리자 계정 이름
        password: 관리자 비밀번호
    """
    print_step("데이터베이스 초기화 중...")

    db_path = os.getenv('WCMS_DB_PATH', os.path.join("db", "wcms.sqlite3"))

    if os.path.exists(db_path):
        if force:
            os.remove(db_path)
            print(f"기존 {db_path} 삭제됨.")
        else:
            response = input(f"기존 데이터베이스({db_path})를 삭제하고 재설정하시겠습니까? (y/n): ")
            if response.lower() == 'y':
                os.remove(db_path)
                print(f"기존 {db_path} 삭제됨.")
            else:
                print("초기화 취소.")
                return

    # DB 디렉토리 생성
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        print(f"DB 디렉토리 생성: {db_dir}")

    env = os.environ.copy()
    if db_path:
        env["WCMS_DB_PATH"] = os.path.abspath(db_path)

    try:
        subprocess.run(
            ["npm", "run", "db:init", "--", username, password],
            cwd="api",
            env=env,
            check=True
        )
    except subprocess.CalledProcessError:
        print("[!] DB 초기화 실패.")
        sys.exit(1)

    print("\n초기화 완료.")
    print(f"    관리자 ID: {username}")
    print(f"    비밀번호 : {password}")

def migrate_db(migration_file=None):
    """데이터베이스 마이그레이션 실행

    Args:
        migration_file: 실행할 마이그레이션 파일명 (None이면 모든 마이그레이션 실행)
    """
    print_step("데이터베이스 마이그레이션 중...")

    import sqlite3

    db_path = os.getenv('WCMS_DB_PATH', os.path.join("db", "wcms.sqlite3"))
    migrations_dir = os.path.join("server", "migrations")

    if not os.path.exists(db_path):
        print(f"오류: 데이터베이스({db_path})가 존재하지 않습니다.")
        print("먼저 'python manage.py init-db'를 실행하세요.")
        return

    # 마이그레이션 파일 목록
    if migration_file:
        migration_files = [migration_file]
    else:
        # 모든 .sql 파일 중 숫자로 시작하는 파일만 (schema.sql 제외)
        all_files = os.listdir(migrations_dir)
        migration_files = sorted([f for f in all_files if f.endswith('.sql') and f[0].isdigit()])

    if not migration_files:
        print("실행할 마이그레이션이 없습니다.")
        return

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        # 마이그레이션 히스토리 테이블 생성 (없으면)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS migration_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                migration_file TEXT UNIQUE NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()

        # 이미 적용된 마이그레이션 확인
        applied = set(row['migration_file'] for row in
                     conn.execute('SELECT migration_file FROM migration_history').fetchall())

        # 마이그레이션 실행
        for filename in migration_files:
            if filename in applied:
                print(f"⏭️  {filename} - 이미 적용됨")
                continue

            filepath = os.path.join(migrations_dir, filename)
            if not os.path.exists(filepath):
                print(f"⚠️  {filename} - 파일 없음")
                continue

            print(f"📝 {filename} 실행 중...")

            with open(filepath, 'r', encoding='utf-8') as f:
                migration_sql = f.read()

            try:
                conn.executescript(migration_sql)
                conn.execute('INSERT INTO migration_history (migration_file) VALUES (?)', (filename,))
                conn.commit()
                print(f"✅ {filename} - 완료")
            except sqlite3.Error as e:
                print(f"❌ {filename} - 실패: {e}")
                conn.rollback()
                raise

        conn.close()
        print_step("마이그레이션 완료!")

    except Exception as e:
        print(f"오류: {e}")
        sys.exit(1)

def _ensure_frontend(prod=False):
    """프론트엔드 의존성 설치 및 빌드 확인"""
    frontend_dir = os.path.join(os.getcwd(), "frontend")
    if not os.path.exists(frontend_dir):
        return

    node_modules = os.path.join(frontend_dir, "node_modules")
    if not os.path.exists(node_modules):
        print_step("프론트엔드 의존성 설치 중 (npm install)...")
        subprocess.run(["npm", "install"], cwd=frontend_dir, check=True)

    if prod:
        print_step("프론트엔드 빌드 중 (npm run build)...")
        subprocess.run(["npm", "run", "build"], cwd=frontend_dir, check=True)

def run_server(prod=False):
    """API 서버 실행 (Hono, api/ 디렉토리)"""
    _ensure_frontend(prod=prod)

    if prod:
        print_step("API 서버 시작 (프로덕션)...")
        cmd = ["npm", "start"]
    else:
        print_step("API 서버 시작 (개발)...")
        # Vite 개발 서버를 백그라운드로 실행
        frontend_dir = os.path.join(os.getcwd(), "frontend")
        if os.path.exists(frontend_dir):
            print_step("프론트엔드 개발 서버 시작 중 (Vite :5173)...")
            subprocess.Popen(["npm", "run", "dev"], cwd=frontend_dir)
        cmd = ["npm", "run", "dev"]

    print("접속 주소: http://0.0.0.0:5050")
    if not prod:
        print("프론트엔드: http://localhost:5173 (Vite dev server)")
    try:
        subprocess.run(cmd, cwd="api", check=True)
    except KeyboardInterrupt:
        print("\n서버가 종료되었습니다.")

def run_tests(target="all"):
    """테스트 실행 (uv run 사용)"""

    if target == "archive":
        print_step("아카이브 서버 테스트 실행 (app.py 검증)...")
        env = os.environ.copy()
        env["PYTHONPATH"] = os.path.join(os.getcwd(), "archive", "code")

        try:
            subprocess.run(["uv", "run", "python", "archive/code/test_server.py"], env=env, check=True)
        except subprocess.CalledProcessError:
            print("아카이브 서버 테스트 실패")
            sys.exit(1)
        return

    if target in ["all", "api"]:
        print_step("API 서버 테스트 실행 (vitest)...")
        try:
            subprocess.run(["npm", "test"], cwd="api", check=True)
        except subprocess.CalledProcessError:
            print("API 테스트 실패")
            if target == "api":
                sys.exit(1)

    if target in ["all", "server"]:
        print_step("서버 테스트 실행...")

        try:
            subprocess.run(["uv", "run", "python", "-m", "pytest", "tests/server", "-v", "--tb=short"], check=True)
        except subprocess.CalledProcessError:
            print("서버 테스트 실패")
            if target == "server":
                sys.exit(1)

    if target in ["all", "client"]:
        if platform.system() != "Windows":
            print_step("클라이언트 테스트 건너뛰기 (Windows 전용)")
            return

        print_step("클라이언트 테스트 실행...")

        try:
            subprocess.run(["uv", "run", "python", "-m", "pytest", "tests/client", "-v", "--tb=short"], check=True)
        except subprocess.CalledProcessError:
            print("클라이언트 테스트 실패")
            if target == "client":
                sys.exit(1)

def run_docker_test(skip_setup: bool = False):
    """Docker Compose 기반 통합 테스트 실행"""
    venv_python = os.path.join(os.getcwd(), ".venv", "Scripts", "python.exe") if platform.system() == "Windows" else os.path.join(os.getcwd(), ".venv", "bin", "python")

    print_step("Docker Compose 통합 테스트 실행")

    # 새 테스트 스크립트 실행 (Docker Compose 기반)
    cmd = [venv_python, "tests/docker_test.py"]

    # 추가 옵션 전달
    if "--rebuild" in sys.argv or "-r" in sys.argv:
        cmd.append("--rebuild")
    if "--no-cache" in sys.argv or "-n" in sys.argv:
        cmd.append("--no-cache")
    if "--cleanup" in sys.argv or "-c" in sys.argv:
        cmd.append("--cleanup")
    if "--skip-boot" in sys.argv or "-s" in sys.argv:
        cmd.append("--skip-boot")

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        print("Docker 통합 테스트 실패")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n테스트 중단됨")

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
    cwd = os.getcwd()
    try:
        # client 디렉토리로 이동하여 빌드 수행 (경로 문제 방지)
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
        os.chdir(cwd)
    except Exception as e:
        print(f"예상치 못한 오류: {e}")
        os.chdir(cwd)

def main():
    if len(sys.argv) < 2:
        command = "run"
    else:
        command = sys.argv[1]

    # uv는 Python 의존성 명령에서만 필요
    uv_commands = {"install", "docker-test", "build"}
    uv_test_targets = {"server", "client", "all"}
    needs_uv = command in uv_commands or (
        command == "test" and (len(sys.argv) < 3 or sys.argv[2] in uv_test_targets)
    )
    if needs_uv:
        check_uv()

    args = sys.argv[2:]

    if command == "install":
        install_dependencies()
    elif command == "init-db":
        force = "--force" in args or "-f" in args
        pos_args = [a for a in args if not a.startswith('-')]
        username = pos_args[0] if len(pos_args) > 0 else 'admin'
        password = pos_args[1] if len(pos_args) > 1 else 'admin'
        init_db(force=force, username=username, password=password)
    elif command == "migrate":
        migration_file = args[0] if args else None
        migrate_db(migration_file)
    elif command == "run":
        run_server(prod="--prod" in args or "-p" in args)
    elif command == "test":
        target = sys.argv[2] if len(sys.argv) > 2 else "all"
        run_tests(target)
    elif command == "docker-test":
        run_docker_test()
    elif command == "build":
        build_client()
    elif command == "help":
        print("사용법: python3 manage.py [command] [options]")
        print("Commands:")
        print("  run                    : API 서버 + 프론트엔드 개발 서버 실행")
        print("    --prod,    -p        : 프론트엔드 빌드 후 프로덕션 모드 실행")
        print("  test [target]          : 테스트 실행 (target: all, api, server, client, archive)")
        print("  docker-test            : Docker Compose 통합 테스트 (dockurr/windows + VNC)")
        print("    --rebuild, -r        : 서버 이미지 강제 재빌드")
        print("    --no-cache,-n        : Docker 빌드 캐시 사용 안 함")
        print("    --cleanup, -c        : 테스트 후 컨테이너 정리")
        print("    --skip-boot,-s       : Windows 부팅 대기 스킵")
        print("  init-db [id] [pw]      : 데이터베이스 초기화 (기본값: admin / admin)")
        print("    --force,   -f        : 기존 DB를 묻지 않고 삭제 후 재초기화")
        print("  migrate [file]         : 마이그레이션 실행 (file 생략 시 모든 마이그레이션)")
        print("  install                : 의존성 설치")
        print("  build                  : 클라이언트 EXE 빌드 (Windows 전용)")
    else:
        print(f"알 수 없는 명령: {command}")
        print("사용 가능한 명령: run, test, docker-test, init-db, migrate, install, build")

if __name__ == "__main__":
    main()
