"""
등록 토큰 모델 (v0.8.0 PIN 인증)
PC 등록 시 사용하는 PIN 토큰 관리
"""
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from utils.database import get_db


class RegistrationTokenModel:
    """등록 토큰 관리 모델"""

    @staticmethod
    def create(created_by: str, usage_type: str = 'single',
               expires_in: int = 600) -> Dict[str, Any]:
        """등록 토큰 생성

        Args:
            created_by: 생성한 관리자 username
            usage_type: 'single' (1회용) 또는 'multi' (재사용 가능)
            expires_in: 만료 시간 (초, 기본값 600 = 10분)

        Returns:
            생성된 토큰 정보 딕셔너리
        """
        db = get_db()

        # 6자리 랜덤 PIN 생성 (중복 방지)
        max_retries = 10
        token = None

        for _ in range(max_retries):
            token = f"{random.randint(0, 999999):06d}"

            # 중복 확인
            existing = db.execute(
                'SELECT id FROM pc_registration_tokens WHERE token = ?',
                (token,)
            ).fetchone()

            if not existing:
                break
        else:
            raise ValueError("토큰 생성 실패: 중복 회피 불가")

        # 만료 시각 계산
        expires_at = datetime.now() + timedelta(seconds=expires_in)

        # DB에 저장
        cursor = db.execute('''
            INSERT INTO pc_registration_tokens 
            (token, usage_type, expires_in, created_by, expires_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (token, usage_type, expires_in, created_by, expires_at))

        db.commit()

        return {
            'id': cursor.lastrowid,
            'token': token,
            'usage_type': usage_type,
            'expires_in': expires_in,
            'created_by': created_by,
            'expires_at': expires_at.isoformat(),
            'used_count': 0,
            'is_expired': False
        }

    @staticmethod
    def validate(token: str) -> Tuple[bool, Optional[str]]:
        """토큰 검증 (유효성, 만료 여부)

        Args:
            token: 6자리 PIN

        Returns:
            (유효 여부, 에러 메시지) 튜플
        """
        db = get_db()

        row = db.execute('''
            SELECT * FROM pc_registration_tokens 
            WHERE token = ?
        ''', (token,)).fetchone()

        if not row:
            return (False, "Invalid PIN")

        token_data = dict(row)

        # 수동 만료 체크
        if token_data['is_expired']:
            return (False, "PIN has been manually expired")

        # 시간 만료 체크
        expires_at = token_data['expires_at']
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)

        if datetime.now() > expires_at:
            return (False, "PIN expired")

        # 1회용 토큰 재사용 체크
        if token_data['usage_type'] == 'single' and token_data['used_count'] > 0:
            return (False, "PIN already used (single-use token)")

        return (True, None)

    @staticmethod
    def mark_used(token: str) -> bool:
        """토큰 사용 처리 (used_count 증가)

        Args:
            token: 6자리 PIN

        Returns:
            성공 여부
        """
        db = get_db()

        try:
            cursor = db.execute('''
                UPDATE pc_registration_tokens 
                SET used_count = used_count + 1
                WHERE token = ?
            ''', (token,))
            db.commit()

            return cursor.rowcount > 0
        except Exception:
            db.rollback()
            return False

    @staticmethod
    def get_active_tokens(created_by: Optional[str] = None) -> List[Dict[str, Any]]:
        """활성 토큰 목록 조회

        Args:
            created_by: 관리자 username (None이면 모든 토큰)

        Returns:
            토큰 정보 딕셔너리 리스트
        """
        db = get_db()

        # 만료되지 않은 토큰만 조회
        if created_by:
            rows = db.execute('''
                SELECT * FROM pc_registration_tokens
                WHERE created_by = ? 
                  AND is_expired = 0 
                  AND datetime(expires_at) > datetime('now')
                ORDER BY created_at DESC
            ''', (created_by,)).fetchall()
        else:
            rows = db.execute('''
                SELECT * FROM pc_registration_tokens
                WHERE is_expired = 0 
                  AND datetime(expires_at) > datetime('now')
                ORDER BY created_at DESC
            ''').fetchall()

        return [dict(row) for row in rows]

    @staticmethod
    def get_all_tokens(created_by: Optional[str] = None) -> List[Dict[str, Any]]:
        """모든 토큰 목록 조회 (만료된 것 포함)

        Args:
            created_by: 관리자 username (None이면 모든 토큰)

        Returns:
            토큰 정보 딕셔너리 리스트
        """
        db = get_db()

        if created_by:
            rows = db.execute('''
                SELECT * FROM pc_registration_tokens
                WHERE created_by = ?
                ORDER BY created_at DESC
            ''', (created_by,)).fetchall()
        else:
            rows = db.execute('''
                SELECT * FROM pc_registration_tokens
                ORDER BY created_at DESC
            ''').fetchall()

        return [dict(row) for row in rows]

    @staticmethod
    def expire_token(token: str) -> bool:
        """토큰 수동 만료

        Args:
            token: 6자리 PIN

        Returns:
            성공 여부
        """
        db = get_db()

        try:
            cursor = db.execute('''
                UPDATE pc_registration_tokens 
                SET is_expired = 1
                WHERE token = ?
            ''', (token,))
            db.commit()

            return cursor.rowcount > 0
        except Exception:
            db.rollback()
            return False

    @staticmethod
    def cleanup_expired() -> int:
        """만료된 토큰 자동 정리 (24시간 이상 지난 것만)

        Returns:
            삭제된 토큰 개수
        """
        db = get_db()

        try:
            cursor = db.execute('''
                DELETE FROM pc_registration_tokens
                WHERE datetime(expires_at) < datetime('now', '-1 day')
            ''')
            db.commit()

            return cursor.rowcount
        except Exception:
            db.rollback()
            return 0

    @staticmethod
    def get_by_token(token: str) -> Optional[Dict[str, Any]]:
        """토큰으로 조회

        Args:
            token: 6자리 PIN

        Returns:
            토큰 정보 딕셔너리 또는 None
        """
        db = get_db()

        row = db.execute('''
            SELECT * FROM pc_registration_tokens
            WHERE token = ?
        ''', (token,)).fetchone()

        return dict(row) if row else None
