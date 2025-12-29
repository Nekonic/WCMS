"""
명령 모델 (Repository 패턴)
PC 명령 관련 데이터베이스 작업을 캡슐화
"""
import json
from typing import Optional, List, Dict, Any
from utils import get_db


class CommandModel:
    """명령 관리 모델"""

    @staticmethod
    def create(pc_id: int, command_type: str, command_data: Optional[Dict] = None,
               admin_username: Optional[str] = None, priority: int = 5,
               max_retries: int = 3, timeout_seconds: int = 300) -> int:
        """새로운 명령 생성"""
        db = get_db()
        command_data_str = json.dumps(command_data) if command_data else '{}'

        cursor = db.execute('''
            INSERT INTO pc_command (pc_id, admin_username, command_type, command_data, priority, status, max_retries, timeout_seconds)
            VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)
        ''', (pc_id, admin_username, command_type, command_data_str, priority, max_retries, timeout_seconds))

        db.commit()
        return cursor.lastrowid

    @staticmethod
    def get_by_id(command_id: int) -> Optional[Dict[str, Any]]:
        """명령 ID로 조회"""
        db = get_db()
        row = db.execute(
            'SELECT * FROM pc_command WHERE id=?',
            (command_id,)
        ).fetchone()
        return dict(row) if row else None

    @staticmethod
    def get_pending_for_pc(pc_id: int) -> List[Dict[str, Any]]:
        """특정 PC의 대기 중인 명령 조회"""
        db = get_db()
        rows = db.execute('''
            SELECT * FROM pc_command 
            WHERE pc_id=? AND status='pending' 
            ORDER BY priority ASC, created_at ASC
        ''', (pc_id,)).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def get_all_pending() -> List[Dict[str, Any]]:
        """모든 대기 중인 명령 조회"""
        db = get_db()
        rows = db.execute('''
            SELECT * FROM pc_command 
            WHERE status='pending' 
            ORDER BY priority ASC, created_at ASC
        ''').fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def start_execution(command_id: int) -> bool:
        """명령 실행 시작"""
        try:
            db = get_db()
            db.execute('''
                UPDATE pc_command 
                SET status='executing', started_at=CURRENT_TIMESTAMP 
                WHERE id=?
            ''', (command_id,))
            db.commit()
            return True
        except Exception:
            return False

    @staticmethod
    def complete(command_id: int, result: str) -> bool:
        """명령 완료"""
        try:
            db = get_db()
            db.execute('''
                UPDATE pc_command 
                SET status='completed', result=?, completed_at=CURRENT_TIMESTAMP 
                WHERE id=?
            ''', (result, command_id))
            db.commit()
            return True
        except Exception:
            return False

    @staticmethod
    def set_error(command_id: int, error_message: str) -> bool:
        """명령 에러 설정"""
        try:
            db = get_db()
            db.execute('''
                UPDATE pc_command 
                SET status='error', error_message=?, completed_at=CURRENT_TIMESTAMP 
                WHERE id=?
            ''', (error_message, command_id))
            db.commit()
            return True
        except Exception:
            return False

    @staticmethod
    def set_timeout(command_id: int) -> bool:
        """명령 타임아웃 설정"""
        try:
            db = get_db()
            db.execute('''
                UPDATE pc_command 
                SET status='timeout', error_message='Command execution timeout', completed_at=CURRENT_TIMESTAMP 
                WHERE id=?
            ''', (command_id,))
            db.commit()
            return True
        except Exception:
            return False

    @staticmethod
    def increment_retry(command_id: int) -> bool:
        """재시도 횟수 증가"""
        try:
            db = get_db()
            command = CommandModel.get_by_id(command_id)
            if not command:
                return False

            retry_count = command.get('retry_count', 0) + 1
            max_retries = command.get('max_retries', 3)

            if retry_count >= max_retries:
                # 최대 재시도 횟수 초과
                db.execute('''
                    UPDATE pc_command 
                    SET status='error', error_message='Max retries exceeded', retry_count=?, completed_at=CURRENT_TIMESTAMP 
                    WHERE id=?
                ''', (retry_count, command_id))
            else:
                # 재시도
                db.execute('''
                    UPDATE pc_command 
                    SET status='pending', retry_count=? 
                    WHERE id=?
                ''', (retry_count, command_id))

            db.commit()
            return True
        except Exception:
            return False

    @staticmethod
    def get_by_status(status: str) -> List[Dict[str, Any]]:
        """상태별 명령 조회"""
        db = get_db()
        rows = db.execute('''
            SELECT * FROM pc_command 
            WHERE status=? 
            ORDER BY created_at DESC
        ''', (status,)).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def get_statistics() -> Dict[str, Any]:
        """명령 통계 조회"""
        db = get_db()

        total = db.execute('SELECT COUNT(*) as count FROM pc_command').fetchone()
        pending = db.execute("SELECT COUNT(*) as count FROM pc_command WHERE status='pending'").fetchone()
        completed = db.execute("SELECT COUNT(*) as count FROM pc_command WHERE status='completed'").fetchone()
        errors = db.execute("SELECT COUNT(*) as count FROM pc_command WHERE status='error'").fetchone()

        return {
            'total': total['count'] if total else 0,
            'pending': pending['count'] if pending else 0,
            'completed': completed['count'] if completed else 0,
            'errors': errors['count'] if errors else 0,
        }

    @staticmethod
    def get_recent(limit: int = 100) -> List[Dict[str, Any]]:
        """최근 명령 조회"""
        db = get_db()
        rows = db.execute('''
            SELECT * FROM pc_command 
            ORDER BY created_at DESC 
            LIMIT ?
        ''', (limit,)).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def cleanup_old(days: int = 30) -> int:
        """오래된 명령 삭제"""
        try:
            db = get_db()
            cursor = db.execute('''
                DELETE FROM pc_command 
                WHERE created_at < datetime('now', '-' || ? || ' days')
                AND status IN ('completed', 'error', 'timeout')
            ''', (days,))
            db.commit()
            return cursor.rowcount
        except Exception:
            return 0
