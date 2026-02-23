"""
WCMS 서버 설정 관리
환경변수 및 설정 값 중앙화
"""
import os
from pathlib import Path


class Config:
    """기본 설정"""

    # 애플리케이션 경로
    BASE_DIR = Path(__file__).parent

    # Flask 설정
    SECRET_KEY = os.getenv('WCMS_SECRET_KEY')  # 환경변수 필수 (프로덕션)
    DEBUG = False
    TESTING = False

    # 보안 설정
    SESSION_COOKIE_SECURE = True  # HTTPS에서만 쿠키 전송
    SESSION_COOKIE_HTTPONLY = True  # JavaScript 접근 차단
    SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF 보호
    PERMANENT_SESSION_LIFETIME = 3600  # 세션 만료 시간 (1시간)

    # 데이터베이스 설정
    DB_PATH = os.getenv('WCMS_DB_PATH', str(BASE_DIR / 'db.sqlite3'))
    DB_TIMEOUT = int(os.getenv('WCMS_DB_TIMEOUT', '10'))
    DB_BUSY_TIMEOUT = int(os.getenv('WCMS_DB_BUSY_TIMEOUT', '5000'))

    # 서버 설정
    HOST = os.getenv('WCMS_HOST', '0.0.0.0')
    PORT = int(os.getenv('WCMS_PORT', '5050'))

    # 타임아웃 설정
    OFFLINE_THRESHOLD_MINUTES = int(os.getenv('WCMS_OFFLINE_THRESHOLD', '2'))  # PC 오프라인 판단 기준
    BACKGROUND_CHECK_INTERVAL = int(os.getenv('WCMS_BG_CHECK_INTERVAL', '30'))  # 백그라운드 체크 주기

    # 명령 설정
    COMMAND_TIMEOUT_SECONDS = int(os.getenv('WCMS_COMMAND_TIMEOUT', '300'))
    MAX_COMMAND_RETRIES = int(os.getenv('WCMS_MAX_RETRIES', '3'))

    # 로깅 설정
    LOG_LEVEL = os.getenv('WCMS_LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('WCMS_LOG_FILE', str(BASE_DIR / 'logs' / 'server.log'))

    # 클라이언트 버전 관리
    UPDATE_TOKEN = os.getenv('UPDATE_TOKEN', 'default-secret-token')

    # 데이터 보관 기간
    STATUS_RETENTION_MONTHS = int(os.getenv('WCMS_STATUS_RETENTION', '3'))
    COMMAND_RETENTION_DAYS = int(os.getenv('WCMS_COMMAND_RETENTION', '30'))


class DevelopmentConfig(Config):
    """개발 환경 설정"""
    DEBUG = True
    SECRET_KEY = os.getenv('WCMS_SECRET_KEY', 'dev-secret-key-change-in-production')
    SESSION_COOKIE_SECURE = False  # 개발 환경에서는 HTTP 허용


class ProductionConfig(Config):
    """프로덕션 환경 설정"""
    DEBUG = False
    # 프로덕션에서는 SECRET_KEY 환경변수 필수
    # 클래스 정의 시점에 검사하지 않고, 인스턴스화 또는 속성 접근 시점에 검사하도록 변경
    # 또는 기본값을 제거하고 런타임에 확인


class TestConfig(Config):
    """테스트 환경 설정"""
    TESTING = True
    DB_PATH = ':memory:'  # 인메모리 DB 사용
    SECRET_KEY = 'test-secret-key'


# 환경에 따른 설정 선택
config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'test': TestConfig,
}


def get_config(env=None):
    """환경에 맞는 설정 반환"""
    if env is None:
        env = os.getenv('WCMS_ENV', 'development')
    
    config_class = config_map.get(env, DevelopmentConfig)
    
    # 프로덕션 환경일 때 필수 환경변수 체크
    if env == 'production' and not os.getenv('WCMS_SECRET_KEY'):
        raise ValueError("프로덕션 환경에서는 WCMS_SECRET_KEY 환경변수가 필요합니다")
        
    return config_class
