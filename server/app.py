from flask import Flask, render_template, request, redirect, url_for, session, jsonify, g
import sqlite3
import bcrypt
import os
import json
import time

app = Flask(__name__)
app.secret_key = 'woosuk25'
DB_PATH = os.path.join(os.path.dirname(__file__), 'db.sqlite3')


# ==================== 데이터베이스 헬퍼 ====================

def get_db():
    """데이터베이스 연결 가져오기 (컨텍스트당 하나)"""
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA journal_mode=WAL')
        g.db.execute('PRAGMA busy_timeout=5000')
    return g.db


@app.teardown_appcontext
def close_db(error):
    """요청 종료 시 데이터베이스 연결 닫기"""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def require_admin(f):
    """관리자 권한 확인 데코레이터"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin'):
            return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
        return f(*args, **kwargs)

    return decorated_function


# ==================== 웹 페이지 라우트 ====================

@app.route('/')
def index():
    """메인 페이지 - PC 목록"""
    room = request.args.get('room')
    if not room:
        return redirect(url_for('index', room='1실습실'))

    db = get_db()
    pcs_raw = db.execute('SELECT * FROM pc_info WHERE room_name=?', (room,)).fetchall()
    pcs = []

    for pc in pcs_raw:
        p = dict(pc)

        # 최신 상태 정보 (동적)
        status = db.execute(
            'SELECT * FROM pc_status WHERE pc_id=? ORDER BY created_at DESC LIMIT 1',
            (pc['id'],)
        ).fetchone()

        # 스펙 정보 (정적)
        specs = db.execute('SELECT * FROM pc_specs WHERE pc_id=?', (pc['id'],)).fetchone()

        if status:
            p['cpu_usage'] = status['cpu_usage']
            p['ram_used'] = status['ram_used']
            p['processes'] = status['processes']
        else:
            p['cpu_usage'] = None
            p['ram_used'] = 0
            p['processes'] = None

        if specs:
            p['ram_total'] = specs['ram_total']
            p['disk_info'] = specs['disk_info']
            p['os_edition'] = specs['os_edition']
        else:
            p['ram_total'] = 0
            p['disk_info'] = None
            p['os_edition'] = None

        pcs.append(p)

    return render_template('index.html', pcs=pcs, room=room, admin=session.get('admin'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """관리자 로그인"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        db = get_db()
        admin = db.execute('SELECT * FROM admins WHERE username=?', (username,)).fetchone()

        if admin and bcrypt.checkpw(password.encode(), admin['password_hash'].encode()):
            session['admin'] = username
            return redirect(url_for('index'))

        return render_template('login.html', error='로그인 실패')

    return render_template('login.html')


@app.route('/logout', methods=['POST'])
def logout():
    """관리자 로그아웃"""
    session.pop('admin', None)
    return redirect(url_for('index'))


@app.route('/layout/editor')
@require_admin
def layout_editor():
    """좌석 배치 편집기"""
    room = request.args.get('room')
    if not room:
        return redirect(url_for('layout_editor', room='1실습실'))

    db = get_db()
    pcs = db.execute('SELECT * FROM pc_info WHERE room_name=?', (room,)).fetchall()
    unassigned = db.execute('SELECT * FROM pc_info WHERE room_name IS NULL').fetchall()

    return render_template('layout_editor.html',
                           room=room,
                           pcs=[dict(pc) for pc in pcs],
                           unassigned=[dict(pc) for pc in unassigned])


@app.route('/pc/<int:pc_id>/history')
@require_admin
def pc_history_page(pc_id):
    """PC 프로세스 기록 페이지"""
    db = get_db()
    pc = db.execute('SELECT * FROM pc_info WHERE id=?', (pc_id,)).fetchone()
    if not pc:
        return "PC not found", 404

    return render_template('process_history.html', pc=dict(pc))


@app.route('/account/manager')
@require_admin
def account_manager():
    """Windows 계정 관리 페이지"""
    return render_template('account_manager.html')


# ==================== 관리자 API ====================

@app.route('/api/pcs')
def api_pcs_list():
    """모든 PC 목록 조회 (온라인 상태 포함)"""
    db = get_db()
    pcs = db.execute('SELECT * FROM pc_info ORDER BY room_name, seat_number').fetchall()

    result = []
    for pc in pcs:
        pc_dict = dict(pc)
        result.append(pc_dict)

    return jsonify(result)


