"""
WCMS 서버 메인 애플리케이션

모듈화된 구조:
- config: 환경 설정 관리
- models: 데이터 접근 계층 (Repository 패턴)
- api: HTTP API 레이어 (Flask Blueprint)
- services: 비즈니스 로직 계층
- utils: 공통 유틸리티 함수
"""
import logging
import sys
import os
from pathlib import Path

from flask import Flask, render_template, redirect, url_for, session, request
from flask_cors import CORS
from flask_session import Session
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
import cachelib

# 프로젝트 루트 경로
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'server'))

from config import get_config
from utils import get_db, close_db, init_db_manager, require_admin
from api import client_bp, admin_bp, install_bp
from services import PCService


# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s'
)
logger = logging.getLogger('wcms')


def _setup_file_logging(log_file: str):
    """서버 로그 파일 핸들러 추가 (중복 방지)"""
    from logging.handlers import RotatingFileHandler
    wcms_logger = logging.getLogger('wcms')
    if any(isinstance(h, RotatingFileHandler) for h in wcms_logger.handlers):
        return
    try:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        handler = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding='utf-8')
        handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s'))
        wcms_logger.addHandler(handler)
    except Exception as e:
        logger.warning(f"파일 로깅 설정 실패: {e}")

# Flask 기본 로거 설정 (개발 시 환경변수 DEBUG=1 설정)
if os.getenv('DEBUG') == '1':
    # 개발 모드: 모든 요청 로그 표시
    logging.getLogger('werkzeug').setLevel(logging.INFO)
    logger.info("개발 모드: 모든 요청 로그 활성화")
else:
    # 프로덕션 모드: GET 요청 로그 최소화
    logging.getLogger('werkzeug').setLevel(logging.WARNING)


