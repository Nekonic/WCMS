"""
서버 API 통합 테스트
"""
import json
import pytest


class TestClientAPI:
    """클라이언트 API 테스트"""

    def test_client_register(self, client):
        """클라이언트 등록 API"""
        response = client.post('/api/client/register', json={
            'machine_id': 'TEST-MACHINE-001',
            'hostname': 'test-pc',
            'mac_address': 'AA:BB:CC:DD:EE:FF',
            'cpu_model': 'Intel Core i5',
            'cpu_cores': 4,
            'cpu_threads': 8,
            'ram_total': 16.0
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'pc_id' in data

    def test_client_heartbeat(self, client):
        """클라이언트 하트비트 API"""
        # 먼저 PC 등록
        client.post('/api/client/register', json={
            'machine_id': 'TEST-HEARTBEAT-001',
            'hostname': 'test-hb',
            'mac_address': '11:22:33:44:55:66'
        })

        # 하트비트 전송
        response = client.post('/api/client/heartbeat', json={
            'pc_id': 1,
            'cpu_usage': 45.5,
            'ram_used': 8.5,
            'ram_usage_percent': 53.1,
            'current_user': 'student'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'

    def test_client_command_get(self, client):
        """클라이언트 명령 조회 API"""
        response = client.get('/api/client/command?pc_id=1')

        # PC가 등록되지 않았으면 404
        assert response.status_code in [200, 404]


class TestAdminAPI:
    """관리자 API 테스트"""

    def test_admin_list_pcs(self, client):
        """PC 목록 조회 API (인증 필요)"""
        response = client.get('/api/pcs')

        # 로그인 필요하면 302 또는 401
        # 기본적으로는 접근 가능해야 함
        assert response.status_code in [200, 302, 401]

    def test_admin_command_send(self, client):
        """관리자 명령 전송 API"""
        # 테스트 명령 전송
        response = client.post('/api/pc/1/shutdown', json={})

        # PC가 없으면 404, 있으면 200
        assert response.status_code in [200, 404]


class TestHealthCheck:
    """헬스 체크 테스트"""

    def test_root_endpoint(self, client):
        """루트 엔드포인트 접근"""
        response = client.get('/')

        # 200 또는 302 (리다이렉트) 중 하나
        assert response.status_code in [200, 302]

