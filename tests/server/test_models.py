"""
서버 모델 단위 테스트
"""
import pytest
from server.models import PCModel, CommandModel, AdminModel


class TestPCModel:
    """PCModel 테스트"""

    def test_get_by_id_not_found(self):
        """존재하지 않는 PC 조회"""
        result = PCModel.get_by_id(99999)
        assert result is None

    def test_register_pc(self):
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

    def test_get_all(self):
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

    def test_create_command(self):
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

    def test_get_pending_for_pc(self):
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

    def test_create_admin(self):
        """관리자 생성"""
        admin_id = AdminModel.create(
            username='test_admin',
            password='testpass123',
            email='test@example.com'
        )
        assert admin_id is not None

    def test_authenticate_admin(self):
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

    def test_authenticate_wrong_password(self):
        """잘못된 비밀번호 인증"""
        AdminModel.create(
            username='wrong_pass_test',
            password='correct_password'
        )

        admin = AdminModel.authenticate('wrong_pass_test', 'wrong_password')
        assert admin is None

