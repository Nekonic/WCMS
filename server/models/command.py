"""
명령 모델 (Repository 패턴)
PC 명령 관련 데이터베이스 작업을 캡슐화
"""
import json
from typing import Optional, List, Dict, Any
from utils.database import get_db


class CommandModel:
    """명령 관리 모델"""

    @staticmethod
    def create(pc_id: int, command_type: str, command_data: Optional[Dict] = None,
               admin_username: Optional[str] = None, priority: int = 5,
               max_retries: int = 3, timeout_seconds: int = 300) -> int:
        """새로운 명령 생성 (archive/code/app.py 호환)"""
        db = get_db()
        command_data_str = json.dumps(command_data) if command_data else '{}'

        # archive 스키마 호환성: admin_username, max_retries, timeout_seconds 컬럼이 없을 수 있음
        # 먼저 테이블 스키마 확인
        try:
            # 테이블 정보 조회
            columns_info = db.execute("PRAGMA table_info(commands)").fetchall()
            columns = {col['name'] for col in columns_info}

            if 'admin_username' in columns and 'max_retries' in columns and 'timeout_seconds' in columns:
                # 리팩터링된 스키마 (확장 컬럼 사용)
                cursor = db.execute('''
                    INSERT INTO commands (pc_id, admin_username, command_type, command_data, priority, status, max_retries, timeout_seconds)
                    VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)
                ''', (pc_id, admin_username, command_type, command_data_str, priority, max_retries, timeout_seconds))
            else:
                # archive 스키마 (기본 컬럼만 사용)
                cursor = db.execute('''
                    INSERT INTO commands (pc_id, command_type, command_data, priority, status)
                    VALUES (?, ?, ?, ?, 'pending')
                ''', (pc_id, command_type, command_data_str, priority))
        except Exception:
            # 에러 발생 시 기본 스키마 사용
            cursor = db.execute('''
                INSERT INTO commands (pc_id, command_type, command_data, status)
                VALUES (?, ?, ?, 'pending')
            ''', (pc_id, command_type, command_data_str))

        db.commit()
        return cursor.lastrowid

    @staticmethod
    def get_by_id(command_id: int) -> Optional[Dict[str, Any]]:
        """명령 ID로 조회"""
        db = get_db()
        row = db.execute(
            'SELECT * FROM commands WHERE id=?',
            (command_id,)
        ).fetchone()
        return dict(row) if row else None

    @staticmethod
    def get_pending_for_pc(pc_id: int) -> List[Dict[str, Any]]:
        """특정 PC의 대기 중인 명령 조회"""
        db = get_db()
        rows = db.execute('''
            SELECT * FROM commands 
            WHERE pc_id=? AND status='pending' 
            ORDER BY priority ASC, created_at ASC
        ''', (pc_id,)).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def get_all_pending() -> List[Dict[str, Any]]:
        """모든 대기 중인 명령 조회"""
        db = get_db()
        rows = db.execute('''
            SELECT * FROM commands 
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
                UPDATE commands 
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
            import logging
            logger = logging.getLogger('wcms.command_model')

            db = get_db()
            cursor = db.execute('''
                UPDATE commands 
                SET status='completed', result=?, completed_at=CURRENT_TIMESTAMP 
                WHERE id=?
            ''', (result, command_id))
            db.commit()

            rows_affected = cursor.rowcount
            logger.info(f"명령 완료 처리: cmd_id={command_id}, rows_affected={rows_affected}")
            return rows_affected > 0
        except Exception as e:
            import logging
            logger = logging.getLogger('wcms.command_model')
            logger.error(f"명령 완료 처리 실패: cmd_id={command_id}, error={e}", exc_info=True)
            return False

    @staticmethod
    def set_error(command_id: int, error_message: str) -> bool:
        """명령 에러 설정"""
        try:
            import logging
            logger = logging.getLogger('wcms.command_model')

            db = get_db()
            cursor = db.execute('''
                UPDATE commands 
                SET status='error', error_message=?, completed_at=CURRENT_TIMESTAMP 
                WHERE id=?
            ''', (error_message, command_id))
            db.commit()

            rows_affected = cursor.rowcount
            logger.info(f"명령 오류 처리: cmd_id={command_id}, rows_affected={rows_affected}")
            return rows_affected > 0
        except Exception as e:
            import logging
            logger = logging.getLogger('wcms.command_model')
            logger.error(f"명령 오류 처리 실패: cmd_id={command_id}, error={e}", exc_info=True)
            return False

    @staticmethod
    def set_timeout(command_id: int) -> bool:
        """명령 타임아웃 설정"""
        try:
            db = get_db()
            db.execute('''
                UPDATE commands 
                SET status='timeout', error_message='Command execution timeout', completed_at=CURRENT_TIMESTAMP 
                WHERE id=?
            ''', (command_id,))
            db.commit()
            return True
        except Exception:
            return False

    @staticmethod
    def increment_retry(command_id: int) -> bool:
        """재시도 횟수 증가 (archive 스키마 호환)"""
        try:
            db = get_db()
            command = CommandModel.get_by_id(command_id)
            if not command:
                return False

            # 스키마 확인
            columns_info = db.execute("PRAGMA table_info(commands)").fetchall()
            columns = {col['name'] for col in columns_info}

            retry_count = command.get('retry_count', 0) + 1
            max_retries = command.get('max_retries', 3)

            if 'retry_count' in columns and 'max_retries' in columns:
                # 확장 스키마
                if retry_count >= max_retries:
                    # 최대 재시도 횟수 초과
                    db.execute('''
                        UPDATE commands
                        SET status='error', error_message='Max retries exceeded', retry_count=?, completed_at=CURRENT_TIMESTAMP
                        WHERE id=?
                    ''', (retry_count, command_id))
                else:
                    # 재시도
                    db.execute('''
                        UPDATE commands
                        SET status='pending', retry_count=?
                        WHERE id=?
                    ''', (retry_count, command_id))
            else:
                # archive 스키마 - retry_count 없이 그냥 pending으로 변경
                db.execute('''
                    UPDATE commands
                    SET status='pending'
                    WHERE id=?
                ''', (command_id,))

            db.commit()
            return True
        except Exception:
            return False

    @staticmethod
    def get_by_status(status: str) -> List[Dict[str, Any]]:
        """상태별 명령 조회"""
        db = get_db()
        rows = db.execute('''
            SELECT * FROM commands 
            WHERE status=? 
            ORDER BY created_at DESC
        ''', (status,)).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def get_statistics() -> Dict[str, Any]:
        """명령 통계 조회"""
        db = get_db()

        total = db.execute('SELECT COUNT(*) as count FROM commands').fetchone()
        pending = db.execute("SELECT COUNT(*) as count FROM commands WHERE status='pending'").fetchone()
        completed = db.execute("SELECT COUNT(*) as count FROM commands WHERE status='completed'").fetchone()
        errors = db.execute("SELECT COUNT(*) as count FROM commands WHERE status='error'").fetchone()

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
            SELECT * FROM commands 
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
                DELETE FROM commands 
                WHERE created_at < datetime('now', '-' || ? || ' days')
                AND status IN ('completed', 'error', 'timeout')
            ''', (days,))
            db.commit()
            return cursor.rowcount
        except Exception:
            return 0

