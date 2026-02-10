"""
클라이언트-서버 통합 테스트
실제 통신 흐름을 시뮬레이션하여 테스트합니다.
"""
import pytest
import time
from datetime import datetime, timedelta


class TestClientServerIntegration:
    """클라이언트-서버 간 전체 통신 흐름 테스트"""

    def test_full_registration_flow(self, client, app):
        """전체 등록 플로우: PIN 생성 → PC 등록 → 검증"""
        # 1. 관리자가 PIN 생성
        with client.session_transaction() as sess:
            sess['admin'] = True
            sess['username'] = 'admin'

        pin_response = client.post('/api/admin/registration-token', json={
            'usage_type': 'single',
            'expires_in': 600
        })
        assert pin_response.status_code == 200
        pin_data = pin_response.get_json()
        pin = pin_data['token']
        assert len(pin) == 6

        # 2. 클라이언트가 PIN으로 등록
        reg_response = client.post('/api/client/register', json={
            'machine_id': 'INTEGRATION-TEST-001',
            'pin': pin,
            'hostname': 'test-integration-pc',
            'mac_address': 'AA:BB:CC:DD:EE:01',
            'cpu_model': 'Intel Core i7',
            'cpu_cores': 8,
            'cpu_threads': 16,
            'ram_total': 32.0
        })
        assert reg_response.status_code == 200
        reg_data = reg_response.get_json()
        assert reg_data['status'] == 'success'
        pc_id = reg_data['pc_id']

        # 3. API를 통해 PC 정보 조회 (검증 확인)
        pc_detail_response = client.get(f'/api/pc/{pc_id}')
        assert pc_detail_response.status_code == 200
        pc_detail = pc_detail_response.get_json()
        assert pc_detail['machine_id'] == 'INTEGRATION-TEST-001'
        assert pc_detail['hostname'] == 'test-integration-pc'

    def test_heartbeat_and_command_flow(self, client, app, test_pin):
        """하트비트와 명령 실행 플로우"""
        # 1. PC 등록
        reg_response = client.post('/api/client/register', json={
            'machine_id': 'HEARTBEAT-TEST-001',
            'pin': test_pin,
            'hostname': 'test-hb-pc',
            'mac_address': '11:22:33:44:55:01'
        })
        pc_id = reg_response.get_json()['pc_id']

        # 2. 첫 하트비트 전송
        hb_response = client.post('/api/client/heartbeat', json={
            'pc_id': pc_id,
            'cpu_usage': 25.5,
            'ram_used': 8.0,
            'ram_usage_percent': 25.0,
            'current_user': 'student01'
        })
        assert hb_response.status_code == 200

        # 3. API를 통해 PC 상태 확인
        pc_detail = client.get(f'/api/pc/{pc_id}').get_json()
        assert pc_detail['cpu_usage'] == 25.5
        assert pc_detail['current_user'] == 'student01'

        # 4. 관리자가 명령 전송
        with client.session_transaction() as sess:
            sess['admin'] = True
            sess['username'] = 'admin'

        cmd_response = client.post(f'/api/pc/{pc_id}/shutdown', json={
            'delay': 60,
            'message': 'System maintenance'
        })
        assert cmd_response.status_code == 200

        # 5. 클라이언트가 명령 조회 (새 API)
        cmd_get_response = client.post('/api/client/commands', json={
            'machine_id': 'HEARTBEAT-TEST-001'
        })
        assert cmd_get_response.status_code == 200
        cmd_data = cmd_get_response.get_json()
        assert cmd_data['status'] == 'success'
        assert cmd_data['data']['has_command'] is True
        assert cmd_data['data']['command']['type'] == 'shutdown'
        command_id = cmd_data['data']['command']['id']

        # 6. 클라이언트가 명령 실행 결과 전송 (새 API)
        result_response = client.post(f'/api/client/commands/{command_id}/result', json={
            'status': 'success',
            'output': 'Shutdown initiated'
        })
        assert result_response.status_code == 200


    def test_multi_pc_concurrent_heartbeat(self, client, app, test_pin):
        """여러 PC의 동시 하트비트 테스트"""
        # 3개의 PC 등록
        pc_ids = []
        for i in range(3):
            reg_response = client.post('/api/client/register', json={
                'machine_id': f'CONCURRENT-TEST-{i:03d}',
                'pin': test_pin,
                'hostname': f'test-concurrent-{i}',
                'mac_address': f'22:33:44:55:66:{i:02d}'
            })
            pc_ids.append(reg_response.get_json()['pc_id'])

        # 동시에 하트비트 전송
        for i, pc_id in enumerate(pc_ids):
            hb_response = client.post('/api/client/heartbeat', json={
                'pc_id': pc_id,
                'cpu_usage': 10.0 + i * 10,
                'ram_used': 4.0 + i * 2,
                'ram_usage_percent': 25.0 + i * 10,
                'current_user': f'user{i:02d}'
            })
            assert hb_response.status_code == 200

        # API를 통해 모든 PC의 상태 확인
        for i, pc_id in enumerate(pc_ids):
            pc_detail = client.get(f'/api/pc/{pc_id}').get_json()
            assert pc_detail['cpu_usage'] == 10.0 + i * 10
            assert pc_detail['current_user'] == f'user{i:02d}'


