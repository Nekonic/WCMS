from flask import Flask, render_template, request, redirect, url_for, session, jsonify, g
import sqlite3, bcrypt, os, json, time

app = Flask(__name__)
app.secret_key = 'woosuk25'
DB_PATH = os.path.join(os.path.dirname(__file__), 'db.sqlite3')


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA journal_mode=WAL')
        g.db.execute('PRAGMA busy_timeout=5000')
    return g.db


@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()


@app.route('/')
def index():
    room = request.args.get('room')

    if not room:
        return redirect(url_for('index', room='1실습실'))

    db = get_db()
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
            p.update({'cpu_usage': None, 'ram_total': 0, 'ram_used': 0, 'disk_info': None, 'os_edition': None})
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

        return render_template('login.html', error='로그인 실패')

    return render_template('login.html')


@app.route('/logout', methods=['POST'])
def logout():
    session.pop('admin', None)
    return redirect(url_for('index'))


@app.route('/layout/editor')
def layout_editor():
    if not session.get('admin'):
        return redirect(url_for('login'))

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


@app.route('/api/pc/<int:pc_id>')
def api_pc_detail(pc_id):
    db = get_db()
    pc = db.execute('SELECT * FROM pc_info WHERE id=?', (pc_id,)).fetchone()
    if not pc:
        return jsonify({"error": "PC not found"}), 404

    pc_dict = dict(pc)
    status = db.execute(
        'SELECT * FROM pc_status WHERE pc_id=? ORDER BY created_at DESC LIMIT 1',
        (pc_id,)
    ).fetchone()
    if status:
        pc_dict.update(dict(status))
    return jsonify(pc_dict)

@app.route('/api/layout/map/<room_name>', methods=['GET', 'POST'])
def manage_layout_map(room_name):
    db = get_db()

    if request.method == 'POST':
        if not session.get('admin'):
            return jsonify({'error': 'Unauthorized'}), 401

        data = request.json

        # 1. 기존 배치 삭제
        db.execute('DELETE FROM seat_map WHERE room_name=?', (room_name,))

        # 2. 해당 실습실에 있던 PC들을 미배치로 변경
        db.execute('UPDATE pc_info SET room_name=NULL WHERE room_name=?', (room_name,))

        # 3. 새로운 배치 저장
        for seat in data.get('seats', []):
            if seat.get('pc_id'):
                # seat_map에 저장
                db.execute('''
                           INSERT INTO seat_map (room_name, row, col, pc_id)
                           VALUES (?, ?, ?, ?)
                           ''', (room_name, seat['row'], seat['col'], seat['pc_id']))

                # pc_info 테이블 업데이트 (중요!)
                db.execute('''
                           UPDATE pc_info SET room_name=?, seat_number=? WHERE id = ?
                           ''', (room_name, str(seat['col'] + 1)+", "+str(seat['row'] + 1), seat['pc_id']))

        # 4. 레이아웃 저장
        db.execute('''
            INSERT OR REPLACE INTO seat_layout (room_name, cols, rows)
            VALUES (?, ?, ?)
        ''', (room_name, data.get('cols', 8), data.get('rows', 5)))

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


@app.route('/api/pc/<int:pc_id>/command', methods=['POST'])
def api_pc_command(pc_id):
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json
    db = get_db()

    db.execute('''
               INSERT INTO pc_command (pc_id, command_type, command_data)
               VALUES (?, ?, ?)
               ''', (pc_id, data.get('type'), json.dumps(data.get('data', {}))))

    db.commit()
    return jsonify({'message': '명령 전송 완료'})


@app.route('/api/client/command')
def api_client_command():
    machine_id = request.args.get('machine_id')
    timeout = int(request.args.get('timeout', 10))

    db = get_db()
    pc = db.execute('SELECT id FROM pc_info WHERE machine_id=?', (machine_id,)).fetchone()

    if not pc:
        return jsonify({'command_type': None, 'command_data': None})

    start_time = time.time()
    while time.time() - start_time < timeout:
        cmd = db.execute('''
                         SELECT id, command_type, command_data
                         FROM pc_command
                         WHERE pc_id = ?
                           AND executed = 0
                         LIMIT 1
                         ''', (pc['id'],)).fetchone()

        if cmd:
            db.execute('UPDATE pc_command SET executed=1 WHERE id=?', (cmd['id'],))
            db.commit()
            return jsonify({'command_type': cmd['command_type'], 'command_data': cmd['command_data']})

        time.sleep(0.5)

    return jsonify({'command_type': None, 'command_data': None})


@app.route('/api/client/register', methods=['POST'])
def api_client_register():
    data = request.json
    db = get_db()

    existing = db.execute('SELECT id, room_name, seat_number FROM pc_info WHERE machine_id=?',
                          (data['machine_id'],)).fetchone()

    if existing:
        return jsonify({
            'status': 'already_registered',
            'room_name': existing['room_name'],
            'seat_number': existing['seat_number']
        }), 200

    db.execute('''
               INSERT INTO pc_info (machine_id, hostname, ip_address, is_online, room_name, seat_number)
               VALUES (?, ?, ?, 1, NULL, NULL)
               ''', (data['machine_id'], data.get('hostname'), data.get('ip_address')))

    db.commit()
    print(f"[+] PC 등록 (미배치): {data['machine_id']}")

    return jsonify({'status': 'success', 'message': '등록 완료'}), 200


@app.route('/api/client/heartbeat', methods=['POST'])
def api_client_heartbeat():
    data = request.json
    db = get_db()

    pc = db.execute('SELECT id FROM pc_info WHERE machine_id=?', (data['machine_id'],)).fetchone()

    if not pc:
        return jsonify({'status': 'error', 'message': 'PC not registered'}), 404

    db.execute('UPDATE pc_info SET is_online=1, last_seen=CURRENT_TIMESTAMP WHERE machine_id=?', (data['machine_id'],))

    info = data.get('system_info', {})
    db.execute('''
               INSERT INTO pc_status (pc_id, cpu_model, cpu_usage, ram_total, ram_used, disk_info, os_edition,
                                      ip_address, mac_address, current_user)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ''', (
                   pc['id'],
                   info.get('cpu_model'),
                   info.get('cpu_usage'),
                   info.get('ram_total'),
                   info.get('ram_used'),
                   info.get('disk_info'),
                   info.get('os_edition'),
                   info.get('ip_address'),
                   info.get('mac_address'),
                   info.get('current_user')
               ))

    db.commit()
    return jsonify({'status': 'success'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050, debug=False)
