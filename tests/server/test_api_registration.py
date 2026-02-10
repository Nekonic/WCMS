"""
등록 토큰 관리 API 테스트

관리자의 토큰 생성/조회/삭제 API를 테스트합니다.
"""
import pytest
import json


class TestRegistrationTokenAPI:
    """등록 토큰 관리 API 테스트"""

    def test_admin_create_token_single(self, client, admin_session):
        """1회용 토큰 생성 (관리자 인증 필요)"""
        response = client.post(
            '/api/admin/registration-token',
            json={
                'usage_type': 'single',
                'expires_in': 600
            }
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'token' in data
        assert len(data['token']) == 6
        assert data['token'].isdigit()
        assert data['usage_type'] == 'single'

    def test_admin_create_token_multi_custom_expiry(self, client, admin_session):
        """재사용 가능 토큰 생성 (커스텀 만료 시간)"""
        response = client.post(
            '/api/admin/registration-token',
            json={
                'usage_type': 'multi',
                'expires_in': 1800
            }
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['usage_type'] == 'multi'

    def test_admin_create_token_invalid_type(self, client, admin_session):
        """잘못된 usage_type"""
        response = client.post(
            '/api/admin/registration-token',
            json={
                'usage_type': 'invalid',
                'expires_in': 600
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data['message'].lower() or 'must be' in data['message'].lower()

    def test_admin_create_token_invalid_expiry(self, client, admin_session):
        """잘못된 만료 시간"""
        # 너무 짧음 (< 60초)
        response = client.post(
            '/api/admin/registration-token',
            json={
                'usage_type': 'single',
                'expires_in': 30
            }
        )
        assert response.status_code == 400

        # 너무 김 (> 86400초)
        response = client.post(
            '/api/admin/registration-token',
            json={
                'usage_type': 'single',
                'expires_in': 100000
            }
        )
        assert response.status_code == 400

    def test_admin_list_tokens(self, client, admin_session):
        """토큰 목록 조회"""
        # 토큰 2개 생성
        client.post('/api/admin/registration-token', json={'usage_type': 'single'})
        client.post('/api/admin/registration-token', json={'usage_type': 'multi'})

        # 목록 조회
        response = client.get('/api/admin/registration-tokens')

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'tokens' in data
        assert len(data['tokens']) >= 2

    def test_admin_list_all_tokens(self, client, admin_session):
        """모든 토큰 조회 (만료된 것 포함)"""
        response = client.get('/api/admin/registration-tokens?all=true')

        assert response.status_code == 200
        data = response.get_json()
        assert 'tokens' in data

    def test_admin_delete_token(self, client, admin_session):
        """토큰 삭제"""
        # 토큰 생성
        create_response = client.post(
            '/api/admin/registration-token',
            json={'usage_type': 'single'}
        )
        token_data = create_response.get_json()
        token_id = token_data['id']

        # 삭제 (ID 사용)
        response = client.delete(f'/api/admin/registration-token/{token_id}')

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'

    def test_admin_delete_nonexistent_token(self, client, admin_session):
        """존재하지 않는 토큰 삭제 시도"""
        response = client.delete('/api/admin/registration-token/999999')

        assert response.status_code == 404

    def test_admin_token_unauthorized(self, client):
        """인증 없이 토큰 API 호출 (실패해야 함)"""
        # 토큰 생성 시도
        response = client.post(
            '/api/admin/registration-token',
            json={'usage_type': 'single'}
        )

        # 401 또는 403 또는 redirect
        assert response.status_code in [401, 403, 302]