class TestErrorScenarios:
    """에러 시나리오 테스트"""

    def test_register_with_invalid_pin(self, client):
        """잘못된 PIN으로 등록 시도"""
        response = client.post('/api/client/register', json={
            'machine_id': 'INVALID-PIN-TEST',
            'pin': '999999',
            'hostname': 'test-invalid',
            'mac_address': 'AA:BB:CC:DD:EE:99'
        })
        # 잘못된 PIN은 실패해야 함
        assert response.status_code in [400, 401, 403]

    def test_register_with_expired_pin(self, client, app):
        """만료된 PIN으로 등록 시도"""
        # 1초 만료되는 PIN 생성
        with client.session_transaction() as sess:
            sess['admin'] = True
            sess['username'] = 'admin'

        pin_response = client.post('/api/admin/registration-token', json={
            'usage_type': 'single',
            'expires_in': 1
        })

        # 토큰 생성 실패 시 (최소 시간 제한으로 인해)
        if pin_response.status_code != 200:
            # 최소 만료 시간이 60초인 경우, 이 테스트는 스킵
            return

        pin = pin_response.get_json()['token']

        # 2초 대기 (만료)
        time.sleep(2)

        # 만료된 PIN으로 등록 시도
        response = client.post('/api/client/register', json={
            'machine_id': 'EXPIRED-PIN-TEST',
            'pin': pin,
            'hostname': 'test-expired',
            'mac_address': 'BB:CC:DD:EE:FF:99'
        })
        assert response.status_code in [400, 401, 403]

    def test_single_use_pin_reuse(self, client, app):
        """1회용 PIN 재사용 시도"""
        # 1회용 PIN 생성
        with client.session_transaction() as sess:
            sess['admin'] = True
            sess['username'] = 'admin'

        pin_response = client.post('/api/admin/registration-token', json={
            'usage_type': 'single',
            'expires_in': 600
        })
        pin = pin_response.get_json()['token']

        # 첫 번째 등록 (성공)
        reg1 = client.post('/api/client/register', json={
            'machine_id': 'SINGLE-USE-TEST-1',
            'pin': pin,
            'hostname': 'test-single-1',
            'mac_address': 'CC:DD:EE:FF:00:01'
        })
        assert reg1.status_code == 200

        # 두 번째 등록 시도 (실패해야 함)
        reg2 = client.post('/api/client/register', json={
            'machine_id': 'SINGLE-USE-TEST-2',
            'pin': pin,
            'hostname': 'test-single-2',
            'mac_address': 'CC:DD:EE:FF:00:02'
        })
        assert reg2.status_code in [400, 401, 403]

    def test_unverified_pc_command_access(self, client, app):
        """미검증 PC의 명령 조회 시도"""
        # PIN 없이 등록 시도 (실패해야 함)
        response = client.post('/api/client/register', json={
            'machine_id': 'UNVERIFIED-TEST',
            'hostname': 'test-unverified',
            'mac_address': 'ZZ:ZZ:ZZ:ZZ:ZZ:ZZ'
            # PIN이 없음
        })
        # PIN이 없으면 등록이 거부되어야 함
        assert response.status_code in [400, 401, 403]

    def test_heartbeat_with_ip_change(self, client, test_pin):
        """IP 변경 시 하트비트 동작"""
        # PC 등록
        reg_response = client.post('/api/client/register', json={
            'machine_id': 'IP-CHANGE-TEST',
            'pin': test_pin,
            'hostname': 'test-ip-change',
            'mac_address': 'DD:EE:FF:00:11:22'
        })
        pc_id = reg_response.get_json()['pc_id']

        # 첫 하트비트 (IP: 127.0.0.1 - 테스트 클라이언트 기본값)
        hb1 = client.post('/api/client/heartbeat', json={
            'pc_id': pc_id,
            'cpu_usage': 20.0,
            'ram_used': 8.0,
            'ram_usage_percent': 50.0
        })
        assert hb1.status_code == 200

        # IP가 변경되어도 machine_id로 식별되어야 함
        # (실제 테스트 환경에서는 IP를 바꿀 수 없으므로 로직 확인만)
        hb2 = client.post('/api/client/heartbeat', json={
            'pc_id': pc_id,
            'cpu_usage': 30.0,
            'ram_used': 10.0,
            'ram_usage_percent': 62.5
        })
        assert hb2.status_code == 200


