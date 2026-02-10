"""
데이터베이스 유틸리티 모듈
DB 연결 관리 및 쿼리 헬퍼 함수
"""
import sqlite3
import datetime
from flask import g
from typing import Optional, List, Dict, Any, Union


# Python 3.12+ 호환성을 위한 datetime 어댑터 등록
def adapt_datetime(val):
    """datetime 객체를 ISO 포맷 문자열로 변환"""
    return val.isoformat(" ")

def convert_datetime(val):
    """ISO 포맷 문자열을 datetime 객체로 변환"""
    return datetime.datetime.fromisoformat(val.decode())

sqlite3.register_adapter(datetime.datetime, adapt_datetime)
sqlite3.register_converter("timestamp", convert_datetime)


class DatabaseManager:
    """데이터베이스 연결 및 쿼리 관리 클래스"""

    def __init__(self, db_path: str, timeout: int = 10, busy_timeout: int = 5000):
        self.db_path = db_path
        self.timeout = timeout
        self.busy_timeout = busy_timeout

    def get_connection(self) -> sqlite3.Connection:
        """데이터베이스 연결 가져오기 (컨텍스트당 하나)"""
        if 'db' not in g:
            g.db = sqlite3.connect(
                self.db_path,
                timeout=self.timeout,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
                check_same_thread=False,
                isolation_level=None  # autocommit 모드 (성능 향상)
            )
            g.db.row_factory = sqlite3.Row

            # SQLite 최적화 설정
            g.db.execute('PRAGMA journal_mode=WAL')  # Write-Ahead Logging
            g.db.execute(f'PRAGMA busy_timeout={self.busy_timeout}')
            g.db.execute('PRAGMA synchronous=NORMAL')  # 성능 향상 (FULL → NORMAL)
            g.db.execute('PRAGMA cache_size=-64000')  # 64MB 캐시 (성능 향상)
            g.db.execute('PRAGMA temp_store=MEMORY')  # 임시 테이블 메모리 저장
        return g.db

    def close_connection(self, error=None):
        """요청 종료 시 데이터베이스 연결 닫기"""
        db = g.pop('db', None)
        if db is not None:
            db.close()

    def execute_query(
        self,
        query: str,
        params: Optional[tuple] = None,
        fetch_one: bool = False,
        fetch_all: bool = False,
        commit: bool = False
    ) -> Union[sqlite3.Cursor, sqlite3.Row, List[sqlite3.Row], int, None]:
        """
        DB 쿼리 실행 헬퍼

        Args:
            query: SQL 쿼리
            params: 쿼리 파라미터
            fetch_one: 단일 행 반환
            fetch_all: 모든 행 반환
            commit: 커밋 여부

        Returns:
            Cursor, Row, List[Row], lastrowid, rowcount, 또는 None
        """
        db = self.get_connection()
        cursor = db.execute(query, params or [])

        if commit:
            db.commit()
            return cursor.lastrowid if cursor.lastrowid else cursor.rowcount

        if fetch_one:
            return cursor.fetchone()
        if fetch_all:
            return cursor.fetchall()
        return cursor


# 전역 데이터베이스 매니저 (앱 초기화 시 설정됨)
_db_manager: Optional[DatabaseManager] = None


def init_db_manager(db_path: str, timeout: int = 10, busy_timeout: int = 5000):
    """데이터베이스 매니저 초기화"""
    global _db_manager
    _db_manager = DatabaseManager(db_path, timeout, busy_timeout)
    return _db_manager


def get_db() -> sqlite3.Connection:
    """데이터베이스 연결 가져오기"""
    if _db_manager is None:
        raise RuntimeError("DatabaseManager가 초기화되지 않았습니다. init_db_manager()를 먼저 호출하세요.")
    return _db_manager.get_connection()


def close_db(error=None):
    """데이터베이스 연결 닫기"""
    if _db_manager:
        _db_manager.close_connection(error)


def execute_query(
    query: str,
    params: Optional[tuple] = None,
    fetch_one: bool = False,
    fetch_all: bool = False,
    commit: bool = False
) -> Union[sqlite3.Cursor, sqlite3.Row, List[sqlite3.Row], int, None]:
    """DB 쿼리 실행 헬퍼 (전역 함수)"""
    if _db_manager is None:
        raise RuntimeError("DatabaseManager가 초기화되지 않았습니다.")
    return _db_manager.execute_query(query, params, fetch_one, fetch_all, commit)


def validate_not_null(value: Any, default: Any) -> Any:
    """
    NOT NULL 필드 기본값 보정

    Args:
        value: 검증할 값
        default: 기본값

    Returns:
        검증된 값 또는 기본값
    """
    try:
        if isinstance(default, int):
            return int(value) if value is not None else default
        elif isinstance(default, float):
            return float(value) if value is not None else default
        return value if value else default
    except (ValueError, TypeError):
        return default


def dict_from_row(row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
    """
    sqlite3.Row를 딕셔너리로 변환

    Args:
        row: sqlite3.Row 객체

    Returns:
        딕셔너리 또는 None
    """
    if row is None:
        return None
    return dict(row)


def dicts_from_rows(rows: List[sqlite3.Row]) -> List[Dict[str, Any]]:
    """
    sqlite3.Row 리스트를 딕셔너리 리스트로 변환

    Args:
        rows: sqlite3.Row 리스트

    Returns:
        딕셔너리 리스트
    """
    return [dict(row) for row in rows]
