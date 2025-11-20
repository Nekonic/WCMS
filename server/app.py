from flask import Flask, render_template, request, redirect, url_for, session, jsonify, g
import sqlite3
import bcrypt
import os
import json
import time
import platform

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


def execute_query(query, params=None, fetch_one=False, fetch_all=False, commit=False):
    """DB 쿼리 실행 헬퍼"""
    db = get_db()
    cursor = db.execute(query, params or [])

    if commit:
        db.commit()
        return cursor.lastrowid if cursor.lastrowid else cursor.rowcount

    if fetch_one:
        return cursor.fetchone()
    if fetch_all:
        return cursor.fetchall()
    return cursor


def get_pc_by_id(pc_id):
    """PC ID로 PC 조회"""
    return execute_query('SELECT * FROM pc_info WHERE id=?', [pc_id], fetch_one=True)


def get_pc_by_machine_id(machine_id):
    """Machine ID로 PC 조회"""
    return execute_query('SELECT id FROM pc_info WHERE machine_id=?', [machine_id], fetch_one=True)


def validate_not_null(value, default):
    """NOT NULL 필드 기본값 보정"""
    try:
        if isinstance(default, int):
            return int(value) if value is not None else default
        elif isinstance(default, float):
            return float(value) if value is not None else default
        return value if value else default
    except (ValueError, TypeError):
        return default


# ==================== 데코레이터 ====================

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


@app.route('/command/test')
@require_admin
def command_test():
    """명령 실행 테스트 페이지"""
    return render_template('command_test.html')


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
    specs = execute_query('SELECT * FROM pc_specs WHERE pc_id=?', [pc_id], fetch_one=True)
    if specs:
        pc_dict.update(dict(specs))
        # 디스크 파싱 및 사용량 병합
        disk_raw = pc_dict.get('disk_info') or '{}'
        try:
            disk_parsed = json.loads(disk_raw) if isinstance(disk_raw, str) else disk_raw
        except Exception:
            disk_parsed = {}

        # 디스크 사용량 정보 병합
        disk_usage_raw = pc_dict.get('disk_usage') or '{}'
        try:
            disk_usage = json.loads(disk_usage_raw) if isinstance(disk_usage_raw, str) else disk_usage_raw
            # disk_parsed에 사용량 정보 추가
            for dev, usage_info in disk_usage.items():
                if dev in disk_parsed:
                    disk_parsed[dev].update(usage_info)
        except Exception:
            pass

        pc_dict['disk_info_parsed'] = disk_parsed
        # OS Unknown 보강
        if not pc_dict.get('os_edition') or pc_dict.get('os_edition') == 'Unknown':
            pc_dict['os_edition'] = f"{platform.system()} {platform.release()}"

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

    if not get_pc_by_id(pc_id):
        return jsonify({'status': 'error', 'message': 'PC를 찾을 수 없습니다'}), 404

    execute_query(
        'INSERT INTO pc_command (pc_id, command_type, command_data) VALUES (?, ?, ?)',
        (pc_id, data.get('type'), json.dumps(data.get('data', {}))),
        commit=True
    )
    return jsonify({'status': 'success', 'message': '명령 전송 완료'})


@app.route('/api/pc/<int:pc_id>/shutdown', methods=['POST'])
@require_admin
def api_pc_shutdown(pc_id):
    """PC 종료"""
    return _send_pc_command(pc_id, 'shutdown', {}, '종료')


@app.route('/api/pc/<int:pc_id>/reboot', methods=['POST'])
@require_admin
def api_pc_reboot(pc_id):
    """PC 재시작"""
    return _send_pc_command(pc_id, 'reboot', {}, '재시작')


def _send_pc_command(pc_id, cmd_type, cmd_data, action_name):
    """명령 전송 헬퍼 (내부용)"""
    if not get_pc_by_id(pc_id):
        return jsonify({'status': 'error', 'message': 'PC를 찾을 수 없습니다'}), 404

    execute_query(
        'INSERT INTO pc_command (pc_id, command_type, command_data) VALUES (?, ?, ?)',
        (pc_id, cmd_type, json.dumps(cmd_data)),
        commit=True
    )
    return jsonify({'status': 'success', 'message': f'{action_name} 명령 전송 완료'})


