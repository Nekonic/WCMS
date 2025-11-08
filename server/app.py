from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3, bcrypt, os, json, time

app = Flask(__name__)
app.secret_key = 'woosuk25'
DB_PATH = os.path.join(os.path.dirname(__file__), 'db.sqlite3')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ==================== 웹 UI 라우트 ====================

@app.route('/')
def index():
    room = request.args.get('room', '1실습실')
    db = get_db()

    # pc_info와 최신 pc_status JOIN
    pcs_raw = db.execute('SELECT * FROM pc_info WHERE room_name=?', (room,)).fetchall()
    pcs = []

    for pc in pcs_raw:
        p = dict(pc)
        status = db.execute(
            'SELECT * FROM pc_status WHERE pc_id=? ORDER BY created_at DESC LIMIT 1',
            (pc['id'],)
        ).fetchone()

        if status:
            for key in ['cpu_usage', 'ram_total', 'ram_used', 'disk_info', 'os_edition']:
                p[key] = status[key] if key in status.keys() else None
        else:
            p.update({
                'cpu_usage': None,
                'ram_total': 0,
                'ram_used': 0,
                'disk_info': None,
                'os_edition': None
            })
        pcs.append(p)

    return render_template('index.html', pcs=pcs, room=room, admin=session.get('admin'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        db = get_db()

        admin = db.execute('SELECT * FROM admins WHERE username=?', (username,)).fetchone()
        if admin and bcrypt.checkpw(password.encode(), admin['password_hash'].encode()):
            session['admin'] = username
            return redirect(url_for('index'))

        return render_template('login.html', error='아이디 또는 비밀번호가 올바르지 않습니다.')

    return render_template('login.html')


@app.route('/logout', methods=['POST'])
def logout():
    session.pop('admin', None)
    return redirect(url_for('index'))


@app.route('/layout/editor')
def layout_editor():
    if not session.get('admin'):
        return redirect(url_for('login'))

    room = request.args.get('room', '1실습실')
    db = get_db()
    pcs = db.execute('SELECT * FROM pc_info WHERE room_name=?', (room,)).fetchall()

    return render_template('layout_editor.html', room=room, pcs=[dict(pc) for pc in pcs])


# ==================== 레이아웃 API ====================

@app.route('/api/layout/map/<room_name>', methods=['GET', 'POST'])
def manage_layout_map(room_name):
    if request.method == 'POST':
        if not session.get('admin'):
            return jsonify({'error': 'Unauthorized'}), 401

        data = request.json
        db = get_db()

        # 기존 배치 삭제
        db.execute('DELETE FROM seat_map WHERE room_name=?', (room_name,))

        # 새 배치 저장
        for seat in data.get('seats', []):
            if seat.get('pc_id'):
                db.execute('''
                           INSERT INTO seat_map (room_name, row, col, pc_id)
                           VALUES (?, ?, ?, ?)
                           ''', (room_name, seat['row'], seat['col'], seat['pc_id']))

        # 레이아웃 설정 업데이트
        db.execute('''
            INSERT OR REPLACE INTO seat_layout (room_name, cols, rows)
            VALUES (?, ?, ?)
        ''', (room_name, data['cols'], data['rows']))

        db.commit()
        return jsonify({'status': 'success', 'message': '배치 저장 완료'})

    else:  # GET 요청
        db = get_db()
        layout = db.execute('SELECT * FROM seat_layout WHERE room_name=?', (room_name,)).fetchone()
        seats = db.execute('SELECT * FROM seat_map WHERE room_name=?', (room_name,)).fetchall()

        if not layout:
            return jsonify({'error': 'Layout not found'}), 404

        return jsonify({
            'rows': layout['rows'],
            'cols': layout['cols'],
            'seats': [dict(s) for s in seats]
        })


# ==================== PC 제어 API ====================

@app.route('/api/pc/<int:pc_id>/command', methods=['POST'])
def api_pc_command(pc_id):
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json
    cmd_type = data.get('type')  # 'shutdown', 'reboot', 'install', 'execute'
    cmd_data = data.get('data', {})

    db = get_db()
    db.execute(
        'INSERT INTO pc_command (pc_id, command_type, command_data) VALUES (?, ?, ?)',
        (pc_id, cmd_type, json.dumps(cmd_data))
    )
    db.commit()

    return jsonify({'message': f'명령 저장됨: {cmd_type}'})


@app.route('/api/pc/<int:pc_id>/shutdown', methods=['POST'])
def api_pc_shutdown(pc_id):
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 401

    db = get_db()
    db.execute(
        'INSERT INTO pc_command (pc_id, command_type, command_data) VALUES (?, ?, ?)',
        (pc_id, 'shutdown', json.dumps({}))
    )
    db.commit()

    return jsonify({'message': f'PC {pc_id} 종료 명령 저장됨'})


@app.route('/api/pc/<int:pc_id>/reboot', methods=['POST'])
def api_pc_reboot(pc_id):
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 401

    db = get_db()
    db.execute(
        'INSERT INTO pc_command (pc_id, command_type, command_data) VALUES (?, ?, ?)',
        (pc_id, 'reboot', json.dumps({}))
    )
    db.commit()

    return jsonify({'message': f'PC {pc_id} 재시작 명령 저장됨'})


@app.route('/api/pc/<int:pc_id>', methods=['GET'])
def api_pc_detail(pc_id):
    db = get_db()
    pc = db.execute('SELECT * FROM pc_info WHERE id=?', (pc_id,)).fetchone()
    status = db.execute('SELECT * FROM pc_status WHERE pc_id=? ORDER BY created_at DESC LIMIT 1', (pc_id,)).fetchone()

    result = dict(pc) if pc else {}

    if status:
        for key in ['cpu_model', 'ram_total', 'disk_info', 'os_edition', 'ip_address', 'mac_address']:
            result[key] = status[key] if key in status.keys() else None

    return jsonify(result)


# ==================== 클라이언트 API ====================

@app.route('/api/client/command')
def api_client_command():
    machine_id = request.args.get('machine_id')
    timeout = int(request.args.get('timeout', 30))
    db = get_db()

    # machine_id로 pc_id 조회
    pc = db.execute('SELECT id FROM pc_info WHERE machine_id=?', (machine_id,)).fetchone()
    if not pc:
        return jsonify({'command_type': None, 'command_data': None})

    # Long-polling: timeout 동안 명령 대기
    start_time = time.time()
    while time.time() - start_time < timeout:
        cmd = db.execute(
            'SELECT id, command_type, command_data FROM pc_command WHERE pc_id=? AND executed=0 LIMIT 1',
            (pc['id'],)
        ).fetchone()

        if cmd:
            db.execute('UPDATE pc_command SET executed=1 WHERE id=?', (cmd['id'],))
            db.commit()
            return jsonify({
                'command_type': cmd['command_type'],
                'command_data': cmd['command_data']
            })

        time.sleep(1)  # 1초 대기 후 다시 확인

    # 타임아웃: 명령 없음
    return jsonify({'command_type': None, 'command_data': None})


@app.route('/api/client/register', methods=['POST'])
def api_client_register():
    data = request.json
    db = get_db()

    try:
        db.execute('''
                   INSERT INTO pc_info (machine_id, hostname, room_name, seat_number, is_online)
                   VALUES (?, ?, ?, ?, 1)
                   ''', (data['machine_id'], data['hostname'], data['room_name'], data['seat_number']))
        db.commit()

        return jsonify({'status': 'success', 'message': '등록 완료'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/client/heartbeat', methods=['POST'])
def api_client_heartbeat():
    data = request.json
    db = get_db()

    # pc_info 업데이트
    pc = db.execute('SELECT id FROM pc_info WHERE machine_id=?', (data['machine_id'],)).fetchone()
    if not pc:
        return jsonify({'status': 'error', 'message': 'PC not registered'}), 404

    db.execute('UPDATE pc_info SET is_online=1, last_seen=CURRENT_TIMESTAMP WHERE machine_id=?', (data['machine_id'],))

    # pc_status 삽입
    info = data.get('system_info', {})

    db.execute('''
               INSERT INTO pc_status (pc_id, cpu_model, cpu_cores, cpu_threads, cpu_usage,
                                      ram_total, ram_used, ram_usage_percent, ram_type,
                                      disk_info, os_edition, os_version, os_build, os_activated,
                                      ip_address, mac_address, gpu_model, gpu_vram,
                                      current_user, uptime)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ''', (
                   pc['id'],
                   info.get('cpu_model'), info.get('cpu_cores'), info.get('cpu_threads'), info.get('cpu_usage'),
                   info.get('ram_total'), info.get('ram_used'), info.get('ram_usage_percent'), info.get('ram_type'),
                   info.get('disk_info'), info.get('os_edition'), info.get('os_version'), info.get('os_build'),
                   info.get('os_activated'),
                   info.get('ip_address'), info.get('mac_address'), info.get('gpu_model'), info.get('gpu_vram'),
                   info.get('current_user'), info.get('uptime')
               ))

    db.commit()
    return jsonify({'status': 'success', 'message': 'Heartbeat received'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050, debug=False)
