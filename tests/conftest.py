"""
Pytest 설정 및 공통 픽스처
"""
import sys
import os
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from flask import Flask


@pytest.fixture
def app():
    """Flask 앱 테스트용 픽스처"""
    # server.app에서 앱 임포트
    from server.app import create_app

    app = create_app('test')  # 'test' 환경 설정 사용

    with app.app_context():
        yield app


@pytest.fixture
def client(app):
    """Flask 테스트 클라이언트"""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Flask CLI 테스트 러너"""
    return app.test_cli_runner()


@pytest.fixture(autouse=True)
def reset_db(app):
    """각 테스트 전후로 DB 초기화"""
    from server.utils import get_db, init_db_manager
    
    # 테스트 환경에서는 인메모리 DB 사용
    # app.config['DB_PATH']는 'test' 환경 설정에 의해 ':memory:'로 설정됨
    
    with app.app_context():
        # DB 매니저 초기화 (이미 되어 있을 수 있지만 확실하게)
        init_db_manager(app.config['DB_PATH'])
        
        db = get_db()
        
        # 스키마 로드 및 실행
        schema_path = project_root / 'server' / 'migrations' / 'schema.sql'
        if schema_path.exists():
            with open(schema_path, 'r', encoding='utf-8') as f:
                db.executescript(f.read())
        else:
            # 스키마 파일이 없으면 기본 테이블 생성 (테스트용)
            db.executescript("""
                CREATE TABLE IF NOT EXISTS pc_info (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    machine_id TEXT UNIQUE NOT NULL,
                    hostname TEXT,
                    ip_address TEXT,
                    mac_address TEXT,
                    room_name TEXT,
                    seat_number TEXT,
                    is_online INTEGER DEFAULT 0,
                    last_seen TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS pc_specs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pc_id INTEGER NOT NULL,
                    cpu_model TEXT,
                    cpu_cores INTEGER,
                    cpu_threads INTEGER,
                    ram_total REAL,
                    disk_info TEXT,
                    os_edition TEXT,
                    os_version TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (pc_id) REFERENCES pc_info (id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS pc_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pc_id INTEGER NOT NULL,
                    cpu_usage REAL,
                    ram_used REAL,
                    ram_usage_percent REAL,
                    disk_usage TEXT,
                    current_user TEXT,
                    uptime INTEGER,
                    processes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (pc_id) REFERENCES pc_info (id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS pc_command (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pc_id INTEGER NOT NULL,
                    admin_username TEXT,
                    command_type TEXT NOT NULL,
                    command_data TEXT,
                    priority INTEGER DEFAULT 5,
                    status TEXT DEFAULT 'pending',
                    result TEXT,
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    timeout_seconds INTEGER DEFAULT 300,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (pc_id) REFERENCES pc_info (id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS admins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    email TEXT,
                    is_active INTEGER DEFAULT 1,
                    last_login TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS seat_layout (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    room_name TEXT UNIQUE NOT NULL,
                    rows INTEGER NOT NULL,
                    cols INTEGER NOT NULL,
                    description TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS seat_map (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    room_name TEXT NOT NULL,
                    row INTEGER NOT NULL,
                    col INTEGER NOT NULL,
                    pc_id INTEGER,
                    FOREIGN KEY (room_name) REFERENCES seat_layout (room_name) ON DELETE CASCADE,
                    FOREIGN KEY (pc_id) REFERENCES pc_info (id) ON DELETE SET NULL
                );
                CREATE TABLE IF NOT EXISTS client_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version VARCHAR(50) NOT NULL UNIQUE,
                    download_url TEXT NOT NULL,
                    changelog TEXT,
                    released_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
        
        db.commit()
        
        yield

        # 테스트 후 정리 (인메모리 DB는 연결 닫으면 사라짐)
        db.close()
