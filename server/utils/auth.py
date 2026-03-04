"""
인증 및 권한 관리 유틸리티
"""
import bcrypt
from functools import wraps
from flask import session, jsonify, current_app
from typing import Callable


def hash_password(password: str) -> str:
    """
    비밀번호 해싱

    Args:
        password: 평문 비밀번호

    Returns:
        해시된 비밀번호 (문자열)
    """
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def check_password(password: str, hashed: str) -> bool:
    """
    비밀번호 확인

    Args:
        password: 평문 비밀번호
        hashed: 해시된 비밀번호

    Returns:
        일치 여부
    """
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


def require_admin(f: Callable) -> Callable:
    """
    관리자 권한 확인 데코레이터

    세션에 'admin' 키가 없으면 401 Unauthorized 반환

    Usage:
        @app.route('/api/admin/...')
        @require_admin
        def admin_function():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin'):
            return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

        # 세션의 관리자가 DB에 여전히 존재하는지 확인 (삭제/비활성화 즉시 차단)
        from utils.database import get_db
        username = session.get('username')
        db = get_db()
        admin = db.execute(
            'SELECT id FROM admins WHERE username=? AND is_active=1', (username,)
        ).fetchone()
        if not admin:
            session.clear()
            return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

        return f(*args, **kwargs)

    return decorated_function


def is_admin() -> bool:
    """
    현재 사용자가 관리자인지 확인

    Returns:
        관리자 여부
    """
    return session.get('admin', False)


def get_current_admin() -> str:
    """
    현재 로그인한 관리자 사용자명 반환

    Returns:
        관리자 사용자명 또는 None
    """
    return session.get('username')

