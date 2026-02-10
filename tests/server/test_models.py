"""
서버 모델 단위 테스트
"""
import pytest
from models import PCModel, CommandModel, AdminModel


class TestPCModel:
    """PCModel 테스트"""

    def test_get_by_id_not_found(self, app):
        """존재하지 않는 PC 조회"""
        result = PCModel.get_by_id(99999)
        assert result is None

    def test_register_pc(self, app):
        """PC 등록"""
        pc_id = PCModel.register(
            machine_id='TEST-PC-001',
            hostname='test-pc',
            mac_address='AA:BB:CC:DD:EE:FF',
            cpu_model='Intel Core i5',
            cpu_cores=4,
            cpu_threads=8,
            ram_total=16.0
        )
        assert pc_id is not None
        assert isinstance(pc_id, int)

    def test_get_all(self, app):
        """모든 PC 조회"""
        # PC 등록
        PCModel.register(
            machine_id='TEST-PC-002',
            hostname='test-pc-2',
            mac_address='FF:EE:DD:CC:BB:AA'
        )

        # 조회
        pcs = PCModel.get_all()
        assert isinstance(pcs, list)


class TestCommandModel:
    """CommandModel 테스트"""

    def test_create_command(self, app):
        """명령 생성"""
        # 테스트용 PC 먼저 등록
        pc_id = PCModel.register(
            machine_id='TEST-PC-CMD',
            hostname='test-pc-cmd',
            mac_address='11:22:33:44:55:66'
        )

        # 명령 생성
        cmd_id = CommandModel.create(
            pc_id=pc_id,
            command_type='shutdown',
            admin_username='admin'
        )
        assert cmd_id is not None

    def test_get_pending_for_pc(self, app):
        """대기 중인 명령 조회"""
        # PC 등록
        pc_id = PCModel.register(
            machine_id='TEST-PC-PENDING',
            hostname='test-pc-pending',
            mac_address='77:88:99:AA:BB:CC'
        )

        # 명령 생성
        CommandModel.create(pc_id=pc_id, command_type='reboot')

        # 조회
        commands = CommandModel.get_pending_for_pc(pc_id)
        assert len(commands) > 0


class TestAdminModel:
    """AdminModel 테스트"""

    def test_create_admin(self, app):
        """관리자 생성"""
        admin_id = AdminModel.create(
            username='test_admin',
            password='testpass123',
            email='test@example.com'
        )
        assert admin_id is not None

    def test_authenticate_admin(self, app):
        """관리자 인증"""
        # 관리자 생성
        AdminModel.create(
            username='auth_test',
            password='correct_password'
        )

        # 인증 시도
        admin = AdminModel.authenticate('auth_test', 'correct_password')
        assert admin is not None
        assert admin['username'] == 'auth_test'

    def test_authenticate_wrong_password(self, app):
        """잘못된 비밀번호 인증"""
        AdminModel.create(
            username='wrong_pass_test',
            password='correct_password'
        )

        admin = AdminModel.authenticate('wrong_pass_test', 'wrong_password')
        assert admin is None


class TestPCModelV071BugFixes:
    """v0.7.1 버그 수정 테스트 (disk_info_parsed, 프로세스 표시)"""

    def test_get_with_status_disk_info_parsed(self, app):
        """disk_info_parsed 필드가 정상 생성되는지 테스트"""
        # PC 등록 (정적 정보)
        disk_info = {
            "C:\\": {
                "total_gb": 500.0,
                "fstype": "NTFS",
                "mountpoint": "C:\\"
            }
        }

        pc_id = PCModel.register(
            machine_id='TEST-DISK-PARSED-001',
            hostname='test-disk-pc',
            mac_address='AA:BB:CC:DD:EE:F1',
            disk_info=disk_info
        )

        # 하트비트 전송 (동적 정보)
        disk_usage = {
            "C:\\": {
                "used_gb": 200.0,
                "free_gb": 300.0,
                "percent": 40.0
            }
        }

        PCModel.update_heartbeat(
            pc_id=pc_id,
            cpu_usage=50.0,
            ram_used=8.0,
            ram_usage_percent=50.0,
            disk_usage=disk_usage
        )

        # get_with_status로 조회
        pc = PCModel.get_with_status(pc_id)

        # disk_info_parsed 필드 확인
        assert pc is not None
        assert 'disk_info_parsed' in pc
        assert 'C:\\' in pc['disk_info_parsed']

        # 병합된 데이터 확인
        c_drive = pc['disk_info_parsed']['C:\\']
        assert c_drive['total_gb'] == 500.0
        assert c_drive['used_gb'] == 200.0
        assert c_drive['free_gb'] == 300.0
        assert c_drive['percent'] == 40.0

    def test_get_with_status_all_fields(self, app):
        """get_with_status가 모든 필수 필드를 포함하는지 테스트"""
        pc_id = PCModel.register(
            machine_id='TEST-ALL-FIELDS-001',
            hostname='test-fields-pc',
            mac_address='AA:BB:CC:DD:EE:F2'
        )

        # 하트비트 전송
        PCModel.update_heartbeat(
            pc_id=pc_id,
            cpu_usage=45.5,
            ram_used=8.0,
            ram_usage_percent=50.0,
            disk_usage={'C:\\': {'used_gb': 200.0, 'free_gb': 300.0}},
            current_user='student',
            uptime=7200,
            processes=['chrome.exe', 'vscode.exe']
        )

        # 조회
        pc = PCModel.get_with_status(pc_id)

        # 필수 필드 확인
        assert 'cpu_usage' in pc
        assert 'ram_used' in pc
        assert 'ram_usage_percent' in pc
        assert 'disk_usage' in pc
        assert 'current_user' in pc
        assert 'uptime' in pc
        assert 'processes' in pc

        # 값 확인
        assert pc['cpu_usage'] == 45.5
        assert pc['ram_usage_percent'] == 50.0
        assert pc['current_user'] == 'student'
        assert pc['uptime'] == 7200

    def test_get_with_status_no_heartbeat_defaults(self, app):
        """하트비트 없을 때 기본값 확인"""
        pc_id = PCModel.register(
            machine_id='TEST-NO-HB-001',
            hostname='test-no-hb-pc',
            mac_address='AA:BB:CC:DD:EE:F3'
        )

        # 하트비트 없이 조회
        pc = PCModel.get_with_status(pc_id)

        # 기본값 확인
        assert pc['cpu_usage'] is None
        assert pc['ram_used'] == 0
        assert pc['ram_usage_percent'] == 0
        assert pc['disk_usage'] == '{}'
        assert pc['current_user'] is None
        assert pc['uptime'] == 0
        assert pc['processes'] == '[]'



