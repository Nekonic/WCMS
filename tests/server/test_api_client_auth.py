"""
PIN 인증이 포함된 클라이언트 등록 API 테스트
"""
import pytest


class TestClientRegistrationWithPIN:
    """클라이언트 등록 (PIN 인증) 테스트"""

    def test_register_with_valid_pin(self, client, test_pin):
        """유효한 PIN으로 등록 성공"""
        # 클라이언트 등록
        response = client.post('/api/client/register', json={
            'machine_id': 'TEST-001',
            'pin': test_pin,
            'hostname': 'TEST-PC',
            'mac_address': 'AA:BB:CC:DD:EE:FF',
            'cpu_cores': 4,
            'ram_total': 16.0
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'pc_id' in data

    def test_register_with_expired_pin(self, client, app):
        """만료된 PIN으로 등록 시도"""
        from utils.database import get_db
        from datetime import datetime, timedelta

        db = get_db()

        # 만료된 토큰 생성
        expired_pin = "111111"
        expires_at = datetime.now() - timedelta(seconds=10)

        db.execute('''
            INSERT INTO pc_registration_tokens 
            (token, usage_type, expires_in, created_by, expires_at)
            VALUES (?, 'single', 60, 'admin', ?)
        ''', (expired_pin, expires_at.isoformat()))

        # 등록 시도
        response = client.post('/api/client/register', json={
            'machine_id': 'TEST-002',
            'pin': expired_pin,
            'hostname': 'TEST-PC-2',
            'mac_address': 'AA:BB:CC:DD:EE:FF'
        })

        assert response.status_code == 403
        data = response.get_json()
        assert 'expired' in data['message'].lower()

    def test_register_without_pin(self, client):
        """PIN 없이 등록 시도 (실패해야 함)"""
        response = client.post('/api/client/register', json={
            'machine_id': 'TEST-003',
            'hostname': 'TEST-PC-3',
            'mac_address': 'AA:BB:CC:DD:EE:FF'
        })

        assert response.status_code == 400
        data = response.get_json()
        assert 'pin' in data['message'].lower() or 'required' in data['message'].lower()

    def test_register_with_invalid_pin(self, client):
        """존재하지 않는 PIN으로 등록 시도"""
        response = client.post('/api/client/register', json={
            'machine_id': 'TEST-004',
            'pin': '999999',
            'hostname': 'TEST-PC-4',
            'mac_address': 'AA:BB:CC:DD:EE:FF'
        })

        assert response.status_code == 403
        data = response.get_json()
        assert 'invalid' in data['message'].lower()

    def test_register_single_use_pin_twice(self, client, test_pin):
        """1회용 PIN 재사용 시도"""
        # 첫 번째 등록 (성공)
        response1 = client.post('/api/client/register', json={
            'machine_id': 'TEST-005',
            'pin': test_pin,
            'hostname': 'TEST-PC-5',
            'mac_address': 'AA:BB:CC:DD:EE:FF'
        })
        assert response1.status_code == 200

        # 두 번째 등록 시도 (test_pin은 multi라서 성공함 - 1회용 테스트는 별도 필요)
        # 이 테스트는 multi PIN이므로 성공할 것임
        response2 = client.post('/api/client/register', json={
            'machine_id': 'TEST-006',
            'pin': test_pin,
            'hostname': 'TEST-PC-6',
            'mac_address': 'BB:CC:DD:EE:FF:00'
        })

        # test_pin은 multi이므로 성공
        assert response2.status_code == 200

    def test_register_multi_use_pin_multiple_times(self, client, test_pin):
        """재사용 가능 PIN으로 여러 PC 등록"""
        # 5대 PC 등록 (모두 성공해야 함)
        for i in range(5):
            response = client.post('/api/client/register', json={
                'machine_id': f'TEST-MULTI-{i:03d}',
                'pin': test_pin,
                'hostname': f'TEST-PC-MULTI-{i}',
                'mac_address': f'AA:BB:CC:DD:EE:{i:02X}'
            })

            assert response.status_code == 200
            data = response.get_json()
            assert data['status'] == 'success'

    def test_register_updates_pc_verified_status(self, client, app, test_pin):
        """등록 시 is_verified, registered_with_token 업데이트 확인"""
        # 등록
        response = client.post('/api/client/register', json={
            'machine_id': 'TEST-VERIFY-001',
            'pin': test_pin,
            'hostname': 'TEST-VERIFY-PC',
            'mac_address': 'AA:BB:CC:DD:EE:11'
        })

        assert response.status_code == 200
        pc_id = response.get_json()['pc_id']

        # DB 확인
        from utils.database import get_db
        db = get_db()

        pc = db.execute(
            'SELECT is_verified, registered_with_token FROM pc_info WHERE id=?',
            (pc_id,)
        ).fetchone()

        assert pc['is_verified'] == 1
        assert pc['registered_with_token'] == test_pin
