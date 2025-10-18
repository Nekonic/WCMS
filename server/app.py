from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3, bcrypt, os

app = Flask(__name__)
app.secret_key = 'woosuk25'
DB_PATH = os.path.join(os.path.dirname(__file__), 'db.sqlite3')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    room = request.args.get('room', '1실습실')
    db = get_db()
    pcs_raw = db.execute('SELECT * FROM pc_info WHERE room_name=?', (room,)).fetchall()
    pcs = []
    for pc in pcs_raw:
        p = dict(pc)
        status = db.execute('SELECT * FROM pc_status WHERE pc_id=? ORDER BY created_at DESC LIMIT 1', (pc['id'],)).fetchone()
        for key in ['cpu_model','ram_total','disk_info','os_edition']:
            p[key] = status[key] if status and key in status.keys() else None
        pcs.append(p)
    return render_template('index.html', pcs=pcs, room=room)

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username, password = request.form['username'], request.form['password']
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

@app.route('/api/pc/<int:pc_id>')
def api_pc_detail(pc_id):
    db = get_db()
    pc = db.execute('SELECT * FROM pc_info WHERE id=?', (pc_id,)).fetchone()
    status = db.execute('SELECT * FROM pc_status WHERE pc_id=? ORDER BY created_at DESC LIMIT 1', (pc_id,)).fetchone()
    result = dict(pc) if pc else {}
    if status:
        for key in ['cpu_model','ram_total','disk_info','os_edition','ip_address','mac_address']:
            result[key] = status[key] if key in status.keys() else None
    return jsonify(result)

@app.route('/api/pc/<int:pc_id>/shutdown', methods=['POST'])
def api_pc_shutdown(pc_id):
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 401
    return jsonify({'message': f'PC {pc_id} 종료 명령 전송됨'})

@app.route('/api/pc/<int:pc_id>/reboot', methods=['POST'])
def api_pc_reboot(pc_id):
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 401
    return jsonify({'message': f'PC {pc_id} 재시작 명령 전송됨'})


# 클라이언트 등록
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


# 클라이언트 상태 업데이트 (heartbeat)
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


# 명령 확인 (폴링)
@app.route('/api/client/command', methods=['GET'])
def api_client_command():
    machine_id = request.args.get('machine_id')
    # TODO: 명령 큐 구현 (나중에)
    return jsonify({'command': None})

if __name__ == '__main__':
    app.run(debug=True)
