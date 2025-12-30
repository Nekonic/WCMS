"""
PC 관리 서비스
비즈니스 로직 처리
"""
import time
import threading
import logging
from typing import List, Dict, Any, Optional
from models import PCModel
from utils import get_db, execute_query

logger = logging.getLogger('wcms')


class PCService:
    """PC 관련 비즈니스 로직"""

    @staticmethod
    def update_offline_status(threshold_minutes: int = 2) -> int:
        """
        오랫동안 하트비트가 없는 PC를 오프라인으로 전환
        
        Args:
            threshold_minutes: 오프라인 판단 기준 시간 (분)
            
        Returns:
            업데이트된 PC 수
        """
        try:
            # 직접 DB 연결 사용 (스레드 안전성 확보)
            # utils.execute_query는 g.db를 사용하므로 백그라운드 스레드에서는 부적절할 수 있음
            # 하지만 여기서는 간단히 모델을 통해 호출하거나, 별도 연결을 맺어야 함
            
            # 모델 메서드 활용 (내부적으로 get_db 호출 -> g.db 사용)
            # 백그라운드 스레드에서는 app_context가 필요함
            
            # 쿼리 직접 실행
            db = get_db()
            cursor = db.execute("""
                UPDATE pc_info 
                SET is_online=0 
                WHERE is_online=1 
                AND (julianday('now') - julianday(last_seen)) * 24 * 60 > ?
            """, (threshold_minutes,))
            
            count = cursor.rowcount
            if count > 0:
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
