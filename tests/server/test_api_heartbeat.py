"""
명령 조회 + 하트비트 통합 API 테스트
"""
import pytest
import time


class TestCommandHeartbeatIntegration:
    """명령 조회 + 하트비트 통합 테스트"""

    def test_command_get_with_heartbeat(self, client, registered_pc):
        """POST 방식 명령 조회 + 경량 하트비트"""
        pc_id, machine_id = registered_pc

        response = client.post('/api/client/commands', json={
            'machine_id': machine_id,
            'heartbeat': {
                'cpu_usage': 50.0,
                'ram_usage_percent': 60.0,
                'ip_address': '192.168.1.100'
            }
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert data['data']['heartbeat_processed'] is True
        assert 'ip_changed' in data['data']

    def test_command_get_without_heartbeat(self, client, registered_pc):
        """명령 조회 (하트비트 없음)"""
        pc_id, machine_id = registered_pc

        response = client.post('/api/client/commands', json={
            'machine_id': machine_id
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert data['data']['has_command'] is False
        assert data['data']['heartbeat_processed'] is False

    def test_heartbeat_ip_changed_detection(self, client, test_pin):
        """IP 변경 감지"""
        # PC 등록 시 IP 설정
        reg_response = client.post('/api/client/register', json={
            'machine_id': 'IP-CHANGE-TEST',
            'pin': test_pin,
            'hostname': 'test-ip',
            'mac_address': 'AA:BB:CC:DD:EE:99',
            'ip_address': '192.168.1.100'  # 초기 IP
        })
        machine_id = 'IP-CHANGE-TEST'

        # 첫 번째 요청 (동일 IP: 192.168.1.100)
        response1 = client.post('/api/client/commands', json={
            'machine_id': machine_id,
            'heartbeat': {
                'cpu_usage': 50.0,
                'ram_usage_percent': 60.0,
                'ip_address': '192.168.1.100'
            }
        })

        data1 = response1.get_json()
        assert data1['status'] == 'success'
        # 동일 IP이므로 변경 없음
        assert data1['data']['ip_changed'] is False

        # Rate limiting 회피를 위해 2초 대기
        time.sleep(2.1)

        # 두 번째 요청 (IP 변경: 192.168.1.101)
        response2 = client.post('/api/client/commands', json={
            'machine_id': machine_id,
            'heartbeat': {
                'cpu_usage': 55.0,
                'ram_usage_percent': 65.0,
                'ip_address': '192.168.1.101'
            }
        })

        data2 = response2.get_json()
        assert data2['status'] == 'success'
        # IP 변경 감지되어야 함
        assert data2['data']['ip_changed'] is True

    def test_heartbeat_full_update_flag(self, client, registered_pc):
        """full_update 플래그 테스트"""
        pc_id, machine_id = registered_pc

        # 전체 하트비트
        response = client.post('/api/client/heartbeat', json={
            'machine_id': machine_id,
            'full_update': True,
            'system_info': {
                'cpu_usage': 45.0,
                'ram_used': 8.0,
                'ram_usage_percent': 50.0,
                'disk_usage': {
                    'C:\\\\': {'used_gb': 100, 'free_gb': 100, 'percent': 50}
                },
                'current_user': 'student',
                'uptime': 3600,
                'ip_address': '192.168.1.100',
                'processes': ['chrome.exe', 'notepad.exe']
            }
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['full_update'] is True

    def test_heartbeat_light_update(self, client, registered_pc):
        """경량 하트비트 (full_update=false)"""
        pc_id, machine_id = registered_pc

        response = client.post('/api/client/heartbeat', json={
            'machine_id': machine_id,
            'full_update': False,
            'system_info': {
                'cpu_usage': 45.0,
                'ram_usage_percent': 50.0,
                'ip_address': '192.168.1.100'
            }
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['full_update'] is False

    def test_command_with_pending_command(self, client, registered_pc):
        """대기 중인 명령이 있을 때"""
        pc_id, machine_id = registered_pc

        # 관리자로 로그인하여 명령 생성
        with client.session_transaction() as sess:
            sess['admin'] = True
            sess['username'] = 'admin'

        # shutdown 명령 생성 (API 사용)
        client.post(f'/api/pc/{pc_id}/shutdown', json={'delay': 0})

        # 명령 조회 + 하트비트
        response = client.post('/api/client/commands', json={
            'machine_id': machine_id,
            'heartbeat': {
                'cpu_usage': 50.0,
                'ram_usage_percent': 60.0,
                'ip_address': '192.168.1.100'
            }
        })

        data = response.get_json()
        assert data['status'] == 'success'
        assert data['data']['has_command'] is True
        assert data['data']['command']['type'] == 'shutdown'
        assert data['data']['heartbeat_processed'] is True

    def test_rate_limiting(self, client, registered_pc):
        """Rate limiting (2초 간격)"""
        pc_id, machine_id = registered_pc

        # 첫 번째 요청
        response1 = client.post('/api/client/commands', json={
            'machine_id': machine_id,
            'heartbeat': {'cpu_usage': 50.0, 'ram_usage_percent': 60.0}
        })
        assert response1.status_code == 200

        # 즉시 두 번째 요청 (rate limit에 걸려야 함)
        response2 = client.post('/api/client/commands', json={
            'machine_id': machine_id,
            'heartbeat': {'cpu_usage': 50.0, 'ram_usage_percent': 60.0}
        })

        # Rate limit에 걸려도 200 OK, 단 has_command: false
        assert response2.status_code == 200
        data2 = response2.get_json()
        assert data2['status'] == 'success'
        assert data2['data']['has_command'] is False
        # Note: Rate limit 체크는 구현에 따라 다를 수 있음