@app.route('/api/pc/<int:pc_id>')
def api_pc_detail(pc_id):
    """PC 상세 정보 조회"""
    db = get_db()
    pc = db.execute('SELECT * FROM pc_info WHERE id=?', (pc_id,)).fetchone()
    if not pc:
        return jsonify({"error": "PC not found"}), 404

    pc_dict = dict(pc)

    # 최신 상태 정보
    status = db.execute(
        'SELECT * FROM pc_status WHERE pc_id=? ORDER BY created_at DESC LIMIT 1',
        (pc_id,)
    ).fetchone()
    if status:
        pc_dict.update(dict(status))

    # 스펙 정보
    specs = db.execute('SELECT * FROM pc_specs WHERE pc_id=?', (pc_id,)).fetchone()
    if specs:
        pc_dict.update(dict(specs))

    return jsonify(pc_dict)


@app.route('/api/pc/<int:pc_id>/history')
@require_admin
def api_pc_history(pc_id):
    """PC 프로세스 실행 기록 조회"""
    db = get_db()
    history = db.execute('''
                         SELECT created_at, current_user, processes
                         FROM pc_status
                         WHERE pc_id = ?
                           AND processes IS NOT NULL
                         ORDER BY created_at DESC
                         LIMIT 100
                         ''', (pc_id,)).fetchall()

    return jsonify([dict(row) for row in history])


@app.route('/api/pc/<int:pc_id>/command', methods=['POST'])
@require_admin
def api_pc_command(pc_id):
    """원격 명령 전송 (통합)"""
    data = request.json
    if not data or 'type' not in data:
        return jsonify({'status': 'error', 'message': 'type 필드가 필요합니다'}), 400

    db = get_db()

    # PC 존재 확인
    pc = db.execute('SELECT id FROM pc_info WHERE id=?', (pc_id,)).fetchone()
    if not pc:
        return jsonify({'status': 'error', 'message': 'PC를 찾을 수 없습니다'}), 404

    db.execute('INSERT INTO pc_command (pc_id, command_type, command_data) VALUES (?, ?, ?)',
               (pc_id, data.get('type'), json.dumps(data.get('data', {}))))
    db.commit()
    return jsonify({'status': 'success', 'message': '명령 전송 완료'})


@app.route('/api/pc/<int:pc_id>/shutdown', methods=['POST'])
@require_admin
def api_pc_shutdown(pc_id):
    """PC 종료 (편의 엔드포인트)"""
    return api_pc_command_wrapper(pc_id, 'shutdown', {})


@app.route('/api/pc/<int:pc_id>/reboot', methods=['POST'])
@require_admin
def api_pc_reboot(pc_id):
    """PC 재시작 (편의 엔드포인트)"""
    return api_pc_command_wrapper(pc_id, 'reboot', {})


def api_pc_command_wrapper(pc_id, cmd_type, cmd_data):
    """명령 전송 헬퍼 함수"""
    db = get_db()

    # PC 존재 확인
    pc = db.execute('SELECT id FROM pc_info WHERE id=?', (pc_id,)).fetchone()
    if not pc:
        return jsonify({'status': 'error', 'message': 'PC를 찾을 수 없습니다'}), 404

    db.execute('INSERT INTO pc_command (pc_id, command_type, command_data) VALUES (?, ?, ?)',
               (pc_id, cmd_type, json.dumps(cmd_data)))
    db.commit()

    action_name = {'shutdown': '종료', 'reboot': '재시작'}.get(cmd_type, '명령')
    return jsonify({'status': 'success', 'message': f'{action_name} 명령 전송 완료'})


@app.route('/api/pc/<int:pc_id>/account/create', methods=['POST'])
@require_admin
def api_create_account(pc_id):
    """Windows 계정 생성 명령 전송"""
    data = request.json

    # 필수 필드 검증
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({
            'status': 'error',
            'message': 'username과 password 필드가 필요합니다'
        }), 400

    db = get_db()
    pc = db.execute('SELECT id FROM pc_info WHERE id=?', (pc_id,)).fetchone()
    if not pc:
        return jsonify({'status': 'error', 'message': 'PC를 찾을 수 없습니다'}), 404

    command_data = {
        'username': data['username'],
        'password': data['password'],
        'full_name': data.get('full_name'),
        'comment': data.get('comment')
    }

    db.execute('INSERT INTO pc_command (pc_id, command_type, command_data) VALUES (?, ?, ?)',
               (pc_id, 'create_user', json.dumps(command_data)))
    db.commit()

    return jsonify({'status': 'success', 'message': '계정 생성 명령 전송 완료'})