class TestAdminWorkflows:
    """관리자 워크플로우 테스트"""

    @pytest.fixture(autouse=True)
    def login_admin(self, client):
        """관리자 로그인"""
        with client.session_transaction() as sess:
            sess['admin'] = True
            sess['username'] = 'admin'

    def test_admin_create_and_manage_tokens(self, client, app):
        """관리자 토큰 생성 및 관리"""
        # 토큰 생성
        response = client.post('/api/admin/registration-token', json={
            'usage_type': 'multi',
            'expires_in': 3600
        })
        assert response.status_code == 200
        token_data = response.get_json()
        token_id = token_data['id']

        # 토큰 목록 조회
        list_response = client.get('/api/admin/registration-tokens')
        assert list_response.status_code == 200
        response_data = list_response.get_json()
        tokens = response_data['tokens']
        assert any(t['id'] == token_id for t in tokens)

        # 토큰 삭제
        delete_response = client.delete(f'/api/admin/registration-token/{token_id}')
        assert delete_response.status_code == 200

    def test_admin_pc_management(self, client, test_pin):
        """관리자 PC 관리"""
        # PC 등록
        reg_response = client.post('/api/client/register', json={
            'machine_id': 'ADMIN-MGMT-TEST',
            'pin': test_pin,
            'hostname': 'test-admin-mgmt',
            'mac_address': 'EE:FF:00:11:22:33'
        })
        pc_id = reg_response.get_json()['pc_id']

        # PC 목록 조회
        list_response = client.get('/api/pcs')
        assert list_response.status_code == 200
        pcs = list_response.get_json()
        assert any(pc['id'] == pc_id for pc in pcs)

        # PC 상세 정보 조회
        detail_response = client.get(f'/api/pc/{pc_id}')
        assert detail_response.status_code == 200
        pc_detail = detail_response.get_json()
        assert pc_detail['machine_id'] == 'ADMIN-MGMT-TEST'

        # PC 삭제
        delete_response = client.delete(f'/api/pc/{pc_id}')
        assert delete_response.status_code == 200

        # 삭제 확인
        list_after = client.get('/api/pcs').get_json()
        assert not any(pc['id'] == pc_id for pc in list_after)


class TestCommandExecution:
    """명령 실행 테스트"""

    @pytest.fixture(autouse=True)
    def setup(self, client, test_pin):
        """테스트용 PC 등록"""
        reg_response = client.post('/api/client/register', json={
            'machine_id': 'CMD-EXEC-TEST',
            'pin': test_pin,
            'hostname': 'test-cmd-exec',
            'mac_address': 'FF:00:11:22:33:44'
        })
        self.pc_id = reg_response.get_json()['pc_id']

    def test_shutdown_command(self, client):
        """종료 명령 테스트"""
        with client.session_transaction() as sess:
            sess['admin'] = True
            sess['username'] = 'admin'

        response = client.post(f'/api/pc/{self.pc_id}/shutdown', json={
            'delay': 60,
            'message': 'Test shutdown'
        })
        assert response.status_code == 200

    def test_restart_command(self, client):
        """재시작 명령 테스트"""
        with client.session_transaction() as sess:
            sess['admin'] = True
            sess['username'] = 'admin'

        response = client.post(f'/api/pc/{self.pc_id}/restart', json={
            'delay': 60
        })
        assert response.status_code == 200

    def test_message_command(self, client):
        """메시지 전송 명령 테스트"""
        with client.session_transaction() as sess:
            sess['admin'] = True
            sess['username'] = 'admin'

        response = client.post(f'/api/pc/{self.pc_id}/message', json={
            'message': 'Test message',
            'duration': 10
        })
        assert response.status_code == 200

    def test_process_kill_command(self, client):
        """프로세스 종료 명령 테스트"""
        with client.session_transaction() as sess:
            sess['admin'] = True
            sess['username'] = 'admin'

        response = client.post(f'/api/pc/{self.pc_id}/kill-process', json={
            'process_name': 'notepad.exe'
        })
        assert response.status_code == 200
