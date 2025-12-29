"""
Pytest 설정 및 공통 픽스처
"""
import sys
import os
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'server'))
sys.path.insert(0, str(project_root / 'client'))

import pytest
from flask import Flask


@pytest.fixture
def app():
    """Flask 앱 테스트용 픽스처"""
    # app.py에서 앱 임포트
    sys.path.insert(0, str(project_root / 'server'))
    from app import create_app

    app = create_app('testing')

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
    from utils import get_db

    with app.app_context():
        db = get_db()

        # 테스트용 테이블 생성 (필요시)
        yield

        # 테스트 후 정리
        db.close()