@app.route('/api/pc/<int:pc_id>/account/delete', methods=['POST'])
@require_admin
def api_delete_account(pc_id):
    """Windows 계정 삭제 명령 전송"""
    data = request.json

    if not data or 'username' not in data:
        return jsonify({
            'status': 'error',
            'message': 'username 필드가 필요합니다'
        }), 400

    db = get_db()
    pc = db.execute('SELECT id FROM pc_info WHERE id=?', (pc_id,)).fetchone()
    if not pc:
        return jsonify({'status': 'error', 'message': 'PC를 찾을 수 없습니다'}), 404

    db.execute('INSERT INTO pc_command (pc_id, command_type, command_data) VALUES (?, ?, ?)',
               (pc_id, 'delete_user', json.dumps({'username': data['username']})))
    db.commit()

    return jsonify({'status': 'success', 'message': '계정 삭제 명령 전송 완료'})


@app.route('/api/pc/<int:pc_id>/account/password', methods=['POST'])
@require_admin
def api_change_password(pc_id):
    """Windows 계정 비밀번호 변경 명령 전송"""
    data = request.json

    if not data or 'username' not in data or 'new_password' not in data:
        return jsonify({
            'status': 'error',
            'message': 'username과 new_password 필드가 필요합니다'
        }), 400

    db = get_db()
    pc = db.execute('SELECT id FROM pc_info WHERE id=?', (pc_id,)).fetchone()
    if not pc:
        return jsonify({'status': 'error', 'message': 'PC를 찾을 수 없습니다'}), 404

    command_data = {
        'username': data['username'],
        'new_password': data['new_password']
    }

    db.execute('INSERT INTO pc_command (pc_id, command_type, command_data) VALUES (?, ?, ?)',
               (pc_id, 'change_password', json.dumps(command_data)))
    db.commit()

    return jsonify({'status': 'success', 'message': '비밀번호 변경 명령 전송 완료'})


@app.route('/api/layout/map/<room_name>', methods=['GET', 'POST'])
def manage_layout_map(room_name):
    """좌석 배치 관리"""
    db = get_db()

    if request.method == 'POST':
        if not session.get('admin'):
            return jsonify({'error': 'Unauthorized'}), 401

        data = request.json
        db.execute('DELETE FROM seat_map WHERE room_name=?', (room_name,))
        db.execute('UPDATE pc_info SET room_name=NULL WHERE room_name=?', (room_name,))

        for seat in data.get('seats', []):
            if seat.get('pc_id'):
                db.execute('INSERT INTO seat_map (room_name, row, col, pc_id) VALUES (?, ?, ?, ?)',
                           (room_name, seat['row'], seat['col'], seat['pc_id']))
                seat_number = f"{seat['col'] + 1}, {seat['row'] + 1}"
                db.execute('UPDATE pc_info SET room_name=?, seat_number=? WHERE id = ?',
                           (room_name, seat_number, seat['pc_id']))

        db.execute('INSERT OR REPLACE INTO seat_layout (room_name, cols, rows) VALUES (?, ?, ?)',
                   (room_name, data.get('cols', 8), data.get('rows', 5)))
        db.commit()
        return jsonify({'status': 'success'})
    else:
        layout = db.execute('SELECT * FROM seat_layout WHERE room_name=?', (room_name,)).fetchone()
        seats = db.execute('SELECT * FROM seat_map WHERE room_name=?', (room_name,)).fetchall()

        if not layout:
            db.execute('INSERT INTO seat_layout (room_name, rows, cols) VALUES (?, 5, 8)', (room_name,))
            db.commit()
            layout = {'rows': 5, 'cols': 8}

        return jsonify({
            'rows': layout['rows'],
            'cols': layout['cols'],
            'seats': [dict(s) for s in seats]
        })


# ==================== 클라이언트 API ====================

@app.route('/api/client/register', methods=['POST'])
def api_client_register():
    """클라이언트 등록"""
    data = request.json

    if not data or 'machine_id' not in data:
        return jsonify({'status': 'error', 'message': 'machine_id is required'}), 400

    db = get_db()
    existing = db.execute('SELECT id FROM pc_info WHERE machine_id=?', (data['machine_id'],)).fetchone()

    if existing:
        return jsonify({'status': 'error', 'message': '이미 등록된 PC입니다.'}), 500

    cursor = db.execute('''
                        INSERT INTO pc_info (machine_id, hostname, mac_address, is_online, last_seen)
                        VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP)
                        ''', (data['machine_id'], data.get('hostname'), data.get('mac_address')))
    pc_id = cursor.lastrowid

    # PC 스펙 정보를 별도 테이블에 저장
    db.execute('''
               INSERT INTO pc_specs (pc_id, cpu_model, cpu_cores, cpu_threads, ram_total, disk_info, os_edition,
                                      os_version)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ''', (
                   pc_id,
                   data.get('cpu_model'),
                   data.get('cpu_cores'),
                   data.get('cpu_threads'),
                   data.get('ram_total'),
                   data.get('disk_info'),
                   data.get('os_edition'),
                   data.get('os_version')
               ))

    db.commit()
    print(f"[+] PC 등록 (미배치): {data['machine_id']}")
    return jsonify({'status': 'success', 'message': '등록 완료'}), 200


