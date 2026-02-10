"""
PC 모델 (Repository 패턴)
PC 정보 관련 데이터베이스 작업을 캡슐화
"""
import sqlite3
import json
from typing import Optional, List, Dict, Any
from utils.database import get_db
from utils.validators import validate_not_null


class PCModel:
    """PC 정보 관리 모델"""

    @staticmethod
    def get_by_id(pc_id: int) -> Optional[Dict[str, Any]]:
        """PC ID로 PC 정보 조회"""
        db = get_db()
        row = db.execute(
            'SELECT * FROM pc_info WHERE id=?',
            (pc_id,)
        ).fetchone()
        return dict(row) if row else None

    @staticmethod
    def get_by_machine_id(machine_id: str) -> Optional[Dict[str, Any]]:
        """Machine ID로 PC 정보 조회"""
        db = get_db()
        row = db.execute(
            'SELECT id FROM pc_info WHERE machine_id=?',
            (machine_id,)
        ).fetchone()
        return dict(row) if row else None

    @staticmethod
    def get_all_by_room(room_name: str) -> List[Dict[str, Any]]:
        """실습실별 모든 PC 조회"""
        db = get_db()
        rows = db.execute(
            'SELECT * FROM pc_info WHERE room_name=? ORDER BY seat_number',
            (room_name,)
        ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def get_all() -> List[Dict[str, Any]]:
        """모든 PC 조회"""
        db = get_db()
        rows = db.execute('SELECT * FROM pc_info ORDER BY hostname').fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def get_online_count() -> int:
        """온라인 PC 개수 조회"""
        db = get_db()
        result = db.execute(
            'SELECT COUNT(*) as count FROM pc_info WHERE is_online=1'
        ).fetchone()
        return result['count'] if result else 0

    @staticmethod
    def register(
        machine_id: str,
        hostname: str,
        mac_address: str,
        ip_address: Optional[str] = None,
        cpu_model: Optional[str] = None,
        cpu_cores: Optional[int] = None,
        cpu_threads: Optional[int] = None,
        ram_total: Optional[float] = None,
        disk_info: Optional[Dict] = None,
        os_edition: Optional[str] = None,
        os_version: Optional[str] = None
    ) -> int:
        """새로운 PC 등록"""
        db = get_db()

        # pc_info 삽입
        cursor = db.execute('''
            INSERT INTO pc_info (machine_id, hostname, ip_address, mac_address, is_online, created_at, last_seen)
            VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''', (machine_id, hostname, ip_address, mac_address))

        pc_id = cursor.lastrowid

        # pc_specs 삽입
        disk_info_str = json.dumps(disk_info) if disk_info else '{}'
        db.execute('''
            INSERT INTO pc_specs (pc_id, cpu_model, cpu_cores, cpu_threads, ram_total, disk_info, os_edition, os_version)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            pc_id,
            cpu_model or 'Unknown CPU',
            validate_not_null(cpu_cores, 0),
            validate_not_null(cpu_threads, 0),
            validate_not_null(ram_total, 0),
            disk_info_str,
            os_edition or 'Unknown',
            os_version or 'Unknown'
        ))

        db.commit()
        return pc_id

    @staticmethod
    def update_or_create(
        machine_id: str,
        hostname: str,
        mac_address: str,
        ip_address: Optional[str] = None,
        cpu_model: Optional[str] = None,
        cpu_cores: Optional[int] = None,
        cpu_threads: Optional[int] = None,
        ram_total: Optional[float] = None,
        disk_info: Optional[Dict] = None,
        os_edition: Optional[str] = None,
        os_version: Optional[str] = None
    ) -> int:
        """PC 등록 또는 업데이트"""
        existing = PCModel.get_by_machine_id(machine_id)

        if existing:
            # 기존 PC 업데이트
            pc_id = existing['id']
            db = get_db()
            db.execute('''
                UPDATE pc_info 
                SET hostname=?, ip_address=?, mac_address=?, is_online=1, last_seen=CURRENT_TIMESTAMP, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            ''', (hostname, ip_address, mac_address, pc_id))

            # pc_specs 업데이트
            disk_info_str = json.dumps(disk_info) if disk_info else '{}'
            
            # pc_specs가 존재하는지 확인
            specs_exist = db.execute('SELECT 1 FROM pc_specs WHERE pc_id=?', (pc_id,)).fetchone()
            
            if specs_exist:
                db.execute('''
                    UPDATE pc_specs 
                    SET cpu_model=?, cpu_cores=?, cpu_threads=?, ram_total=?, disk_info=?, os_edition=?, os_version=?, updated_at=CURRENT_TIMESTAMP 
                    WHERE pc_id=?
                ''', (
                    cpu_model or 'Unknown CPU',
                    validate_not_null(cpu_cores, 0),
                    validate_not_null(cpu_threads, 0),
                    validate_not_null(ram_total, 0),
                    disk_info_str,
                    os_edition or 'Unknown',
                    os_version or 'Unknown',
                    pc_id
                ))
            else:
                # specs가 없으면 생성 (기존 데이터 마이그레이션 이슈 대응)
                db.execute('''
                    INSERT INTO pc_specs (pc_id, cpu_model, cpu_cores, cpu_threads, ram_total, disk_info, os_edition, os_version)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    pc_id,
                    cpu_model or 'Unknown CPU',
                    validate_not_null(cpu_cores, 0),
                    validate_not_null(cpu_threads, 0),
                    validate_not_null(ram_total, 0),
                    disk_info_str,
                    os_edition or 'Unknown',
                    os_version or 'Unknown'
                ))
                
            db.commit()
            return pc_id
        else:
            # 신규 등록
            return PCModel.register(
                machine_id, hostname, mac_address, ip_address,
                cpu_model, cpu_cores, cpu_threads, ram_total,
                disk_info, os_edition, os_version
            )

    @staticmethod
    def update_heartbeat(pc_id: int, cpu_usage: float, ram_used: float, ram_usage_percent: float,
                        disk_usage: Optional[Dict] = None, current_user: Optional[str] = None,
                        uptime: int = 0, processes: Optional[List[str]] = None) -> bool:
        """하트비트 업데이트 (동적 상태)"""
        try:
            db = get_db()

            # pc_info 업데이트
            db.execute('''
                UPDATE pc_info 
                SET is_online=1, last_seen=CURRENT_TIMESTAMP
                WHERE id=?
            ''', (pc_id,))

            # pc_dynamic_info 업데이트 (UNIQUE pc_id 제약으로 최신 상태만 유지)
            disk_usage_str = json.dumps(disk_usage) if disk_usage else '{}'
            processes_str = json.dumps(processes) if processes else '[]'

            db.execute('''
                INSERT OR REPLACE INTO pc_dynamic_info 
                (pc_id, cpu_usage, ram_used, ram_usage_percent, disk_usage, current_user, uptime, processes, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (pc_id, cpu_usage, ram_used, ram_usage_percent, disk_usage_str, current_user, uptime, processes_str))

            db.commit()
            return True
        except Exception as e:
            return False

    @staticmethod
    def set_offline(pc_id: int) -> bool:
        """PC를 오프라인으로 설정"""
        try:
            db = get_db()
            db.execute(
                'UPDATE pc_info SET is_online=0 WHERE id=?',
                (pc_id,)
            )
            db.commit()
            return True
        except Exception:
            return False

    @staticmethod
    def update_layout(pc_id: int, room_name: str, seat_number: str) -> bool:
        """PC 좌석 배치 업데이트"""
        try:
            db = get_db()
            db.execute(
                'UPDATE pc_info SET room_name=?, seat_number=? WHERE id=?',
                (room_name, seat_number, pc_id)
            )
            db.commit()
            return True
        except Exception:
            return False

    @staticmethod
    def get_with_status(pc_id: int) -> Optional[Dict[str, Any]]:
        """PC 정보와 최신 상태를 함께 조회"""
        pc = PCModel.get_by_id(pc_id)
        if not pc:
            return None

        db = get_db()

        # 최신 상태 정보 (UNIQUE pc_id 제약으로 항상 1개만 존재)
        status = db.execute(
            'SELECT * FROM pc_dynamic_info WHERE pc_id=?',
            (pc_id,)
        ).fetchone()

        # 스펙 정보
        specs = db.execute(
            'SELECT * FROM pc_specs WHERE pc_id=?',
            (pc_id,)
        ).fetchone()

        if status:
            pc['cpu_usage'] = status['cpu_usage']
            pc['ram_used'] = status['ram_used']
            pc['ram_usage_percent'] = status['ram_usage_percent']
            pc['disk_usage'] = status['disk_usage']
            pc['current_user'] = status['current_user']
            pc['uptime'] = status['uptime']
            pc['processes'] = status['processes']
        else:
            pc['cpu_usage'] = None
            pc['ram_used'] = 0
            pc['ram_usage_percent'] = 0
            pc['disk_usage'] = '{}'
            pc['current_user'] = None
            pc['uptime'] = 0
            pc['processes'] = '[]'

        if specs:
            pc['cpu_model'] = specs['cpu_model']
            pc['cpu_cores'] = specs['cpu_cores']
            pc['cpu_threads'] = specs['cpu_threads']
            pc['ram_total'] = specs['ram_total']
            pc['disk_info'] = specs['disk_info']
            pc['os_edition'] = specs['os_edition']
            pc['os_version'] = specs['os_version']

        # disk_info_parsed 생성 (정적 disk_info + 동적 disk_usage 병합)
        disk_info_parsed = {}
        try:
            # disk_info 파싱 (정적 정보: total_gb, fstype, mountpoint)
            # 이중 JSON 인코딩 처리 (필요시 재파싱)
            disk_raw = pc.get('disk_info') or '{}'
            while isinstance(disk_raw, str):
                try:
                    disk_raw = json.loads(disk_raw)
                except (json.JSONDecodeError, TypeError):
                    break
            disk_info_data = disk_raw if isinstance(disk_raw, dict) else {}

            # disk_usage 파싱 (동적 정보: used_gb, free_gb, percent)
            # 이중 JSON 인코딩 처리 (필요시 재파싱)
            disk_usage_raw = pc.get('disk_usage') or '{}'
            while isinstance(disk_usage_raw, str):
                try:
                    disk_usage_raw = json.loads(disk_usage_raw)
                except (json.JSONDecodeError, TypeError):
                    break
            disk_usage_data = disk_usage_raw if isinstance(disk_usage_raw, dict) else {}

            # 병합: disk_info를 기반으로 disk_usage 추가
            for dev, info in disk_info_data.items():
                disk_info_parsed[dev] = dict(info)  # 복사
                if dev in disk_usage_data:
                    disk_info_parsed[dev].update(disk_usage_data[dev])
        except Exception as e:
            # JSON 파싱 실패 시 빈 딕셔너리
            disk_info_parsed = {}

        pc['disk_info_parsed'] = disk_info_parsed

        return pc

    @staticmethod
    def delete(pc_id: int) -> bool:
        """PC 삭제"""
        try:
            db = get_db()
            db.execute('DELETE FROM pc_info WHERE id=?', (pc_id,))
            db.commit()
            return True
        except Exception:
            return False

