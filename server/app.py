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
from pathlib import Path

from flask import Flask, render_template, redirect, url_for, session, request
from flask_cors import CORS
from flask_session import Session

# 프로젝트 루트 경로
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'server'))

from config import get_config
from utils import get_db, close_db, init_db_manager
from api import client_bp, admin_bp


# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s'
)
logger = logging.getLogger('wcms')


def create_app(config_name='development'):
    """Flask 애플리케이션 팩토리"""
    app = Flask(__name__, template_folder='../server/templates')

    # 설정 로드
    config = get_config(config_name)
    app.config.from_object(config)

    # CORS 활성화
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # 세션 설정
    app.config['SESSION_TYPE'] = 'filesystem'
    Session(app)

    # DB 초기화/정리
    # 앱 시작 시 DB 매니저 초기화
    init_db_manager(app.config['DB_PATH'], app.config['DB_TIMEOUT'])

    with app.app_context():
        app.teardown_appcontext(close_db)

    # Blueprint 등록
    app.register_blueprint(client_bp)
    app.register_blueprint(admin_bp)

    # 기본 라우트
    @app.route('/')
    def index():
        """홈페이지 리다이렉트"""
        if 'username' in session:
            # 로그인 되어 있으면 첫번째 실습실로 리다이렉트
            db = get_db()
            # seat_layout 테이블에서 활성화된 첫 번째 실습실 조회
            first_room = db.execute('SELECT room_name FROM seat_layout WHERE is_active=1 ORDER BY room_name LIMIT 1').fetchone()
            if first_room:
                return redirect(url_for('room_view', room_name=first_room['room_name']))
            else:
                # 실습실이 없으면 대시보드로 (혹은 실습실 생성 페이지로)
                return redirect(url_for('dashboard'))
        # 로그인 안되어 있으면 로그인 페이지로
        return redirect(url_for('login'))

    @app.route('/room/<room_name>')
    def room_view(room_name):
        """실습실별 PC 목록 뷰"""
        if 'username' not in session:
            return redirect(url_for('login'))
        
        from models import PCModel
        pcs = PCModel.get_all_by_room(room_name)
        return render_template('index.html', pcs=pcs, room=room_name, username=session.get('username'))


    @app.route('/login', methods=['GET', 'POST'])
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
                logger.info(f"로그인 성공: {username}")
                return redirect(url_for('index')) # 로그인 후 메인 페이지로 (index -> room_view)
            else:
                logger.warning(f"로그인 실패: {username}")
                return render_template('login.html', error='아이디 또는 비밀번호가 잘못되었습니다.')

        return render_template('login.html')

    @app.route('/logout')
    def logout():
        """로그아웃"""
        username = session.get('username', 'Unknown')
        session.clear()
        logger.info(f"로그아웃: {username}")
        return redirect(url_for('login'))

    @app.route('/dashboard')
    def dashboard():
        """대시보드"""
        if 'username' not in session:
            return redirect(url_for('login'))

        from models import PCModel
        pcs = PCModel.get_all()
        stats = {
            'total': len(pcs),
            'online': sum(1 for pc in pcs if pc['is_online']),
            'offline': len(pcs) - sum(1 for pc in pcs if pc['is_online'])
        }

        # dashboard.html이 없으므로 index.html을 사용하거나 새로 만들어야 함.
        # 기존 코드에서는 index.html을 대시보드처럼 사용했었음.
        # 하지만 room_view가 index.html을 사용하므로, dashboard용 템플릿이 필요할 수 있음.
        # 일단 index.html을 사용하되 room 파라미터 없이 전달
        return render_template('index.html', stats=stats, username=session.get('username'), room=None, pcs=pcs)

    @app.route('/pcs')
    def list_pcs():
        """PC 목록 페이지"""
        if 'username' not in session:
            return redirect(url_for('login'))

        from models import PCModel
        pcs = PCModel.get_all()
        return render_template('pc_list.html', pcs=pcs, username=session.get('username'))

    @app.route('/pcs/<int:pc_id>')
    def pc_detail(pc_id):
        """PC 상세 페이지"""
        if 'username' not in session:
            return redirect(url_for('login'))

        from models import PCModel
        pc = PCModel.get_by_id(pc_id)
        if not pc:
            return "PC not found", 404

        return render_template('pc_detail.html', pc=pc, username=session.get('username'))

    @app.route('/rooms')
    def manage_rooms():
        """실습실 관리 페이지"""
        if 'username' not in session:
            return redirect(url_for('login'))

        from models import PCModel
        rooms = set(pc.get('room_name') for pc in PCModel.get_all() if pc.get('room_name'))

        return render_template('room_manager.html', rooms=sorted(rooms), username=session.get('username'))

    @app.route('/layout')
    def layout_editor():
        """좌석 배치 편집기"""
        if 'username' not in session:
            return redirect(url_for('login'))

        return render_template('layout_editor.html', username=session.get('username'))

    @app.route('/commands')
    def command_history():
        """명령 실행 기록"""
        if 'username' not in session:
            return redirect(url_for('login'))

        from models import CommandModel
        commands = CommandModel.get_recent(100)

        return render_template('process_history.html', commands=commands, username=session.get('username'))

    @app.route('/system')
    def system_status():
        """시스템 상태 페이지"""
        if 'username' not in session:
            return redirect(url_for('login'))

        from models import PCModel
        pcs = PCModel.get_all()
        stats = {
            'total': len(pcs),
            'online': sum(1 for pc in pcs if pc['is_online']),
            'offline': len(pcs) - sum(1 for pc in pcs if pc['is_online']),
            'online_rate': round((sum(1 for pc in pcs if pc['is_online']) / len(pcs) * 100) if pcs else 0, 2)
        }

        return render_template('system_status.html', stats=stats, username=session.get('username'))

    @app.route('/admin')
    def admin_manager():
        """관리자 계정 관리"""
        if 'username' not in session:
            return redirect(url_for('login'))

        from models import AdminModel
        admins = AdminModel.get_all()

        return render_template('account_manager.html', admins=admins, username=session.get('username'))

    # 에러 핸들러
    @app.errorhandler(404)
    def not_found(error):
        return render_template('error.html', error='페이지를 찾을 수 없습니다 (404)'), 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}")
        return render_template('error.html', error='서버 내부 오류가 발생했습니다 (500)'), 500

    @app.before_request
    def log_request():
        """요청 로깅"""
        if not request.path.startswith('/static'):
            logger.debug(f"{request.method} {request.path}")

    logger.info(f"앱 생성: {config_name} 모드")
    return app


if __name__ == '__main__':
    import os

    # 환경 변수에서 모드 읽기
    mode = os.getenv('FLASK_ENV', 'development')
    debug = mode == 'development'

    app = create_app(mode)

    logger.info(f"WCMS 서버 시작 (모드: {mode})")
    logger.info("http://0.0.0.0:5050 에서 접속 가능합니다.")

    app.run(
        host='0.0.0.0',
        port=5050,
        debug=debug,
        use_reloader=debug
    )