@app.route('/api/pc/<int:pc_id>/account/create', methods=['POST'])
@require_admin
def api_create_account(pc_id):
    """Windows 계정 생성 명령 전송"""
    data = request.json
    if not data or not all(k in data for k in ['username', 'password']):
        return jsonify({'status': 'error', 'message': 'username과 password 필드가 필요합니다'}), 400

    return _send_account_command(pc_id, 'create_user', {
        'username': data['username'],
        'password': data['password'],
        'full_name': data.get('full_name'),
        'comment': data.get('comment')
    }, '계정 생성')


@app.route('/api/pc/<int:pc_id>/account/delete', methods=['POST'])
@require_admin
def api_delete_account(pc_id):
    """Windows 계정 삭제 명령 전송"""
    data = request.json
    if not data or 'username' not in data:
        return jsonify({'status': 'error', 'message': 'username 필드가 필요합니다'}), 400

    return _send_account_command(pc_id, 'delete_user', {'username': data['username']}, '계정 삭제')


@app.route('/api/pc/<int:pc_id>/account/password', methods=['POST'])
@require_admin
def api_change_password(pc_id):
    """Windows 계정 비밀번호 변경 명령 전송"""
    data = request.json
    if not data or not all(k in data for k in ['username', 'new_password']):
        return jsonify({'status': 'error', 'message': 'username과 new_password 필드가 필요합니다'}), 400

    return _send_account_command(pc_id, 'change_password', {
        'username': data['username'],
        'new_password': data['new_password']
    }, '비밀번호 변경')


def _send_account_command(pc_id, cmd_type, cmd_data, action_name):
    """계정 관리 명령 전송 헬퍼"""
    if not get_pc_by_id(pc_id):
        return jsonify({'status': 'error', 'message': 'PC를 찾을 수 없습니다'}), 404

    execute_query(
        'INSERT INTO pc_command (pc_id, command_type, command_data) VALUES (?, ?, ?)',
        (pc_id, cmd_type, json.dumps(cmd_data)),
        commit=True
    )
    return jsonify({'status': 'success', 'message': f'{action_name} 명령 전송 완료'})


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
    """클라이언트 등록 (machine_id 기반 중복 방지)"""
    data = request.json
    if not data or 'machine_id' not in data:
        return jsonify({'status': 'error', 'message': 'machine_id is required'}), 400

    db = get_db()
    machine_id = data['machine_id']
    hostname = data.get('hostname') or 'Unknown-PC'
    mac_address = data.get('mac_address') or '00:00:00:00:00:00'
    ip_address = data.get('ip_address')

    # machine_id로 기존 PC 찾기 (중복 방지)
    existing = db.execute('SELECT id FROM pc_info WHERE machine_id=?', (machine_id,)).fetchone()

    # disk_info 정규화
    disk_info = data.get('disk_info')
    if isinstance(disk_info, str):
        try:
            disk_info = json.loads(disk_info)
        except Exception:
            disk_info = {}
    if not isinstance(disk_info, (dict, list)):
        disk_info = {}
    disk_info_str = json.dumps(disk_info)

    cpu_model = data.get('cpu_model') or 'Unknown CPU'
    cpu_cores = validate_not_null(data.get('cpu_cores'), 0)
    cpu_threads = validate_not_null(data.get('cpu_threads'), cpu_cores)
    ram_total = validate_not_null(data.get('ram_total'), 0)
    os_edition = data.get('os_edition') or 'Unknown'
    os_version = data.get('os_version') or 'Unknown'

    if existing:
        pc_id = existing['id']
        # 기존 PC 업데이트 (호스트명, IP, MAC 주소 변경 가능성 대비)
        db.execute('''
            UPDATE pc_info 
            SET hostname=?, ip_address=?, mac_address=?, is_online=1, last_seen=CURRENT_TIMESTAMP, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
        ''', (hostname, ip_address, mac_address, pc_id))
        db.commit()

        # pc_specs 업데이트
        specs = db.execute('SELECT id FROM pc_specs WHERE pc_id=?', (pc_id,)).fetchone()
        if specs:
            db.execute('''
                UPDATE pc_specs 
                SET cpu_model=?, cpu_cores=?, cpu_threads=?, ram_total=?, disk_info=?, os_edition=?, os_version=?, updated_at=CURRENT_TIMESTAMP 
                WHERE pc_id=?
            ''', (cpu_model, cpu_cores, cpu_threads, ram_total, disk_info_str, os_edition, os_version, pc_id))
        else:
            db.execute('''
                INSERT INTO pc_specs (pc_id, cpu_model, cpu_cores, cpu_threads, ram_total, disk_info, os_edition, os_version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (pc_id, cpu_model, cpu_cores, cpu_threads, ram_total, disk_info_str, os_edition, os_version))
        db.commit()

        print(f"[+] PC 업데이트: machine_id={machine_id}, hostname={hostname}, pc_id={pc_id}")
        return jsonify({'status': 'success', 'message': '업데이트 완료', 'pc_id': pc_id}), 200

    # 신규 등록
    cursor = db.execute('''
        INSERT INTO pc_info (machine_id, hostname, ip_address, mac_address, is_online, created_at, last_seen)
        VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    ''', (machine_id, hostname, ip_address, mac_address))
    pc_id = cursor.lastrowid

    db.execute('''
        INSERT INTO pc_specs (pc_id, cpu_model, cpu_cores, cpu_threads, ram_total, disk_info, os_edition, os_version)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (pc_id, cpu_model, cpu_cores, cpu_threads, ram_total, disk_info_str, os_edition, os_version))
    db.commit()

    print(f"[+] PC 신규 등록: machine_id={machine_id}, hostname={hostname}, pc_id={pc_id}")
    return jsonify({'status': 'success', 'message': '등록 완료', 'pc_id': pc_id}), 200


