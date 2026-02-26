"""
PC 관리 서비스
비즈니스 로직 처리
"""
import time
import threading
import logging
from utils import get_db

logger = logging.getLogger('wcms')


class PCService:
    """PC 관련 비즈니스 로직"""

    @staticmethod
    def update_offline_status(threshold_seconds: int = 40) -> int:
        """
        last_seen이 threshold_seconds 초 이상 갱신되지 않은 PC를 오프라인으로 전환

        long-poll timeout 30s + 여유 10s = 기본 40초
        """
        try:
            db = get_db()

            # 오프라인으로 전환될 PC 목록 조회
            to_offline = db.execute("""
                SELECT id FROM pc_info
                WHERE is_online=1
                AND (julianday('now') - julianday(last_seen)) * 86400 > ?
            """, (threshold_seconds,)).fetchall()

            count = len(to_offline)
            if count == 0:
                return 0

            for row in to_offline:
                pc_id = row['id']
                db.execute('UPDATE pc_info SET is_online=0 WHERE id=?', (pc_id,))
                # 열린 network_events 레코드가 없으면 timeout으로 기록
                existing = db.execute(
                    'SELECT id FROM network_events WHERE pc_id=? AND online_at IS NULL',
                    (pc_id,)
                ).fetchone()
                if not existing:
                    db.execute(
                        'INSERT INTO network_events (pc_id, offline_at, reason) VALUES (?, CURRENT_TIMESTAMP, ?)',
                        (pc_id, 'timeout')
                    )

            db.commit()
            logger.info(f"[+] 오프라인 상태 업데이트: {count}대")
            return count
        except Exception as e:
            logger.error(f"[!] 오프라인 상태 업데이트 실패: {e}")
            return 0

    @staticmethod
    def start_background_checker(app, interval: int = 30):
        """백그라운드 오프라인 체크 스레드 시작"""
        def checker():
            logger.info(f"[*] 백그라운드 오프라인 체크 스레드 시작 ({interval}초 주기)")
            while True:
                try:
                    time.sleep(interval)
                    with app.app_context():
                        PCService.update_offline_status()
                except Exception as e:
                    logger.error(f"[!] 백그라운드 체크 오류: {e}")

        thread = threading.Thread(target=checker, daemon=True)
        thread.start()
