"""
Long-poll 명령 조회 API 및 네트워크 이벤트 테스트
"""
import pytest


class TestLongPollCommands:
    """Long-poll 명령 조회 테스트"""

    def test_longpoll_no_command(self, client, registered_pc):
        """명령 없을 때 즉시 반환 (timeout=0)"""
        pc_id, machine_id = registered_pc

        response = client.get('/api/client/commands', query_string={
            'machine_id': machine_id, 'timeout': 0
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert data['data']['has_command'] is False
        assert data['data']['command'] is None

    def test_longpoll_with_pending_command(self, client, registered_pc):
        """대기 중인 명령이 있을 때 즉시 반환"""
        pc_id, machine_id = registered_pc

        with client.session_transaction() as sess:
            sess['admin'] = True
            sess['username'] = 'admin'

        # 명령 생성
        client.post(f'/api/pc/{pc_id}/shutdown', json={'delay': 0})

        # long-poll 요청 (timeout=0으로 즉시 반환)
        response = client.get('/api/client/commands', query_string={
            'machine_id': machine_id, 'timeout': 0
        })

        data = response.get_json()
        assert data['status'] == 'success'
        assert data['data']['has_command'] is True
        assert data['data']['command']['type'] == 'shutdown'

    def test_longpoll_unknown_machine(self, client):
        """등록되지 않은 machine_id"""
        response = client.get('/api/client/commands', query_string={
            'machine_id': 'UNKNOWN-MACHINE', 'timeout': 0
        })
        assert response.status_code == 404

    def test_longpoll_missing_machine_id(self, client):
        """machine_id 누락"""
        response = client.get('/api/client/commands', query_string={'timeout': 0})
        assert response.status_code == 400

    def test_longpoll_updates_online_status(self, client, registered_pc):
        """long-poll 시작 시 PC is_online=1로 업데이트"""
        pc_id, machine_id = registered_pc

        response = client.get('/api/client/commands', query_string={
            'machine_id': machine_id, 'timeout': 0
        })
        assert response.status_code == 200

        # 관리자 API로 online 상태 확인
        with client.session_transaction() as sess:
            sess['admin'] = True
            sess['username'] = 'admin'
        pc_resp = client.get(f'/api/pc/{pc_id}')
        assert pc_resp.status_code == 200
        pc_data = pc_resp.get_json()
        assert pc_data.get('is_online') == 1

    def test_offline_signal(self, client, registered_pc):
        """네트워크 오프라인 신호"""
        pc_id, machine_id = registered_pc

        response = client.post('/api/client/offline', json={'machine_id': machine_id})
        assert response.status_code == 200

    def test_offline_signal_sets_pc_offline(self, client, registered_pc):
        """오프라인 신호 수신 후 PC is_online=0"""
        pc_id, machine_id = registered_pc

        # 먼저 online 상태로 만들기
        client.get('/api/client/commands', query_string={'machine_id': machine_id, 'timeout': 0})

        # 오프라인 처리
        response = client.post('/api/client/offline', json={'machine_id': machine_id})
        assert response.status_code == 200

        # 관리자 API로 offline 상태 확인
        with client.session_transaction() as sess:
            sess['admin'] = True
            sess['username'] = 'admin'
        pc_resp = client.get(f'/api/pc/{pc_id}')
        assert pc_resp.status_code == 200
        pc_data = pc_resp.get_json()
        assert pc_data.get('is_online') == 0

    def test_reconnect_restores_online_status(self, client, registered_pc):
        """오프라인 후 재연결 시 is_online=1 복원"""
        pc_id, machine_id = registered_pc

        # 오프라인 처리
        client.post('/api/client/offline', json={'machine_id': machine_id})

        # 재연결 (long-poll)
        response = client.get('/api/client/commands', query_string={
            'machine_id': machine_id, 'timeout': 0
        })
        assert response.status_code == 200

        # 관리자 API로 online 상태 확인
        with client.session_transaction() as sess:
            sess['admin'] = True
            sess['username'] = 'admin'
        pc_resp = client.get(f'/api/pc/{pc_id}')
        assert pc_resp.status_code == 200
        pc_data = pc_resp.get_json()
        assert pc_data.get('is_online') == 1

    def test_heartbeat_full_update(self, client, registered_pc):
        """/api/client/heartbeat 전체 업데이트"""
        pc_id, machine_id = registered_pc

        response = client.post('/api/client/heartbeat', json={
            'machine_id': machine_id,
            'full_update': True,
            'system_info': {
                'cpu_usage': 45.0,
                'ram_used': 8.0,
                'ram_usage_percent': 50.0,
                'disk_usage': {'C:\\\\': {'used_gb': 100, 'free_gb': 100, 'percent': 50}},
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
        """/api/client/heartbeat 경량 업데이트"""
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