"""
명령 서비스 (비즈니스 로직)
명령 처리와 관련된 비즈니스 로직을 캡슐화
"""
from models import CommandModel, PCModel
from typing import Dict, List, Any
import json


class CommandService:
    """명령 처리 서비스"""

    @staticmethod
    def send_shutdown_command(pc_id: int, admin_username: str = None) -> int:
        """종료 명령 전송"""
        if not PCModel.get_by_id(pc_id):
            raise ValueError("PC not found")

        return CommandModel.create(
            pc_id=pc_id,
            command_type='shutdown',
            admin_username=admin_username
        )

    @staticmethod
    def send_reboot_command(pc_id: int, admin_username: str = None) -> int:
        """재시작 명령 전송"""
        if not PCModel.get_by_id(pc_id):
            raise ValueError("PC not found")

        return CommandModel.create(
            pc_id=pc_id,
            command_type='reboot',
            admin_username=admin_username
        )

    @staticmethod
    def send_custom_command(pc_id: int, command: str, admin_username: str = None) -> int:
        """커스텀 명령 전송"""
        if not PCModel.get_by_id(pc_id):
            raise ValueError("PC not found")

        return CommandModel.create(
            pc_id=pc_id,
            command_type='execute',
            command_data={'command': command},
            admin_username=admin_username
        )

    @staticmethod
    def send_install_command(pc_id: int, app_name: str, admin_username: str = None) -> int:
        """프로그램 설치 명령 전송"""
        if not PCModel.get_by_id(pc_id):
            raise ValueError("PC not found")

        return CommandModel.create(
            pc_id=pc_id,
            command_type='install',
            command_data={'app_name': app_name},
            admin_username=admin_username
        )

    @staticmethod
    def send_user_create_command(pc_id: int, username: str, password: str,
                                  admin_username: str = None) -> int:
        """사용자 생성 명령 전송"""
        if not PCModel.get_by_id(pc_id):
            raise ValueError("PC not found")

        return CommandModel.create(
            pc_id=pc_id,
            command_type='create_user',
            command_data={'username': username, 'password': password},
            admin_username=admin_username
        )

    @staticmethod
    def send_user_delete_command(pc_id: int, username: str,
                                  admin_username: str = None) -> int:
        """사용자 삭제 명령 전송"""
        if not PCModel.get_by_id(pc_id):
            raise ValueError("PC not found")

        return CommandModel.create(
            pc_id=pc_id,
            command_type='delete_user',
            command_data={'username': username},
            admin_username=admin_username
        )

    @staticmethod
    def send_batch_command(pc_ids: List[int], command_type: str, command_data: Dict = None,
                          admin_username: str = None) -> List[int]:
        """일괄 명령 전송"""
        command_ids = []
        for pc_id in pc_ids:
            if not PCModel.get_by_id(pc_id):
                continue

            cmd_id = CommandModel.create(
                pc_id=pc_id,
                command_type=command_type,
                command_data=command_data,
                admin_username=admin_username
            )
            command_ids.append(cmd_id)

        return command_ids

    @staticmethod
    def get_pending_commands(pc_id: int) -> List[Dict[str, Any]]:
        """대기 중인 명령 조회"""
        commands = CommandModel.get_pending_for_pc(pc_id)
        result = []
        for cmd in commands:
            result.append({
                'id': cmd['id'],
                'type': cmd['command_type'],
                'data': json.loads(cmd['command_data']) if cmd['command_data'] else {},
                'priority': cmd['priority'],
                'timeout': cmd['timeout_seconds']
            })
        return result

    @staticmethod
    def get_command_status(command_id: int) -> Dict[str, Any]:
        """명령 상태 조회"""
        cmd = CommandModel.get_by_id(command_id)
        if not cmd:
            return None

        return {
            'id': cmd['id'],
            'pc_id': cmd['pc_id'],
            'type': cmd['command_type'],
            'status': cmd['status'],
            'result': cmd['result'],
            'error': cmd['error_message'],
            'retry_count': cmd['retry_count'],
            'max_retries': cmd['max_retries'],
            'created_at': cmd['created_at'],
            'started_at': cmd['started_at'],
            'completed_at': cmd['completed_at']
        }

    @staticmethod
    def get_recent_commands(limit: int = 100) -> List[Dict[str, Any]]:
        """최근 명령 조회"""
        return CommandModel.get_recent(limit)

    @staticmethod
    def get_command_statistics() -> Dict[str, int]:
        """명령 통계"""
        return CommandModel.get_statistics()

    @staticmethod
    def cleanup_old_commands(days: int = 30) -> int:
        """오래된 명령 정리"""
        return CommandModel.cleanup_old(days)

    @staticmethod
    def retry_failed_command(command_id: int) -> bool:
        """실패한 명령 재시도"""
        cmd = CommandModel.get_by_id(command_id)
        if not cmd:
            return False

        if cmd['status'] not in ['error', 'timeout']:
            return False

        return CommandModel.increment_retry(command_id)

