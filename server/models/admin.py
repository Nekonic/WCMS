"""
관리자 모델 (Repository 패턴)
관리자 사용자 관련 데이터베이스 작업을 캡슐화
"""
from typing import Optional, Dict, Any
from utils import get_db, hash_password, check_password


class AdminModel:
    """관리자 사용자 관리 모델"""

    @staticmethod
    def get_by_id(admin_id: int) -> Optional[Dict[str, Any]]:
        """관리자 ID로 조회"""
        db = get_db()
        row = db.execute(
            'SELECT * FROM admins WHERE id=?',
            (admin_id,)
        ).fetchone()
        if row:
            result = dict(row)
            # 비밀번호 해시는 반환하지 않음
            result.pop('password_hash', None)
            return result
        return None

    @staticmethod
    def get_by_username(username: str) -> Optional[Dict[str, Any]]:
        """사용자명으로 조회 (로그인용, 해시 포함)"""
        db = get_db()
        row = db.execute(
            'SELECT * FROM admins WHERE username=?',
            (username,)
        ).fetchone()
        return dict(row) if row else None

    @staticmethod
    def authenticate(username: str, password: str) -> Optional[Dict[str, Any]]:
        """인증 (사용자명과 비밀번호 확인)"""
        admin = AdminModel.get_by_username(username)
        if not admin:
            return None

        # 비밀번호 확인
        password_hash = admin.get('password_hash', '')
        if check_password(password, password_hash):
            # 인증 성공 - 비밀번호 해시 제거
            admin.pop('password_hash', None)
            return admin

        return None

    @staticmethod
    def create(username: str, password: str, email: Optional[str] = None) -> Optional[int]:
        """새로운 관리자 생성"""
        try:
            db = get_db()

            # 이미 존재하는지 확인
            existing = db.execute(
                'SELECT id FROM admins WHERE username=?',
                (username,)
            ).fetchone()

            if existing:
                return None  # 이미 존재

            # 비밀번호 해싱
            password_hash = hash_password(password)

            cursor = db.execute('''
                INSERT INTO admins (username, password_hash, email, is_active)
                VALUES (?, ?, ?, 1)
            ''', (username, password_hash, email))

            db.commit()
            return cursor.lastrowid
        except Exception:
            return None

    @staticmethod
    def update_password(admin_id: int, new_password: str) -> bool:
        """비밀번호 변경"""
        try:
            db = get_db()
            password_hash = hash_password(new_password)

            db.execute(
                'UPDATE admins SET password_hash=? WHERE id=?',
                (password_hash, admin_id)
            )
            db.commit()
            return True
        except Exception:
            return False

    @staticmethod
    def update_email(admin_id: int, email: str) -> bool:
        """이메일 변경"""
        try:
            db = get_db()
            db.execute(
                'UPDATE admins SET email=? WHERE id=?',
                (email, admin_id)
            )
            db.commit()
            return True
        except Exception:
            return False

    @staticmethod
    def set_active(admin_id: int, is_active: bool) -> bool:
        """관리자 활성/비활성 설정"""
        try:
            db = get_db()
            db.execute(
                'UPDATE admins SET is_active=? WHERE id=?',
                (1 if is_active else 0, admin_id)
            )
            db.commit()
            return True
        except Exception:
            return False

    @staticmethod
    def update_last_login(admin_id: int) -> bool:
        """마지막 로그인 시간 업데이트"""
        try:
            db = get_db()
            db.execute(
                'UPDATE admins SET last_login=CURRENT_TIMESTAMP WHERE id=?',
                (admin_id,)
            )
            db.commit()
            return True
        except Exception:
            return False

    @staticmethod
    def get_all() -> list:
        """모든 관리자 조회"""
        db = get_db()
        rows = db.execute('SELECT id, username, email, is_active, created_at FROM admins').fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def get_active_count() -> int:
        """활성 관리자 수 조회"""
        db = get_db()
        result = db.execute(
            'SELECT COUNT(*) as count FROM admins WHERE is_active=1'
        ).fetchone()
        return result['count'] if result else 0

    @staticmethod
    def delete(admin_id: int) -> bool:
        """관리자 삭제"""
        try:
            db = get_db()
            db.execute(
                'DELETE FROM admins WHERE id=?',
                (admin_id,)
            )
            db.commit()
            return True
        except Exception:
            return False

    @staticmethod
    def check_username_exists(username: str) -> bool:
        """사용자명 존재 여부 확인"""
        db = get_db()
        row = db.execute(
            'SELECT id FROM admins WHERE username=?',
            (username,)
        ).fetchone()
        return row is not None
