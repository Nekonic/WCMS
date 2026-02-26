"""
서버 API 통합 테스트
"""
import json
import pytest


class TestClientAPI:
    """클라이언트 API 테스트"""

    def test_client_register(self, client, test_pin):
        """클라이언트 등록 API"""
        response = client.post('/api/client/register', json={
            'machine_id': 'TEST-MACHINE-001',
            'pin': test_pin,
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

    def test_client_heartbeat(self, client, test_pin):
        """클라이언트 하트비트 API"""
        # 먼저 PC 등록
        reg_response = client.post('/api/client/register', json={
            'machine_id': 'TEST-HEARTBEAT-001',
            'pin': test_pin,
            'hostname': 'test-hb',
            'mac_address': '11:22:33:44:55:66'
        })
        pc_id = reg_response.get_json()['pc_id']

        # 하트비트 전송
        response = client.post('/api/client/heartbeat', json={
            'pc_id': pc_id,
            'cpu_usage': 45.5,
            'ram_used': 8.5,
            'ram_usage_percent': 53.1,
            'current_user': 'student'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'

    def test_client_command_get(self, client, test_pin):
        """클라이언트 명령 조회 API"""
        # 먼저 PC 등록
        reg_response = client.post('/api/client/register', json={
            'machine_id': 'TEST-CMD-GET-001',
            'pin': test_pin,
            'hostname': 'test-cmd',
            'mac_address': '99:88:77:66:55:44'
        })
        pc_id = reg_response.get_json()['pc_id']

        response = client.get('/api/client/commands', query_string={
            'machine_id': 'TEST-CMD-GET-001', 'timeout': 0
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'


class TestAdminAPI:
    """관리자 API 테스트"""

    @pytest.fixture(autouse=True)
    def login_admin(self, client):
        """관리자 로그인 세션 설정"""
        with client.session_transaction() as sess:
            sess['admin'] = True
            sess['username'] = 'admin'

    def test_admin_list_pcs(self, client):
        """PC 목록 조회 API (인증 필요)"""
        response = client.get('/api/pcs')
        assert response.status_code == 200

    def test_admin_command_send(self, client, test_pin):
        """관리자 명령 전송 API"""
        # 먼저 PC 등록
        reg_response = client.post('/api/client/register', json={
            'machine_id': 'TEST-ADMIN-CMD-001',
            'pin': test_pin,
            'hostname': 'test-admin-cmd',
            'mac_address': '12:34:56:78:90:AB'
        })
        pc_id = reg_response.get_json()['pc_id']

        # 테스트 명령 전송
        response = client.post(f'/api/pc/{pc_id}/shutdown', json={})
        assert response.status_code == 200

    def test_admin_uninstall_command(self, client, test_pin):
        """프로그램 삭제 명령 테스트"""
        # 먼저 PC 등록
        reg_response = client.post('/api/client/register', json={
            'machine_id': 'TEST-UNINSTALL-001',
            'pin': test_pin,
            'hostname': 'test-uninstall',
            'mac_address': '12:34:56:78:90:AC'
        })
        pc_id = reg_response.get_json()['pc_id']

        # 프로그램 삭제 명령 전송
        response = client.post(f'/api/pc/{pc_id}/uninstall', json={
            'app_id': 'googlechrome'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'command_id' in data

    def test_admin_create_account_with_options(self, client, test_pin):
        """계정 생성 명령 테스트 (옵션 포함)"""
        # 먼저 PC 등록
        reg_response = client.post('/api/client/register', json={
            'machine_id': 'TEST-ACCOUNT-001',
            'pin': test_pin,
            'hostname': 'test-account',
            'mac_address': '12:34:56:78:90:AD'
        })
        pc_id = reg_response.get_json()['pc_id']

        # 계정 생성 명령 전송
        response = client.post(f'/api/pc/{pc_id}/account/create', json={
            'username': 'testuser',
            'password': 'password123',
            'full_name': 'Test User',
            'comment': 'Created by Test',
            'language': 'ko-KR',
            'keyboard': '101/104'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'command_id' in data


class TestHealthCheck:
    """헬스 체크 테스트"""

    def test_root_endpoint(self, client):
        """루트 엔드포인트 접근"""
        response = client.get('/')
        # 200 (성공) 또는 302 (리다이렉트) 허용
        assert response.status_code in [200, 302]