@app.route('/api/client/heartbeat', methods=['POST'])
def api_client_heartbeat():
    """클라이언트 하트비트"""
    data = request.json

    if not data or 'machine_id' not in data:
        return jsonify({'status': 'error', 'message': 'machine_id is required'}), 400

    db = get_db()
    pc = db.execute('SELECT id FROM pc_info WHERE machine_id=?', (data['machine_id'],)).fetchone()

    if not pc:
        return jsonify({'status': 'error', 'message': 'PC not registered'}), 404

    pc_id = pc['id']
    info = data.get('system_info', {})

    db.execute('''
               UPDATE pc_info
               SET is_online=1,
                   last_seen=CURRENT_TIMESTAMP,
                   ip_address=?
               WHERE id = ?
               ''', (info.get('ip_address'), pc_id))

    # 동적 정보만 pc_status에 저장
    db.execute('''
               INSERT INTO pc_status (pc_id, cpu_usage, ram_used, ram_usage_percent, disk_usage,
                                      current_user, uptime, processes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ''', (
                   pc_id,
                   info.get('cpu_usage'),
                   info.get('ram_used'),
                   info.get('ram_usage_percent'),
                   info.get('disk_usage'),
                   info.get('current_user'),
                   info.get('uptime'),
                   info.get('processes')
               ))

    db.commit()
    return jsonify({'status': 'success', 'message': 'Heartbeat received'})


@app.route('/api/client/command')
def api_client_command():
    """클라이언트 명령 폴링 (Long-polling)"""
    machine_id = request.args.get('machine_id')
    timeout = int(request.args.get('timeout', 10))

    db = get_db()
    pc = db.execute('SELECT id FROM pc_info WHERE machine_id=?', (machine_id,)).fetchone()

    if not pc:
        return jsonify({'command_id': None, 'command_type': None, 'command_data': None})

    start_time = time.time()
    while time.time() - start_time < timeout:
        cmd = db.execute(
            'SELECT id, command_type, command_data FROM pc_command WHERE pc_id = ? AND status = ? ORDER BY priority DESC, created_at ASC LIMIT 1',
            (pc['id'], 'pending')
        ).fetchone()

        if cmd:
            db.execute('UPDATE pc_command SET status=?, started_at=CURRENT_TIMESTAMP WHERE id=?',
                      ('executing', cmd['id']))
            db.commit()
            return jsonify({
                'command_id': cmd['id'],
                'command_type': cmd['command_type'],
                'command_data': cmd['command_data']
            })

        time.sleep(0.5)

    return jsonify({'command_id': None, 'command_type': None, 'command_data': None})


@app.route('/api/client/command/result', methods=['POST'])
def api_client_command_result():
    """클라이언트 명령 실행 결과 보고"""
    data = request.json

    if not data or 'machine_id' not in data or 'command_id' not in data:
        return jsonify({
            'status': 'error',
            'message': 'machine_id와 command_id가 필요합니다'
        }), 400

    db = get_db()

    # PC 확인
    pc = db.execute('SELECT id FROM pc_info WHERE machine_id=?', (data['machine_id'],)).fetchone()
    if not pc:
        return jsonify({'status': 'error', 'message': 'PC not found'}), 404

    # 명령 확인
    cmd = db.execute('SELECT id FROM pc_command WHERE id=? AND pc_id=?',
                     (data['command_id'], pc['id'])).fetchone()
    if not cmd:
        return jsonify({'status': 'error', 'message': 'Command not found'}), 404

    # 결과 저장
    cmd_status = 'completed' if data.get('status') == 'completed' else 'error'
    db.execute('''
        UPDATE pc_command 
        SET status=?, result=?, error_message=?, completed_at=CURRENT_TIMESTAMP 
        WHERE id=?
    ''', (cmd_status, data.get('result'), data.get('error_message'), data['command_id']))
    db.commit()

    print(f"[+] 명령 실행 결과: PC={data['machine_id']}, CMD={data['command_id']}, "
          f"STATUS={data.get('status')}, RESULT={data.get('result')}")

    return jsonify({'status': 'success', 'message': 'Result received'})


# ==================== 앱 실행 ====================

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050, debug=False)