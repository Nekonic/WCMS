"""
PC 서비스 (비즈니스 로직)
PC 관리와 관련된 비즈니스 로직을 캡슐화
"""
from models import PCModel
from utils import get_db
from typing import List, Dict, Any
import sqlite3


class PCService:
    """PC 관리 서비스"""

    @staticmethod
    def get_pc_dashboard_data(room_name: str = None) -> Dict[str, Any]:
        """대시보드용 PC 정보 조회"""
        if room_name:
            pcs = PCModel.get_all_by_room(room_name)
        else:
            pcs = PCModel.get_all()

        # 각 PC의 상세 정보 추가
        result = []
        for pc in pcs:
            pc_data = PCModel.get_with_status(pc['id'])
            if pc_data:
                result.append(pc_data)

        # 통계
        total = len(result)
        online = sum(1 for pc in result if pc['is_online'])
        offline = total - online

        return {
            'total': total,
            'online': online,
            'offline': offline,
            'pcs': result
        }

    @staticmethod
    def update_offline_status(threshold_minutes: int = 2) -> int:
        """오프라인 상태 업데이트"""
        try:
            db = get_db()
            cursor = db.execute('''
                UPDATE pc_info 
                SET is_online=0 
                WHERE is_online=1 
                AND (julianday('now') - julianday(last_seen)) * 24 * 60 > ?
            ''', (threshold_minutes,))
            db.commit()
            return cursor.rowcount
        except Exception as e:
            return 0

    @staticmethod
    def get_online_pcs() -> List[Dict[str, Any]]:
        """온라인 PC 목록"""
        pcs = PCModel.get_all()
        return [pc for pc in pcs if pc['is_online']]

    @staticmethod
    def get_offline_pcs() -> List[Dict[str, Any]]:
        """오프라인 PC 목록"""
        pcs = PCModel.get_all()
        return [pc for pc in pcs if not pc['is_online']]

    @staticmethod
    def get_room_statistics(room_name: str) -> Dict[str, Any]:
        """실습실별 통계"""
        pcs = PCModel.get_all_by_room(room_name)

        total = len(pcs)
        online = sum(1 for pc in pcs if pc['is_online'])
        offline = total - online

        # CPU/RAM 평균
        cpu_total = 0
        ram_total = 0
        count = 0

        for pc in pcs:
            pc_data = PCModel.get_with_status(pc['id'])
            if pc_data and pc_data['cpu_usage'] is not None:
                cpu_total += pc_data['cpu_usage']
                ram_total += pc_data.get('ram_used', 0)
                count += 1

        return {
            'room': room_name,
            'total': total,
            'online': online,
            'offline': offline,
            'avg_cpu': round(cpu_total / count, 2) if count > 0 else 0,
            'avg_ram': round(ram_total / count, 2) if count > 0 else 0
        }

    @staticmethod
    def get_system_summary() -> Dict[str, Any]:
        """전체 시스템 요약"""
        pcs = PCModel.get_all()

        total = len(pcs)
        online = PCModel.get_online_count()
        offline = total - online

        return {
            'total_pcs': total,
            'online_pcs': online,
            'offline_pcs': offline,
            'online_rate': round((online / total * 100) if total > 0 else 0, 2)
        }

    @staticmethod
    def get_pc_status_history(pc_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """PC 상태 기록 조회"""
        db = get_db()
        rows = db.execute('''
            SELECT * FROM pc_status 
            WHERE pc_id=? 
            ORDER BY created_at DESC 
            LIMIT ?
        ''', (pc_id, limit)).fetchall()

        return [dict(row) for row in rows]

    @staticmethod
    def update_pc_layout(pc_id: int, room_name: str, row: int, col: int) -> bool:
        """PC 좌석 배치 업데이트"""
        seat_number = f"{col + 1}, {row + 1}"
        return PCModel.update_layout(pc_id, room_name, seat_number)

    @staticmethod
    def get_room_list() -> List[str]:
        """실습실 목록 조회"""
        try:
            db = get_db()
            rows = db.execute(
                'SELECT DISTINCT room_name FROM pc_info WHERE room_name IS NOT NULL ORDER BY room_name'
            ).fetchall()
            return [row['room_name'] for row in rows]
        except Exception:
            return []

