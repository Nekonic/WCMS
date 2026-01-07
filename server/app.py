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
from utils import get_db, close_db, init_db_manager, require_admin
from api import client_bp, admin_bp
from services import PCService


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
    init_db_manager(app.config['DB_PATH'], app.config['DB_TIMEOUT'])

    with app.app_context():
        app.teardown_appcontext(close_db)
        
        # 백그라운드 오프라인 체크 시작
        if not app.config['TESTING']:
            PCService.start_background_checker(app, app.config['BACKGROUND_CHECK_INTERVAL'])

    # Blueprint 등록
    app.register_blueprint(client_bp)
    app.register_blueprint(admin_bp)

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
                logger.info(f"로그인 성공: {username}")
                return redirect(url_for('index'))
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

    # 레거시 경로: /account/manager
    @app.route('/account/manager')
    @require_admin
    def admin_manager():
        """관리자 계정 관리"""
        from models import AdminModel
        admins = AdminModel.get_all()
        return render_template('account_manager.html', admins=admins, username=session.get('username'))

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
