"""
archive/code/app.py 전용 완전한 통합 테스트 스위트

이 테스트는 정상 작동하는 archive/code/app.py를 기준으로 작성되었으며,
리팩터링된 코드가 동일하게 작동하는지 검증하는 기준선(baseline) 역할을 합니다.
"""
import unittest
import json
import sqlite3
import os
import tempfile
import bcrypt
import shutil
import sys
from pathlib import Path

# archive/code/app.py 임포트
sys.path.insert(0, str(Path(__file__).parent))
import app as app_module
from app import app, get_db, close_db


class ArchiveServerCompleteTest(unittest.TestCase):
    """archive/code/app.py의 모든 기능을 테스트하는 완전한 테스트 스위트"""

    @classmethod
    def setUpClass(cls):
        """테스트 클래스 시작 전 한 번만 실행"""
        cls.original_db_path = app_module.DB_PATH

    def setUp(self):
        """각 테스트 시작 전 실행"""
        # 임시 DB 파일 생성
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.sqlite3')

        # 실제 운영 DB가 있다면 복사 (선택사항)
        real_db = Path(__file__).parent / 'db.sqlite3'
        if real_db.exists():
            # 임시 파일 닫고 복사
            os.close(self.db_fd)
            shutil.copy(real_db, self.db_path)
            # 다시 열기
            self.db_fd = os.open(self.db_path, os.O_RDONLY)

        # 앱 설정
        app.config['TESTING'] = True
        app_module.DB_PATH = self.db_path

        # 테스트 클라이언트 생성
        self.client = app.test_client()

        # DB 초기화 (실제 DB 없을 경우)
        if not real_db.exists():
            with app.app_context():
                self.init_test_db()

    def tearDown(self):
        """각 테스트 종료 후 실행"""
        # DB_PATH 복구
        app_module.DB_PATH = self.__class__.original_db_path

        try:
            os.close(self.db_fd)
        except:
            pass

        try:
            os.unlink(self.db_path)
        except:
            pass

    def init_test_db(self):
        """테스트용 DB 스키마 및 초기 데이터 생성"""
        db = get_db()

        # 테이블 생성
        db.executescript('''
            CREATE TABLE IF NOT EXISTS pc_info (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                machine_id TEXT UNIQUE NOT NULL,
                hostname TEXT,
                ip_address TEXT,
                mac_address TEXT,
                room_name TEXT,
                seat_number TEXT,
                is_online INTEGER DEFAULT 0,
                last_seen TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS pc_specs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pc_id INTEGER,
                cpu_model TEXT,
                cpu_cores INTEGER,
                cpu_threads INTEGER,
                ram_total INTEGER,
                disk_info TEXT,
                os_edition TEXT,
                os_version TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(pc_id) REFERENCES pc_info(id)
            );

            CREATE TABLE IF NOT EXISTS pc_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pc_id INTEGER,
                cpu_usage REAL,
                ram_used INTEGER,
                ram_usage_percent REAL,
                disk_usage TEXT,
                current_user TEXT,
                uptime INTEGER,
                processes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(pc_id) REFERENCES pc_info(id)
            );

            CREATE TABLE IF NOT EXISTS pc_command (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pc_id INTEGER,
                command_type TEXT NOT NULL,
                command_data TEXT,
                status TEXT DEFAULT 'pending',
                result TEXT,
                error_message TEXT,
                priority INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY(pc_id) REFERENCES pc_info(id)
            );

            CREATE TABLE IF NOT EXISTS seat_layout (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_name TEXT UNIQUE NOT NULL,
                rows INTEGER DEFAULT 5,
                cols INTEGER DEFAULT 8,
                description TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS seat_map (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_name TEXT,
                row INTEGER,
                col INTEGER,
                pc_id INTEGER,
                FOREIGN KEY(room_name) REFERENCES seat_layout(room_name) ON DELETE CASCADE,
                FOREIGN KEY(pc_id) REFERENCES pc_info(id)
            );

            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS client_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version TEXT NOT NULL,
                download_url TEXT,
                changelog TEXT,
                released_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')

        # 테스트용 관리자 계정 생성
        password_hash = bcrypt.hashpw(b"admin", bcrypt.gensalt()).decode('utf-8')
        db.execute('INSERT INTO admins (username, password_hash) VALUES (?, ?)', ('admin', password_hash))

        # 기본 실습실 생성
        db.execute("INSERT INTO seat_layout (room_name, rows, cols, is_active) VALUES ('1실습실', 5, 8, 1)")

        db.commit()

    def login_admin(self):
        """관리자 로그인 (세션 설정)"""
        with self.client.session_transaction() as sess:
            sess['admin'] = 'admin'

    # ==================== 클라이언트 API 테스트 ====================

    def test_01_client_register_success(self):
        """클라이언트 등록 - 정상 케이스"""
        data = {
            'machine_id': 'test-machine-001',
            'hostname': 'TEST-PC-001',
            'mac_address': '00:11:22:33:44:55',
            'ip_address': '192.168.1.100',
            'cpu_model': 'Intel Core i7-9700K',
            'cpu_cores': 8,
            'cpu_threads': 8,
            'ram_total': 16384,
            'disk_info': json.dumps({'C:': {'total': 500000, 'filesystem': 'NTFS'}}),
            'os_edition': 'Windows 10 Pro',
            'os_version': '10.0.19045'
        }

        response = self.client.post('/api/client/register',
                                   data=json.dumps(data),
                                   content_type='application/json')

        self.assertEqual(response.status_code, 200)
        result = json.loads(response.data)
        self.assertEqual(result['status'], 'success')
        self.assertIn('pc_id', result)
        self.assertIsInstance(result['pc_id'], int)

    def test_02_client_register_duplicate(self):
        """클라이언트 등록 - 중복 machine_id (업데이트)"""
        data = {
            'machine_id': 'test-machine-002',
            'hostname': 'TEST-PC-002',
            'mac_address': '00:11:22:33:44:66',
            'ip_address': '192.168.1.101'
        }

        # 첫 번째 등록
        response1 = self.client.post('/api/client/register',
                                    data=json.dumps(data),
                                    content_type='application/json')
        self.assertEqual(response1.status_code, 200)
        result1 = json.loads(response1.data)
        pc_id_1 = result1['pc_id']

        # 두 번째 등록 (같은 machine_id, 다른 hostname)
        data['hostname'] = 'TEST-PC-002-UPDATED'
        response2 = self.client.post('/api/client/register',
                                    data=json.dumps(data),
                                    content_type='application/json')
        self.assertEqual(response2.status_code, 200)
        result2 = json.loads(response2.data)
        pc_id_2 = result2['pc_id']

        # 같은 PC ID여야 함 (업데이트)
        self.assertEqual(pc_id_1, pc_id_2)
        self.assertEqual(result2['message'], '업데이트 완료')

    def test_03_client_register_missing_machine_id(self):
        """클라이언트 등록 - machine_id 누락"""
        data = {
            'hostname': 'TEST-PC-003',
            'ip_address': '192.168.1.102'
        }

        response = self.client.post('/api/client/register',
                                   data=json.dumps(data),
                                   content_type='application/json')

        self.assertEqual(response.status_code, 400)
        result = json.loads(response.data)
        self.assertEqual(result['status'], 'error')
        self.assertIn('machine_id', result['message'])

    def test_04_client_heartbeat_success(self):
        """클라이언트 하트비트 - 정상 케이스"""
        # 먼저 PC 등록
        self.test_01_client_register_success()

        data = {
            'machine_id': 'test-machine-001',
            'system_info': {
                'cpu_usage': 25.5,
                'ram_used': 8192,
                'ram_usage_percent': 50.0,
                'disk_usage': json.dumps({'C:': {'used': 250000, 'free': 250000}}),
                'current_user': 'admin',
                'uptime': 7200,
                'processes': json.dumps(['chrome.exe', 'python.exe'])
            }
        }

        response = self.client.post('/api/client/heartbeat',
                                   data=json.dumps(data),
                                   content_type='application/json')

        self.assertEqual(response.status_code, 200)
        result = json.loads(response.data)
        self.assertEqual(result['status'], 'success')

    def test_05_client_heartbeat_unregistered(self):
        """클라이언트 하트비트 - 미등록 PC"""
        data = {
            'machine_id': 'unregistered-machine',
            'system_info': {'cpu_usage': 10.0}
        }

        response = self.client.post('/api/client/heartbeat',
                                   data=json.dumps(data),
                                   content_type='application/json')

        self.assertEqual(response.status_code, 404)
        result = json.loads(response.data)
        self.assertEqual(result['status'], 'error')

    def test_06_client_command_polling_no_commands(self):
        """명령 폴링 - 대기 중인 명령 없음"""
        # PC 등록
        self.test_01_client_register_success()

        # 폴링 (timeout=1초)
        response = self.client.get('/api/client/command?machine_id=test-machine-001&timeout=1')

        self.assertEqual(response.status_code, 200)
        result = json.loads(response.data)
        self.assertIsNone(result['command_id'])
        self.assertIsNone(result['command_type'])

    def test_07_client_command_polling_with_command(self):
        """명령 폴링 - 대기 중인 명령 있음"""
        # PC 등록
        self.test_01_client_register_success()

        # 명령 추가 (DB 직접 조작)
        with app.app_context():
            db = get_db()
            pc = db.execute('SELECT id FROM pc_info WHERE machine_id=?', ('test-machine-001',)).fetchone()
            db.execute(
                "INSERT INTO pc_command (pc_id, command_type, command_data, status) VALUES (?, 'shutdown', '{}', 'pending')",
                (pc['id'],)
            )
            db.commit()

        # 폴링
        response = self.client.get('/api/client/command?machine_id=test-machine-001&timeout=1')

        self.assertEqual(response.status_code, 200)
        result = json.loads(response.data)
        self.assertIsNotNone(result['command_id'])
        self.assertEqual(result['command_type'], 'shutdown')

    def test_08_client_command_result_success(self):
        """명령 결과 보고 - 성공"""
        # 명령 폴링 먼저 (명령 생성됨)
        self.test_07_client_command_polling_with_command()

        # 명령 ID 가져오기
        with app.app_context():
            db = get_db()
            pc = db.execute('SELECT id FROM pc_info WHERE machine_id=?', ('test-machine-001',)).fetchone()
            cmd = db.execute('SELECT id FROM pc_command WHERE pc_id=?', (pc['id'],)).fetchone()
            cmd_id = cmd['id']

        # 결과 보고
        data = {
            'machine_id': 'test-machine-001',
            'command_id': cmd_id,
            'status': 'completed',
            'result': 'Shutdown initiated successfully'
        }

        response = self.client.post('/api/client/command/result',
                                   data=json.dumps(data),
                                   content_type='application/json')

        self.assertEqual(response.status_code, 200)
        result = json.loads(response.data)
        self.assertEqual(result['status'], 'success')

    def test_09_client_command_result_error(self):
        """명령 결과 보고 - 오류"""
        # PC 등록 및 명령 추가
        self.test_01_client_register_success()

        with app.app_context():
            db = get_db()
            pc = db.execute('SELECT id FROM pc_info WHERE machine_id=?', ('test-machine-001',)).fetchone()
            db.execute(
                "INSERT INTO pc_command (pc_id, command_type, command_data, status) VALUES (?, 'execute', ?, 'pending')",
                (pc['id'], json.dumps({'command': 'invalid_command'}))
            )
            db.commit()
            cmd = db.execute('SELECT id FROM pc_command WHERE pc_id=? ORDER BY created_at DESC LIMIT 1', (pc['id'],)).fetchone()
            cmd_id = cmd['id']

        # 오류 결과 보고
        data = {
            'machine_id': 'test-machine-001',
            'command_id': cmd_id,
            'status': 'error',
            'error_message': 'Command not found'
        }

        response = self.client.post('/api/client/command/result',
                                   data=json.dumps(data),
                                   content_type='application/json')

        self.assertEqual(response.status_code, 200)

    def test_10_client_version_get(self):
        """클라이언트 버전 조회"""
        response = self.client.get('/api/client/version')

        self.assertEqual(response.status_code, 200)
        result = json.loads(response.data)
        self.assertEqual(result['status'], 'success')
        self.assertIn('version', result)
        # 초기 상태에서는 1.0.0 또는 DB에 저장된 버전
        self.assertIsNotNone(result['version'])

    # ==================== 관리자 API 테스트 ====================

    def test_11_admin_pcs_list(self):
        """PC 목록 조회 (관리자)"""
        # PC 등록
        self.test_01_client_register_success()

        response = self.client.get('/api/pcs')

        self.assertEqual(response.status_code, 200)
        result = json.loads(response.data)
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        # 첫 번째 PC 확인
        pc = result[0]
        self.assertIn('id', pc)
        self.assertIn('hostname', pc)

    def test_12_admin_pc_detail(self):
        """PC 상세 정보 조회"""
        # PC 등록
        self.test_01_client_register_success()

        # PC ID 가져오기
        with app.app_context():
            db = get_db()
            pc = db.execute('SELECT id FROM pc_info WHERE machine_id=?', ('test-machine-001',)).fetchone()
            pc_id = pc['id']

        response = self.client.get(f'/api/pc/{pc_id}')

        self.assertEqual(response.status_code, 200)
        result = json.loads(response.data)
        self.assertEqual(result['id'], pc_id)
        self.assertEqual(result['machine_id'], 'test-machine-001')

    def test_13_admin_pc_detail_not_found(self):
        """PC 상세 정보 조회 - 존재하지 않는 PC"""
        response = self.client.get('/api/pc/99999')

        self.assertEqual(response.status_code, 404)
        result = json.loads(response.data)
        self.assertIn('error', result)

    def test_14_admin_send_command_no_auth(self):
        """명령 전송 - 인증 없음"""
        # PC 등록
        self.test_01_client_register_success()

        with app.app_context():
            db = get_db()
            pc = db.execute('SELECT id FROM pc_info WHERE machine_id=?', ('test-machine-001',)).fetchone()
            pc_id = pc['id']

        data = {'type': 'shutdown', 'data': {}}
        response = self.client.post(f'/api/pc/{pc_id}/command',
                                   data=json.dumps(data),
                                   content_type='application/json')

        self.assertEqual(response.status_code, 401)

    def test_15_admin_send_command_with_auth(self):
        """명령 전송 - 인증 있음"""
        # 로그인
        self.login_admin()

        # PC 등록
        self.test_01_client_register_success()

        with app.app_context():
            db = get_db()
            pc = db.execute('SELECT id FROM pc_info WHERE machine_id=?', ('test-machine-001',)).fetchone()
            pc_id = pc['id']

        data = {'type': 'shutdown', 'data': {}}
        response = self.client.post(f'/api/pc/{pc_id}/command',
                                   data=json.dumps(data),
                                   content_type='application/json')

        self.assertEqual(response.status_code, 200)
        result = json.loads(response.data)
        self.assertEqual(result['status'], 'success')

    def test_16_admin_shutdown_command(self):
        """PC 종료 명령"""
        self.login_admin()
        self.test_01_client_register_success()

        with app.app_context():
            db = get_db()
            pc = db.execute('SELECT id FROM pc_info WHERE machine_id=?', ('test-machine-001',)).fetchone()
            pc_id = pc['id']

        response = self.client.post(f'/api/pc/{pc_id}/shutdown')

        self.assertEqual(response.status_code, 200)
        result = json.loads(response.data)
        self.assertEqual(result['status'], 'success')

    def test_17_admin_reboot_command(self):
        """PC 재시작 명령"""
        self.login_admin()
        self.test_01_client_register_success()

        with app.app_context():
            db = get_db()
            pc = db.execute('SELECT id FROM pc_info WHERE machine_id=?', ('test-machine-001',)).fetchone()
            pc_id = pc['id']

        response = self.client.post(f'/api/pc/{pc_id}/reboot')

        self.assertEqual(response.status_code, 200)
        result = json.loads(response.data)
        self.assertEqual(result['status'], 'success')

    def test_18_admin_create_account(self):
        """Windows 계정 생성 명령"""
        self.login_admin()
        self.test_01_client_register_success()

        with app.app_context():
            db = get_db()
            pc = db.execute('SELECT id FROM pc_info WHERE machine_id=?', ('test-machine-001',)).fetchone()
            pc_id = pc['id']

        data = {
            'username': 'testuser',
            'password': 'testpass123',
            'full_name': 'Test User'
        }

        response = self.client.post(f'/api/pc/{pc_id}/account/create',
                                   data=json.dumps(data),
                                   content_type='application/json')

        self.assertEqual(response.status_code, 200)
        result = json.loads(response.data)
        self.assertEqual(result['status'], 'success')

    def test_19_admin_delete_account(self):
        """Windows 계정 삭제 명령"""
        self.login_admin()
        self.test_01_client_register_success()

        with app.app_context():
            db = get_db()
            pc = db.execute('SELECT id FROM pc_info WHERE machine_id=?', ('test-machine-001',)).fetchone()
            pc_id = pc['id']

        data = {'username': 'testuser'}

        response = self.client.post(f'/api/pc/{pc_id}/account/delete',
                                   data=json.dumps(data),
                                   content_type='application/json')

        self.assertEqual(response.status_code, 200)
        result = json.loads(response.data)
        self.assertEqual(result['status'], 'success')

    def test_20_admin_change_password(self):
        """Windows 계정 비밀번호 변경 명령"""
        self.login_admin()
        self.test_01_client_register_success()

        with app.app_context():
            db = get_db()
            pc = db.execute('SELECT id FROM pc_info WHERE machine_id=?', ('test-machine-001',)).fetchone()
            pc_id = pc['id']

        data = {
            'username': 'testuser',
            'new_password': 'newpass456'
        }

        response = self.client.post(f'/api/pc/{pc_id}/account/password',
                                   data=json.dumps(data),
                                   content_type='application/json')

        self.assertEqual(response.status_code, 200)
        result = json.loads(response.data)
        self.assertEqual(result['status'], 'success')

    def test_21_room_create(self):
        """실습실 생성"""
        self.login_admin()

        data = {
            'room_name': '테스트실',
            'rows': 6,
            'cols': 10,
            'description': '테스트용 실습실'
        }

        response = self.client.post('/api/rooms',
                                   data=json.dumps(data),
                                   content_type='application/json')

        self.assertEqual(response.status_code, 200)
        result = json.loads(response.data)
        self.assertEqual(result['status'], 'success')
        self.assertIn('room_id', result)

    def test_22_room_list(self):
        """실습실 목록 조회"""
        self.login_admin()

        response = self.client.get('/api/rooms')

        self.assertEqual(response.status_code, 200)
        result = json.loads(response.data)
        self.assertIn('total', result)
        self.assertIn('rooms', result)

    def test_23_room_update(self):
        """실습실 정보 수정"""
        self.login_admin()

        # 먼저 실습실 생성
        self.test_21_room_create()

        # 실습실 ID 가져오기
        with app.app_context():
            db = get_db()
            room = db.execute('SELECT id FROM seat_layout WHERE room_name=?', ('테스트실',)).fetchone()
            room_id = room['id']

        data = {
            'room_name': '테스트실_수정',
            'description': '수정된 설명'
        }

        response = self.client.put(f'/api/rooms/{room_id}',
                                  data=json.dumps(data),
                                  content_type='application/json')

        self.assertEqual(response.status_code, 200)
        result = json.loads(response.data)
        self.assertEqual(result['status'], 'success')

    def test_24_room_delete(self):
        """실습실 삭제"""
        self.login_admin()

        # 실습실 생성
        self.test_21_room_create()

        # 실습실 ID 가져오기
        with app.app_context():
            db = get_db()
            room = db.execute('SELECT id FROM seat_layout WHERE room_name=?', ('테스트실',)).fetchone()
            room_id = room['id']

        response = self.client.delete(f'/api/rooms/{room_id}')

        self.assertEqual(response.status_code, 200)
        result = json.loads(response.data)
        self.assertEqual(result['status'], 'success')

    def test_25_pc_delete(self):
        """PC 삭제"""
        self.login_admin()
        self.test_01_client_register_success()

        with app.app_context():
            db = get_db()
            pc = db.execute('SELECT id FROM pc_info WHERE machine_id=?', ('test-machine-001',)).fetchone()
            pc_id = pc['id']

        response = self.client.delete(f'/api/pc/{pc_id}')

        self.assertEqual(response.status_code, 200)
        result = json.loads(response.data)
        self.assertEqual(result['status'], 'success')

    def test_26_bulk_command(self):
        """일괄 명령 전송"""
        self.login_admin()

        # PC 2대 등록
        self.test_01_client_register_success()

        data2 = {
            'machine_id': 'test-machine-002',
            'hostname': 'TEST-PC-002',
            'ip_address': '192.168.1.101'
        }
        self.client.post('/api/client/register',
                        data=json.dumps(data2),
                        content_type='application/json')

        # PC ID들 가져오기
        with app.app_context():
            db = get_db()
            pcs = db.execute('SELECT id FROM pc_info').fetchall()
            pc_ids = [pc['id'] for pc in pcs]

        data = {
            'pc_ids': pc_ids,
            'command_type': 'shutdown',
            'command_data': {}
        }

        response = self.client.post('/api/pcs/bulk-command',
                                   data=json.dumps(data),
                                   content_type='application/json')

        self.assertEqual(response.status_code, 200)
        result = json.loads(response.data)
        self.assertEqual(result['success'], len(pc_ids))

    def test_27_clear_pc_commands(self):
        """PC 명령 초기화"""
        self.login_admin()
        self.test_01_client_register_success()

        with app.app_context():
            db = get_db()
            pc = db.execute('SELECT id FROM pc_info WHERE machine_id=?', ('test-machine-001',)).fetchone()
            pc_id = pc['id']

        response = self.client.delete(f'/api/pc/{pc_id}/commands/clear')

        self.assertEqual(response.status_code, 200)
        result = json.loads(response.data)
        self.assertEqual(result['status'], 'success')

    def test_28_pending_commands(self):
        """대기 중인 명령 조회"""
        self.login_admin()

        response = self.client.get('/api/commands/pending')

        self.assertEqual(response.status_code, 200)
        result = json.loads(response.data)
        self.assertIn('total', result)
        self.assertIn('commands', result)

    # ==================== 웹 페이지 테스트 ====================

    def test_29_index_page(self):
        """메인 페이지 접근"""
        response = self.client.get('/')

        # 리다이렉트 또는 200 OK
        self.assertIn(response.status_code, [200, 302])

    def test_30_login_page(self):
        """로그인 페이지 접근"""
        response = self.client.get('/login')

        self.assertEqual(response.status_code, 200)

    def test_31_login_success(self):
        """로그인 성공"""
        data = {
            'username': 'admin',
            'password': 'admin'
        }

        response = self.client.post('/login',
                                   data=data,
                                   follow_redirects=False)

        # 로그인 성공 시 리다이렉트
        self.assertEqual(response.status_code, 302)

    def test_32_logout(self):
        """로그아웃"""
        self.login_admin()

        response = self.client.post('/logout', follow_redirects=False)

        self.assertEqual(response.status_code, 302)


if __name__ == '__main__':
    # 테스트 실행
    unittest.main(verbosity=2)
