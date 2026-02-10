"""
등록 토큰 모델 테스트

RegistrationTokenModel의 모든 메서드를 테스트합니다.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'server'))

import pytest
from datetime import datetime, timedelta
from models.registration import RegistrationTokenModel


class TestRegistrationTokenModel:
    """등록 토큰 모델 테스트"""

    def test_create_token_single_use(self, app):
        """1회용 토큰 생성"""
        token = RegistrationTokenModel.create(
            created_by='admin',
            usage_type='single',
            expires_in=600
        )

        assert token is not None
        assert len(token['token']) == 6
        assert token['token'].isdigit()
        assert token['usage_type'] == 'single'
        assert token['expires_in'] == 600
        assert token['created_by'] == 'admin'
        assert token['used_count'] == 0
        assert token['is_expired'] is False

    def test_create_token_multi_use(self, app):
        """재사용 가능 토큰 생성"""
        token = RegistrationTokenModel.create(
            created_by='admin',
            usage_type='multi',
            expires_in=1800
        )

        assert token['usage_type'] == 'multi'
        assert token['expires_in'] == 1800

    def test_validate_token_valid(self, app):
        """유효한 토큰 검증"""
        token = RegistrationTokenModel.create(
            created_by='admin',
            usage_type='single',
            expires_in=600
        )

        is_valid, error_msg = RegistrationTokenModel.validate(token['token'])

        assert is_valid is True
        assert error_msg is None

    def test_validate_token_expired(self, app):
        """만료된 토큰 검증"""
        # 만료 시간을 과거로 설정
        from utils import get_db
        db = get_db()

        token_str = "123456"
        expires_at = datetime.now() - timedelta(seconds=10)

        db.execute('''
            INSERT INTO pc_registration_tokens 
            (token, usage_type, expires_in, created_by, expires_at)
            VALUES (?, 'single', 60, 'admin', ?)
        ''', (token_str, expires_at.isoformat()))

        is_valid, error_msg = RegistrationTokenModel.validate(token_str)

        assert is_valid is False
        assert "expired" in error_msg.lower()

    def test_validate_token_already_used(self, app):
        """1회용 토큰 재사용 시도"""
        token = RegistrationTokenModel.create(
            created_by='admin',
            usage_type='single',
            expires_in=600
        )

        # 첫 번째 사용
        RegistrationTokenModel.mark_used(token['token'])

        # 두 번째 사용 시도
        is_valid, error_msg = RegistrationTokenModel.validate(token['token'])

        assert is_valid is False
        assert "already used" in error_msg.lower()

    def test_validate_token_not_found(self, app):
        """존재하지 않는 토큰"""
        is_valid, error_msg = RegistrationTokenModel.validate("999999")

        assert is_valid is False
        assert "invalid" in error_msg.lower()

    def test_mark_used(self, app):
        """토큰 사용 처리"""
        token = RegistrationTokenModel.create(
            created_by='admin',
            usage_type='multi',
            expires_in=600
        )

        # 사용 처리
        success = RegistrationTokenModel.mark_used(token['token'])
        assert success is True

        # used_count 확인
        token_data = RegistrationTokenModel.get_by_token(token['token'])
        assert token_data['used_count'] == 1

        # 다시 사용 (multi)
        RegistrationTokenModel.mark_used(token['token'])
        token_data = RegistrationTokenModel.get_by_token(token['token'])
        assert token_data['used_count'] == 2

    def test_expire_token_manually(self, app):
        """토큰 수동 만료"""
        token = RegistrationTokenModel.create(
            created_by='admin',
            usage_type='single',
            expires_in=600
        )

        # 만료 처리
        success = RegistrationTokenModel.expire_token(token['token'])
        assert success is True

        # 검증 시 실패해야 함
        is_valid, error_msg = RegistrationTokenModel.validate(token['token'])
        assert is_valid is False
        assert "expired" in error_msg.lower()

    def test_get_active_tokens(self, app):
        """활성 토큰 목록 조회"""
        # 토큰 3개 생성
        token1 = RegistrationTokenModel.create('admin', 'single', 600)
        token2 = RegistrationTokenModel.create('admin', 'multi', 600)
        token3 = RegistrationTokenModel.create('user', 'single', 600)

        # 모든 활성 토큰
        tokens = RegistrationTokenModel.get_active_tokens()
        assert len(tokens) >= 3

        # admin이 생성한 토큰만
        admin_tokens = RegistrationTokenModel.get_active_tokens(created_by='admin')
        assert len(admin_tokens) >= 2

    @pytest.mark.skip(reason="cleanup_expired 로직 확인 필요 - 24시간 이내 토큰만 삭제하는지 확인")
    def test_cleanup_expired(self, app):
        """만료된 토큰 자동 정리"""
        from utils import get_db
        db = get_db()

        # 오래된 만료 토큰 생성 (25시간 전)
        old_expires = datetime.now() - timedelta(hours=25)
        db.execute('''
            INSERT INTO pc_registration_tokens 
            (token, usage_type, expires_in, created_by, expires_at)
            VALUES ('000001', 'single', 60, 'admin', ?)
        ''', (old_expires.isoformat(),))

        # 정리 실행
        deleted_count = RegistrationTokenModel.cleanup_expired()

        assert deleted_count >= 1

        # 토큰이 삭제되었는지 확인
        token_data = RegistrationTokenModel.get_by_token('000001')
        assert token_data is None

    def test_multi_use_token_reusable(self, app):
        """재사용 가능 토큰은 여러 번 사용 가능"""
        token = RegistrationTokenModel.create(
            created_by='admin',
            usage_type='multi',
            expires_in=600
        )

        # 5번 사용
        for i in range(5):
            is_valid, error_msg = RegistrationTokenModel.validate(token['token'])
            assert is_valid is True
            RegistrationTokenModel.mark_used(token['token'])

        # 6번째도 가능
        is_valid, error_msg = RegistrationTokenModel.validate(token['token'])
        assert is_valid is True

    def test_token_uniqueness(self, app):
        """토큰 중복 생성 방지"""
        tokens = set()

        # 100개 생성
        for i in range(100):
            token = RegistrationTokenModel.create('admin', 'single', 600)
            tokens.add(token['token'])

        # 모두 고유해야 함
        assert len(tokens) == 100