@app.route('/api/client/heartbeat', methods=['POST'])
def api_client_heartbeat():
    """클라이언트 하트비트"""
    data = request.json
    if not data or 'machine_id' not in data:
        return jsonify({'status': 'error', 'message': 'machine_id is required'}), 400

    pc = get_pc_by_machine_id(data['machine_id'])
    if not pc:
        return jsonify({'status': 'error', 'message': 'PC not registered'}), 404

    info = data.get('system_info', {})

    # pc_info 업데이트
    execute_query(
        'UPDATE pc_info SET is_online=1, last_seen=CURRENT_TIMESTAMP, ip_address=? WHERE id=?',
        (info.get('ip_address'), pc['id']),
        commit=True
    )

    # pc_status 삽입 (기본값 보정)
    execute_query(
        '''INSERT INTO pc_status (pc_id, cpu_usage, ram_used, ram_usage_percent, disk_usage, current_user, uptime, processes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        (pc['id'],
         validate_not_null(info.get('cpu_usage'), 0.0),
         validate_not_null(info.get('ram_used'), 0),
         validate_not_null(info.get('ram_usage_percent'), 0.0),
         info.get('disk_usage'),
         info.get('current_user'),
         validate_not_null(info.get('uptime'), 0),
         info.get('processes')),
        commit=True
    )

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

    # 결과 저장 ('skipped' 포함 허용)
    req_status = (data.get('status') or '').lower()
    if req_status not in ('completed', 'error', 'skipped'):
        req_status = 'error'
    db.execute('''
        UPDATE pc_command 
        SET status=?, result=?, error_message=?, completed_at=CURRENT_TIMESTAMP 
        WHERE id=?
    ''', (req_status, data.get('result'), data.get('error_message'), data['command_id']))
    db.commit()

    print(f"[+] 명령 실행 결과: PC={data['machine_id']}, CMD={data['command_id']}, STATUS={req_status}")

    return jsonify({'status': 'success', 'message': 'Result received'})


@app.route('/api/pcs/bulk-command', methods=['POST'])
@require_admin
def api_bulk_command():
    """여러 PC에 동시에 명령 전송"""
    data = request.json
    pc_ids = data.get('pc_ids', [])
    command_type = data.get('command_type')
    command_data = data.get('command_data', {})

    if not pc_ids or not command_type:
        return jsonify({'error': 'pc_ids와 command_type은 필수입니다'}), 400

    db = get_db()
    results = []

    for pc_id in pc_ids:
        try:
            cursor = db.execute('''
                INSERT INTO pc_command (pc_id, command_type, command_data, status, priority)
                VALUES (?, ?, ?, 'pending', 5)
            ''', (pc_id, command_type, json.dumps(command_data)))

            command_id = cursor.lastrowid
            db.commit()

            results.append({
                'pc_id': pc_id,
                'command_id': command_id,
                'status': 'success'
            })
            print(f"[+] 일괄 명령 전송: PC_ID={pc_id}, TYPE={command_type}")
        except Exception as e:
            results.append({
                'pc_id': pc_id,
                'status': 'error',
                'message': str(e)
            })
            print(f"[!] 명령 전송 실패: PC_ID={pc_id}, ERROR={e}")

    return jsonify({
        'total': len(pc_ids),
        'success': len([r for r in results if r['status'] == 'success']),
        'failed': len([r for r in results if r['status'] == 'error']),
        'results': results
    })


@app.route('/api/pc/<int:pc_id>/commands/clear', methods=['DELETE'])
@require_admin
def api_clear_pc_commands(pc_id):
    """특정 PC의 대기 중인 명령 모두 삭제"""
    try:
        deleted_count = execute_query(
            "DELETE FROM pc_command WHERE pc_id = ? AND status = 'pending'",
            [pc_id],
            commit=True
        )
        print(f"[+] 명령 초기화: PC_ID={pc_id}, 삭제={deleted_count}개")
        return jsonify({
            'status': 'success',
            'message': f'{deleted_count}개의 대기 중인 명령이 삭제되었습니다.',
            'deleted_count': deleted_count
        })
    except Exception as e:
        print(f"[!] 명령 삭제 실패: PC_ID={pc_id}, ERROR={e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/pcs/commands/clear', methods=['DELETE'])
@require_admin
def api_clear_all_commands():
    """여러 PC의 대기 중인 명령 일괄 삭제"""
    pc_ids = request.json.get('pc_ids', [])
    if not pc_ids:
        return jsonify({'error': 'pc_ids는 필수입니다'}), 400

    results, total_deleted = [], 0
    for pc_id in pc_ids:
        try:
            deleted = execute_query(
                "DELETE FROM pc_command WHERE pc_id = ? AND status = 'pending'",
                [pc_id],
                commit=True
            )
            total_deleted += deleted
            results.append({'pc_id': pc_id, 'deleted_count': deleted, 'status': 'success'})
            print(f"[+] 명령 초기화: PC_ID={pc_id}, 삭제={deleted}개")
        except Exception as e:
            results.append({'pc_id': pc_id, 'status': 'error', 'message': str(e)})
            print(f"[!] 명령 삭제 실패: PC_ID={pc_id}, ERROR={e}")

    return jsonify({
        'total': len(pc_ids),
        'success': len([r for r in results if r['status'] == 'success']),
        'failed': len([r for r in results if r['status'] == 'error']),
        'total_deleted': total_deleted,
        'results': results
    })


@app.route('/api/commands/pending', methods=['GET'])
@require_admin
def api_get_pending_commands():
    """대기 중인 명령 목록 조회"""
    db = get_db()

    try:
        commands = db.execute('''
            SELECT 
                c.id, c.pc_id, c.command_type, c.command_data, 
                c.status, c.priority, c.created_at,
                p.hostname, p.seat_number, p.room_name
            FROM pc_command c
            JOIN pc_info p ON c.pc_id = p.id
            WHERE c.status = 'pending'
            ORDER BY c.priority DESC, c.created_at ASC
        ''').fetchall()

        result = []
        for cmd in commands:
            result.append({
                'command_id': cmd['id'],
                'pc_id': cmd['pc_id'],
                'hostname': cmd['hostname'],
                'seat_number': cmd['seat_number'],
                'room_name': cmd['room_name'],
                'command_type': cmd['command_type'],
                'command_data': cmd['command_data'],
                'priority': cmd['priority'],
                'created_at': cmd['created_at']
            })

        return jsonify({
            'total': len(result),
            'commands': result
        })
    except Exception as e:
        print(f"[!] 대기 명령 조회 실패: ERROR={e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/commands/results', methods=['POST'])
@require_admin
def api_get_command_results():
    """명령 실행 결과 조회 (폴링용)"""
    data = request.json
    command_ids = data.get('command_ids', [])

    if not command_ids:
        return jsonify({'error': 'command_ids는 필수입니다'}), 400

    db = get_db()
    results = []

    try:
        for cmd_id in command_ids:
            cmd = db.execute('''
                SELECT 
                    c.id, c.pc_id, c.command_type, c.status, 
                    c.result, c.error_message, c.completed_at,
                    p.hostname, p.seat_number
                FROM pc_command c
                JOIN pc_info p ON c.pc_id = p.id
                WHERE c.id = ?
            ''', (cmd_id,)).fetchone()

            if cmd:
                results.append({
                    'command_id': cmd['id'],
                    'pc_id': cmd['pc_id'],
                    'hostname': cmd['hostname'],
                    'seat_number': cmd['seat_number'],
                    'command_type': cmd['command_type'],
                    'status': cmd['status'],
                    'result': cmd['result'],
                    'error_message': cmd['error_message'],
                    'completed_at': cmd['completed_at']
                })

        return jsonify({
            'total': len(results),
            'results': results
        })
    except Exception as e:
        print(f"[!] 명령 결과 조회 실패: ERROR={e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ==================== 앱 실행 ====================

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050, debug=False)