def create_app(config_name='development'):
    """Flask 애플리케이션 팩토리"""
    app = Flask(__name__, template_folder='../server/templates')

    # 설정 로드
    config = get_config(config_name)
    app.config.from_object(config)

    # CORS 활성화 (Z-02: 환경변수로 허용 오리진 제한)
    allowed_origins = [o.strip() for o in os.getenv('WCMS_ALLOWED_ORIGINS', '*').split(',')]
    CORS(app, resources={r"/api/*": {"origins": allowed_origins}})

    # 세션 설정 (flask_session DeprecationWarning 해결)
    # FileSystemSessionInterface 대신 cachelib 직접 사용
    session_dir = os.path.join(app.root_path, 'flask_session')
    if not os.path.exists(session_dir):
        os.makedirs(session_dir)

    app.config['SESSION_TYPE'] = 'cachelib'
    app.config['SESSION_SERIALIZATION_FORMAT'] = 'json'
    app.config['SESSION_CACHELIB'] = cachelib.FileSystemCache(threshold=500, cache_dir=session_dir)

    Session(app)

    # CSRF 보호 (Z-03: 로그인 폼 등 브라우저 폼 보호)
    csrf = CSRFProtect(app)

    # 보안 헤더 설정 (Flask-Talisman) - 개발 환경에서는 선택적 활성화
    if config_name == 'production':
        # 프로덕션: HTTPS 강제, 보안 헤더 전체 적용
        # Z-01: style-src에서 unsafe-inline 제거 (인라인 CSS 외부화 완료)
        csp = {
            'default-src': "'self'",
            'script-src': ["'self'", "'unsafe-inline'", "cdn.jsdelivr.net"],
            'style-src': ["'self'", "cdn.jsdelivr.net", "cdnjs.cloudflare.com"],
            'img-src': ["'self'", "data:"],
            'font-src': ["'self'", "cdnjs.cloudflare.com"],
        }
        Talisman(app,
                 force_https=True,
                 strict_transport_security=True,
                 content_security_policy=csp,
                 content_security_policy_nonce_in=['script-src'])
    elif config_name == 'development':
        # 개발 환경: HTTPS 강제 없이 보안 헤더만 적용
        Talisman(app,
                 force_https=False,
                 strict_transport_security=False,
                 content_security_policy=False)

    # Rate Limiting 설정
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
        storage_uri="memory://"
    )

    # 파일 로깅 설정 (테스트 환경 제외)
    if config_name != 'test':
        _setup_file_logging(config.LOG_FILE)

    # DB 초기화/정리
    init_db_manager(app.config['DB_PATH'], app.config['DB_TIMEOUT'])

    with app.app_context():
        app.teardown_appcontext(close_db)
        
        # 백그라운드 오프라인 체크 시작
        if not app.config['TESTING']:
            PCService.start_background_checker(app, app.config['BACKGROUND_CHECK_INTERVAL'])

    # Blueprint 등록
    app.register_blueprint(client_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(install_bp)

    # 클라이언트 API는 Rate Limit 제외
    # - 2초 폴링 = 시간당 1,800회로 전역 제한(50회/시간)에 걸림
    # - 토큰 인증으로 이미 보호되므로 IP 기반 제한 불필요
    limiter.exempt(client_bp)

    # API Blueprint는 CSRF 제외 (Z-03: 토큰/세션 인증으로 대체)
    # - client_bp: 클라이언트 토큰 인증
    # - admin_bp: 브라우저 AJAX (fetch), 세션 인증
    # - install_bp: 설치 스크립트 배포
    csrf.exempt(client_bp)
    csrf.exempt(admin_bp)
    csrf.exempt(install_bp)


    # ==================== 웹 페이지 라우트 (레거시 호환) ====================

    @app.route('/')
    def index():
        """메인 페이지 - PC 목록 (비로그인 접근 허용)"""
        # 오프라인 상태 업데이트 (페이지 로드 시)
        PCService.update_offline_status()

        # 쿼리 파라미터 처리 (?room=...)
        room_name = request.args.get('room')
        
        # 실습실이 지정되지 않았으면 첫 번째 실습실로 리다이렉트
        if not room_name:
            db = get_db()
            try:
                first_room = db.execute('SELECT room_name FROM seat_layout WHERE is_active=1 ORDER BY room_name LIMIT 1').fetchone()
                if first_room:
                    return redirect(url_for('index', room=first_room['room_name']))
            except Exception:
                pass
            # 실습실이 아예 없으면 그냥 진행

        from models import PCModel
        if room_name:
            pcs = PCModel.get_all_by_room(room_name)
        else:
            pcs = [] # 실습실 선택 안됨
        
        # 각 PC의 최신 상태 추가
        pcs_with_status = []
        for pc in pcs:
            pc_status = PCModel.get_with_status(pc['id'])
            if pc_status:
                pcs_with_status.append(pc_status)
            else:
                pcs_with_status.append(pc)
        
        admin_user = session.get('username')
                
        return render_template('index.html', pcs=pcs_with_status, room=room_name, username=admin_user, admin=admin_user)

    @app.route('/login', methods=['GET', 'POST'])
    @limiter.limit("5 per minute")  # Brute-force 방어
    def login():
        """관리자 로그인"""
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')

            from models import AdminModel
            admin = AdminModel.authenticate(username, password)

            if admin:
                session['username'] = admin['username']
                session['admin_id'] = admin['id']
                session['admin'] = True  # 레거시 호환성 (require_admin 데코레이터용)
                session.permanent = True  # 세션 만료 시간 적용
                logger.info(f"로그인 성공: {username}")
                return redirect(url_for('index'))
            else:
                logger.warning(f"로그인 실패: {username} from {request.remote_addr}")
                return render_template('login.html', error='아이디 또는 비밀번호가 잘못되었습니다.')

        return render_template('login.html')

    @app.route('/logout')
    def logout():
        """로그아웃"""
        username = session.get('username', 'Unknown')
        session.clear()
        logger.info(f"로그아웃: {username}")
        return redirect(url_for('index'))

    # 레거시 경로: /layout/editor
    @app.route('/layout/editor')
    @require_admin
    def layout_editor():
        """좌석 배치 편집기"""
        room = request.args.get('room')
        if not room:
            return redirect(url_for('layout_editor', room='1실습실'))
            
        db = get_db()
        pcs = db.execute('SELECT * FROM pc_info WHERE room_name=?', (room,)).fetchall()
        unassigned = db.execute('SELECT * FROM pc_info WHERE room_name IS NULL OR room_name = ""').fetchall()

        return render_template('layout_editor.html',
                               room=room,
                               pcs=[dict(pc) for pc in pcs],
                               unassigned=[dict(pc) for pc in unassigned],
                               username=session.get('username'))

    # 레거시 경로: /room/manager
    @app.route('/room/manager')
    @require_admin
    def manage_rooms():
        """실습실 관리 페이지"""
        from models import PCModel
        db = get_db()
        try:
            rooms = db.execute('SELECT room_name FROM seat_layout WHERE is_active=1 ORDER BY room_name').fetchall()
            room_list = [r['room_name'] for r in rooms]
        except Exception:
            room_list = []

        return render_template('room_manager.html', rooms=room_list, username=session.get('username'))

    # 레거시 경로: /system/status
    @app.route('/system/status')
    @require_admin
    def system_status():
        """시스템 상태 페이지"""
        from models import PCModel
        pcs = PCModel.get_all()
        stats = {
            'total': len(pcs),
            'online': sum(1 for pc in pcs if pc['is_online']),
            'offline': len(pcs) - sum(1 for pc in pcs if pc['is_online']),
            'online_rate': round((sum(1 for pc in pcs if pc['is_online']) / len(pcs) * 100) if pcs else 0, 2)
        }
        return render_template('system_status.html', stats=stats, username=session.get('username'))

    # 레거시 경로: /pc/<int:pc_id>/history
    @app.route('/pc/<int:pc_id>/history')
    @require_admin
    def pc_history_page(pc_id):
        """PC 프로세스 기록 페이지"""
        from models import PCModel
        pc = PCModel.get_by_id(pc_id)
        if not pc:
            return "PC not found", 404
        return render_template('process_history.html', pc=pc, username=session.get('username'))

    # 레거시 경로: /command/test
    @app.route('/command/test')
    @require_admin
    def command_test():
        """명령 실행 테스트 페이지"""
        return render_template('command_test.html', username=session.get('username'))

    # 클라이언트 버전 관리 페이지
    @app.route('/client/versions')
    @require_admin
    def client_versions_page():
        """클라이언트 버전 관리 페이지"""
        return render_template('client_versions.html', username=session.get('username'))

    # 등록 토큰 관리 페이지 (v0.8.0)
    @app.route('/registration-tokens')
    @require_admin
    def registration_tokens_page():
        """등록 토큰 관리 페이지"""
        return render_template('registration_tokens.html', username=session.get('username'))

    # 컨텍스트 프로세서 (모든 템플릿에 실습실 목록 주입)
    @app.context_processor
    def inject_rooms():
        try:
            db = get_db()
            rooms = db.execute('SELECT room_name FROM seat_layout WHERE is_active=1 ORDER BY room_name').fetchall()
            room_list = [r['room_name'] for r in rooms]
            return {'all_rooms': room_list}
        except Exception:
            return {'all_rooms': []}

    # 에러 핸들러
    @app.errorhandler(404)
    def not_found(error):
        # API 경로 404는 로깅
        if request.path.startswith('/api/'):
            logger.warning(f"404 Not Found: {request.method} {request.path} from {request.remote_addr}")
        return render_template('error.html', error='페이지를 찾을 수 없습니다 (404)'), 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}")
        return render_template('error.html', error='서버 내부 오류가 발생했습니다 (500)'), 500


    # robots.txt 엔드포인트
    @app.route('/robots.txt')
    def robots_txt():
        """검색 엔진 크롤링 차단"""
        return """User-agent: *
Disallow: /
""", 200, {'Content-Type': 'text/plain'}

    # 서버 로그 페이지
    @app.route('/admin/server-log')
    @require_admin
    def server_log_page():
        """서버 로그 및 네트워크 이벤트 페이지"""
        log_file = config.LOG_FILE
        log_lines = []
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                    lines = f.readlines()
                    log_lines = lines[-200:]
            except Exception as e:
                log_lines = [f"로그 파일 읽기 실패: {e}\n"]

        db = get_db()
        events = db.execute('''
            SELECT ne.id, ne.pc_id, ne.offline_at, ne.online_at, ne.duration_sec, ne.reason,
                   pi.hostname
            FROM network_events ne
            JOIN pc_info pi ON ne.pc_id = pi.id
            ORDER BY ne.offline_at DESC
            LIMIT 100
        ''').fetchall()

        return render_template('server_log.html',
                               log_lines=log_lines,
                               events=[dict(e) for e in events],
                               username=session.get('username'))

    # 소개 페이지
    @app.route('/about')
    def about():
        """WCMS 소개 페이지"""
        return render_template('about.html', username=session.get('username'))

    logger.info(f"앱 생성: {config_name} 모드")
    return app

# Gunicorn 진입점 (전역 app 객체 생성)
import os
mode = os.getenv('FLASK_ENV', 'development')
app = create_app(mode)

if __name__ == '__main__':
    debug = mode == 'development'

    logger.info(f"WCMS 서버 시작 (모드: {mode})")

    # HTTPS 지원 (선택적)
    ssl_context = None
    if os.getenv('WCMS_SSL_CERT') and os.getenv('WCMS_SSL_KEY'):
        ssl_context = (
            os.getenv('WCMS_SSL_CERT'),  # 인증서 파일 경로
            os.getenv('WCMS_SSL_KEY')    # 개인키 파일 경로
        )
        logger.info("HTTPS 모드로 시작합니다.")
        logger.info("https://0.0.0.0:5050 에서 접속 가능합니다.")
    else:
        logger.info("HTTP 모드로 시작합니다. (프로덕션에서는 HTTPS 권장)")
        logger.info("http://0.0.0.0:5050 에서 접속 가능합니다.")

    app.run(
        host='0.0.0.0',
        port=5050,
        debug=debug,
        use_reloader=debug,
        ssl_context=ssl_context
    )
