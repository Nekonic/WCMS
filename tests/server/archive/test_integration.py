import unittest
import json
import sqlite3
import os
import tempfile
import bcrypt
import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'server'))

from app import create_app
from utils import get_db, close_db, init_db_manager

class IntegrationTestCase(unittest.TestCase):
    def setUp(self):
        """테스트 환경 설정"""
        # 임시 DB 파일 생성
        self.db_fd, self.db_path = tempfile.mkstemp()
        
        # 앱 생성 (테스트 모드)
        # 'test' 모드를 사용하면 config.py의 TestConfig가 로드됨 (:memory:)
        self.app = create_app('test')
        self.app.config['DB_PATH'] = self.db_path
        
        # DB 매니저를 임시 파일로 재초기화 (create_app에서 초기화된 것을 덮어씀)
        # 이렇게 해야 전역 _db_manager가 이 테스트의 임시 파일을 가리킴
        init_db_manager(self.db_path)
        
        # 테스트 클라이언트 생성
        self.client = self.app.test_client()
        
        # DB 초기화
        with self.app.app_context():
            self.init_db()

    def tearDown(self):
        """테스트 환경 정리"""
        # DB 연결 닫기 (파일 삭제 전 필수)
        # app context가 종료되면서 close_db가 호출되지만, 명시적으로 닫아주는 것이 안전
        close_db()
        
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def init_db(self):
        """테스트용 DB 스키마 생성"""
        db = get_db()
        
        # PC 정보 테이블
        db.execute('''
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
            )
        ''')
        
        # PC 스펙 테이블
        db.execute('''
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
            )
        ''')
        
        # PC 상태 테이블
        db.execute('''
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
            )
        ''')
        
        # PC 명령 테이블 (리팩토링된 서버 코드 호환을 위해 컬럼 추가)
        db.execute('''
            CREATE TABLE IF NOT EXISTS pc_command (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pc_id INTEGER,
                command_type TEXT NOT NULL,
                command_data TEXT,
                status TEXT DEFAULT 'pending',
                result TEXT,
                error_message TEXT,
                priority INTEGER DEFAULT 0,
                admin_username TEXT,
                max_retries INTEGER DEFAULT 3,
                timeout_seconds INTEGER DEFAULT 300,
                retry_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY(pc_id) REFERENCES pc_info(id)
            )
        ''')
        
        # 좌석 배치 레이아웃 테이블
        db.execute('''
            CREATE TABLE IF NOT EXISTS seat_layout (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_name TEXT UNIQUE NOT NULL,
                rows INTEGER DEFAULT 5,
                cols INTEGER DEFAULT 8,
                description TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 좌석 매핑 테이블
        db.execute('''
            CREATE TABLE IF NOT EXISTS seat_map (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_name TEXT,
                row INTEGER,
                col INTEGER,
                pc_id INTEGER,
                FOREIGN KEY(room_name) REFERENCES seat_layout(room_name) ON DELETE CASCADE,
                FOREIGN KEY(pc_id) REFERENCES pc_info(id)
            )
        ''')
        
        # 관리자 테이블
        db.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 클라이언트 버전 테이블
        db.execute('''
            CREATE TABLE IF NOT EXISTS client_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version TEXT NOT NULL,
                download_url TEXT,
                changelog TEXT,
                released_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 테스트용 관리자 계정 생성
        password_hash = bcrypt.hashpw(b"admin", bcrypt.gensalt()).decode('utf-8')
        db.execute('INSERT INTO admins (username, password_hash) VALUES (?, ?)', ('admin', password_hash))
        
        db.commit()

    def _create_test_pin(self):
        """테스트용 PIN 생성 (v0.8.0)"""
        with self.app.app_context():
            from models.registration import RegistrationTokenModel
            token = RegistrationTokenModel.create('test_admin', 'multi', 3600)
            return token['token']

    def login_admin(self):
        """관리자 세션 설정"""
        with self.client.session_transaction() as sess:
            sess['username'] = 'admin'
            sess['admin'] = True # 레거시 호환

    # ==================== 클라이언트 API 테스트 ====================

    def test_client_register(self):
        """클라이언트 등록 테스트"""
        pin = self._create_test_pin()  # v0.8.0: PIN 필수
        data = {
            'machine_id': 'test-machine-id',
            'pin': pin,  # v0.8.0: PIN 추가
            'hostname': 'TEST-PC',
            'mac_address': '00:11:22:33:44:55',
            'ip_address': '192.168.1.100',
            'cpu_model': 'Intel Core i7',
            'cpu_cores': 4,
            'ram_total': 16384,
            'os_edition': 'Windows 10 Pro'
        }
        
        response = self.client.post('/api/client/register', 
                                   data=json.dumps(data),
                                   content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertIn('pc_id', data)
        
        # DB 확인
        with self.app.app_context():
            db = get_db()
            pc = db.execute('SELECT * FROM pc_info WHERE machine_id = ?', ('test-machine-id',)).fetchone()
            self.assertIsNotNone(pc)
            self.assertEqual(pc['hostname'], 'TEST-PC')

    def test_client_heartbeat(self):
        """클라이언트 하트비트 테스트"""
        # 먼저 PC 등록
        self.test_client_register()
        
        data = {
            'machine_id': 'test-machine-id',
            'system_info': {
                'cpu_usage': 15.5,
                'ram_used': 8192,
                'ram_usage_percent': 50.0,
                'uptime': 3600,
                'current_user': 'admin'
            }
        }
        
        response = self.client.post('/api/client/heartbeat',
                                   data=json.dumps(data),
                                   content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        
        # DB 확인
        with self.app.app_context():
            db = get_db()
            pc = db.execute('SELECT * FROM pc_info WHERE machine_id = ?', ('test-machine-id',)).fetchone()
            self.assertEqual(pc['is_online'], 1)
            
            status = db.execute('SELECT * FROM pc_status WHERE pc_id = ? ORDER BY created_at DESC LIMIT 1', (pc['id'],)).fetchone()
            self.assertIsNotNone(status)
            self.assertEqual(status['cpu_usage'], 15.5)

    def test_command_polling(self):
        """명령 폴링 테스트"""
        # PC 등록
        self.test_client_register()
        
        # 명령 추가 (DB 직접 조작)
        with self.app.app_context():
            db = get_db()
            pc = db.execute('SELECT id FROM pc_info WHERE machine_id = ?', ('test-machine-id',)).fetchone()
            db.execute("INSERT INTO pc_command (pc_id, command_type, command_data, status) VALUES (?, ?, ?, 'pending')",
                      (pc['id'], 'shutdown', '{}'))
            db.commit()
            
        # 폴링 요청
        response = self.client.get('/api/client/command?machine_id=test-machine-id&timeout=1')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['command_type'], 'shutdown')
        self.assertIsNotNone(data['command_id'])

    def test_command_result(self):
        """명령 결과 보고 테스트"""
        # PC 등록 및 명령 추가
        self.test_command_polling()
        
        # 명령 ID 가져오기
        with self.app.app_context():
            db = get_db()
            pc = db.execute('SELECT id FROM pc_info WHERE machine_id = ?', ('test-machine-id',)).fetchone()
            cmd = db.execute('SELECT id FROM pc_command WHERE pc_id = ?', (pc['id'],)).fetchone()
            cmd_id = cmd['id']
            
        data = {
            'machine_id': 'test-machine-id',
            'command_id': cmd_id,
            'status': 'completed',
            'result': 'Success'
        }
        
        response = self.client.post('/api/client/command/result',
                                   data=json.dumps(data),
                                   content_type='application/json')
                                   
        self.assertEqual(response.status_code, 200)
        
        # DB 확인
        with self.app.app_context():
            db = get_db()
            cmd = db.execute('SELECT * FROM pc_command WHERE id = ?', (cmd_id,)).fetchone()
            self.assertEqual(cmd['status'], 'completed')
            self.assertEqual(cmd['result'], 'Success')

    def test_client_version(self):
        """클라이언트 버전 확인 테스트"""
        # 초기 상태 (버전 정보 없음)
        response = self.client.get('/api/client/version')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['version'], '1.0.0')

        # 버전 업데이트 (인증 필요)
        update_data = {
            'version': '1.1.0',
            'download_url': 'http://example.com/client.exe',
            'changelog': 'New features'
        }
        # 인증 토큰 없이 요청
        response = self.client.post('/api/client/version', 
                                   data=json.dumps(update_data),
                                   content_type='application/json')
        self.assertEqual(response.status_code, 401)

        # 인증 토큰 포함 요청
        # app.py에서 os.environ.get('UPDATE_TOKEN', 'default-secret-token') 사용
        headers = {'Authorization': 'Bearer default-secret-token'}
        response = self.client.post('/api/client/version', 
                                   data=json.dumps(update_data),
                                   content_type='application/json',
                                   headers=headers)
        self.assertEqual(response.status_code, 200)

        # 업데이트 후 확인
        response = self.client.get('/api/client/version')
        data = json.loads(response.data)
        self.assertEqual(data['version'], '1.1.0')

    # ==================== 관리자 API 테스트 ====================

    def test_admin_pcs_list(self):
        """관리자 PC 목록 조회 테스트"""
        self.test_client_register() # PC 1대 등록
        
        # 로그인 전
        response = self.client.get('/api/pcs')
        # app.py의 /api/pcs는 @require_admin이 없음 (코드 확인 결과)
        # 하지만 문서에는 인증 필요라고 되어 있음. app.py 코드를 따름.
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['hostname'], 'TEST-PC')

    def test_admin_pc_detail(self):
        """관리자 PC 상세 조회 테스트"""
        self.test_client_register()
        
        with self.app.app_context():
            db = get_db()
            pc = db.execute('SELECT id FROM pc_info').fetchone()
            pc_id = pc['id']

        response = self.client.get(f'/api/pc/{pc_id}')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['hostname'], 'TEST-PC')

    def test_admin_send_command(self):
        """관리자 명령 전송 테스트"""
        self.test_client_register()
        self.login_admin() # 관리자 로그인
        
        with self.app.app_context():
            db = get_db()
            pc = db.execute('SELECT id FROM pc_info').fetchone()
            pc_id = pc['id']

        # 일반 명령
        cmd_data = {'type': 'execute', 'data': {'command': 'dir'}}
        response = self.client.post(f'/api/pc/{pc_id}/command',
                                   data=json.dumps(cmd_data),
                                   content_type='application/json')
        self.assertEqual(response.status_code, 200)

        # 종료 명령
        response = self.client.post(f'/api/pc/{pc_id}/shutdown')
        self.assertEqual(response.status_code, 200)

        # DB 확인
        with self.app.app_context():
            db = get_db()
            cmds = db.execute('SELECT * FROM pc_command WHERE pc_id = ?', (pc_id,)).fetchall()
            self.assertEqual(len(cmds), 2)

    def test_admin_room_management(self):
        """실습실 관리 테스트"""
        self.login_admin()

        # 실습실 생성
        room_data = {'room_name': 'New Room', 'rows': 5, 'cols': 6}
        response = self.client.post('/api/rooms',
                                   data=json.dumps(room_data),
                                   content_type='application/json')
        self.assertEqual(response.status_code, 200)
        
        # 목록 조회
        response = self.client.get('/api/rooms')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['total'], 1)
        self.assertEqual(data['rooms'][0]['room_name'], 'New Room')

        # 실습실 수정
        with self.app.app_context():
            db = get_db()
            room = db.execute('SELECT id FROM seat_layout').fetchone()
            room_id = room['id']

        update_data = {'room_name': 'Updated Room'}
        response = self.client.put(f'/api/rooms/{room_id}',
                                  data=json.dumps(update_data),
                                  content_type='application/json')
        self.assertEqual(response.status_code, 200)

        # 실습실 삭제
        response = self.client.delete(f'/api/rooms/{room_id}')
        self.assertEqual(response.status_code, 200)
        
        # 삭제 확인
        response = self.client.get('/api/rooms')
        data = json.loads(response.data)
        self.assertEqual(data['total'], 0)

    def test_admin_pc_delete(self):
        """PC 삭제 테스트"""
        self.test_client_register()
        self.login_admin()
        
        with self.app.app_context():
            db = get_db()
            pc = db.execute('SELECT id FROM pc_info').fetchone()
            pc_id = pc['id']

        response = self.client.delete(f'/api/pc/{pc_id}')
        self.assertEqual(response.status_code, 200)
        
        # DB 확인
        with self.app.app_context():
            db = get_db()
            pc = db.execute('SELECT * FROM pc_info WHERE id = ?', (pc_id,)).fetchone()
            self.assertIsNone(pc)

if __name__ == '__main__':
    unittest.main()
