"""
Pytest 설정 및 공통 픽스처
"""
import sys
import os
from pathlib import Path

# 프로젝트 루트
project_root = Path(__file__).parent.parent

# server와 client 디렉토리를 sys.path에 추가
# server 테스트: server를 우선 추가
# client 테스트: client를 우선 추가
server_dir = str(project_root / "server")
client_dir = str(project_root / "client")

# 항상 server를 먼저 추가 (공통 설정)
if server_dir not in sys.path:
    sys.path.insert(0, server_dir)

# client는 나중에 추가하되, client 테스트에서만 우선순위를 높임
def pytest_configure(config):
    """pytest 설정 초기화"""
    # 테스트 경로에 따라 sys.path 조정
    test_paths = [str(p) for p in config.args if p]
    is_client_test = any('client' in p for p in test_paths)

    if is_client_test and client_dir not in sys.path:
        # 클라이언트 테스트일 때는 client를 앞에 추가
        sys.path.insert(0, client_dir)
    elif client_dir not in sys.path:
        # 서버 테스트일 때는 client를 뒤에 추가
        sys.path.append(client_dir)

import pytest

# Flask는 서버 테스트에서만 필요함
try:
    from flask import Flask
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False


@pytest.fixture
def app():
    """Flask 앱 테스트용 픽스처 (서버 테스트용)

    실제 서버 실행(python manage.py run)과 동일하게 설정:
    - schema.sql로 DB 생성
    - 기본 관리자 계정 생성 (admin/admin)
    - 클라이언트 버전 데이터 삽입
    """
    if not HAS_FLASK:
        pytest.skip("Flask not installed")

    # server.app에서 앱 임포트
    from app import create_app
    import bcrypt

    app = create_app('test')  # 'test' 환경 설정 사용

    with app.app_context():
        # DB 초기화 (schema.sql 로드)
        from utils.database import get_db, init_db_manager

        init_db_manager(app.config['DB_PATH'])
        db = get_db()

        # schema.sql 파일 사용
        schema_path = project_root / 'server' / 'migrations' / 'schema.sql'
        if schema_path.exists():
            with open(schema_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()
                db.executescript(sql_content)
                db.commit()

        # 기본 관리자 계정 생성 (실제 서버와 동일)
        password_hash = bcrypt.hashpw('admin'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        db.execute('''
            INSERT INTO admins (username, password_hash, email, is_active)
            VALUES (?, ?, ?, ?)
        ''', ('admin', password_hash, 'admin@wcms.local', 1))
        db.commit()

        # 클라이언트 버전 데이터 삽입 (실제 서버와 동일)
        db.execute('''
            INSERT INTO client_versions (version, download_url, changelog)
            VALUES (?, ?, ?)
        ''', (
            '0.7.0',
            'https://github.com/Nekonic/WCMS/releases/download/client-v0.7.0/WCMS-Client.exe',
            '자동 빌드 - v0.7.0 릴리스'
        ))
        db.commit()

        yield app


@pytest.fixture
def client(app):
    """Flask 테스트 클라이언트"""
    return app.test_client()


@pytest.fixture
def admin_session(client, app):
    """관리자 세션 (로그인된 상태)"""
    with client.session_transaction() as sess:
        sess['admin'] = True
        sess['username'] = 'admin'
    return client


@pytest.fixture
def test_pin(app):
    """테스트용 PIN 생성 (실제 RegistrationTokenModel.create와 동일)

    Returns:
        str: 6자리 PIN
    """
    from models.registration import RegistrationTokenModel

    # 실제 모델을 사용하여 토큰 생성
    token = RegistrationTokenModel.create(
        created_by='admin',
        usage_type='multi',
        expires_in=3600
    )

    return token['token']



@pytest.fixture
def registered_pc(client, app, test_pin):
    """등록된 PC (PIN 인증 완료)

    Returns:
        tuple: (pc_id, machine_id)
    """
    # PC 등록
    machine_id = 'TEST-FIXTURE-001'
    response = client.post('/api/client/register', json={
        'machine_id': machine_id,
        'pin': test_pin,
        'hostname': 'TEST-FIXTURE-PC',
        'mac_address': 'AA:BB:CC:DD:EE:99',
        'cpu_cores': 4,
        'ram_total': 16.0
    })

    pc_id = response.get_json()['pc_id']

    return (pc_id, machine_id)

@pytest.fixture
def runner(app):
    """Flask CLI 테스트 러너"""
    return app.test_cli_runner()
