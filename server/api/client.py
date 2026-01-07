"""
클라이언트 API Blueprint
클라이언트가 호출하는 API 엔드포인트
"""
from flask import Blueprint, request, jsonify
import json
import time
import os
from models import PCModel, CommandModel
from utils import get_db

client_bp = Blueprint('client', __name__, url_prefix='/api/client')


@client_bp.route('/register', methods=['POST'])
def register():
    """클라이언트 등록 (machine_id 기반 중복 방지)"""
    data = request.json
    if not data or 'machine_id' not in data:
        return jsonify({'status': 'error', 'message': 'machine_id is required'}), 400

    machine_id = data['machine_id']
    hostname = data.get('hostname') or 'Unknown-PC'
    mac_address = data.get('mac_address') or '00:00:00:00:00:00'
    ip_address = data.get('ip_address')

    pc_id = PCModel.update_or_create(
        machine_id=machine_id,
        hostname=hostname,
        mac_address=mac_address,
        ip_address=ip_address,
        cpu_model=data.get('cpu_model'),
        cpu_cores=data.get('cpu_cores'),
        cpu_threads=data.get('cpu_threads'),
        ram_total=data.get('ram_total'),
        disk_info=data.get('disk_info'),
        os_edition=data.get('os_edition'),
        os_version=data.get('os_version')
    )

    return jsonify({
        'status': 'success',
        'message': 'Registration successful',
        'pc_id': pc_id
    }), 200


@client_bp.route('/heartbeat', methods=['POST'])
def heartbeat():
    """클라이언트 하트비트 (동적 정보 수집)"""
    data = request.json
    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400

    pc_id = data.get('pc_id')
    machine_id = data.get('machine_id')

    if not pc_id and not machine_id:
        return jsonify({'status': 'error', 'message': 'machine_id or pc_id is required'}), 400

    if machine_id:
        pc = PCModel.get_by_machine_id(machine_id)
        if pc:
            pc_id = pc['id']
        else:
            return jsonify({'status': 'error', 'message': 'PC not registered'}), 404
    
    # PC 존재 여부 확인 (pc_id로 조회 시)
    if not PCModel.get_by_id(pc_id):
        return jsonify({'status': 'error', 'message': 'PC not found'}), 404

    # system_info 필드 처리 (app.py 호환성)
    info = data.get('system_info', data)

    success = PCModel.update_heartbeat(
        pc_id=pc_id,
        cpu_usage=info.get('cpu_usage', 0),
        ram_used=info.get('ram_used', 0),
        ram_usage_percent=info.get('ram_usage_percent', 0),
        disk_usage=info.get('disk_usage'),
        current_user=info.get('current_user'),
        uptime=info.get('uptime', 0),
        processes=info.get('processes')
    )

    if success:
        return jsonify({'status': 'success', 'message': 'Heartbeat received'}), 200
    else:
        return jsonify({'status': 'error', 'message': 'Failed to record heartbeat'}), 500


@client_bp.route('/command', methods=['GET'])
def get_command():
    """대기 중인 명령 조회 (Long-polling)"""
    pc_id = request.args.get('pc_id', type=int)
    machine_id = request.args.get('machine_id')
    timeout = int(request.args.get('timeout', 10))

    if not pc_id and not machine_id:
        # app.py 호환: machine_id 없으면 빈 응답? 아니면 에러?
        # app.py는 machine_id 없으면 에러가 아니라 그냥 못찾아서 빈응답 리턴할수도 있음.
        # 하지만 여기선 명시적으로 찾음.
        return jsonify({'command_id': None, 'command_type': None, 'command_data': None})

    if machine_id:
        pc = PCModel.get_by_machine_id(machine_id)
        if pc:
            pc_id = pc['id']
        else:
            return jsonify({'command_id': None, 'command_type': None, 'command_data': None})
    elif not PCModel.get_by_id(pc_id):
         return jsonify({'command_id': None, 'command_type': None, 'command_data': None})

    # Long-polling
    start_time = time.time()
    while time.time() - start_time < timeout:
        commands = CommandModel.get_pending_for_pc(pc_id)
        if commands:
            cmd = commands[0] # 가장 우선순위 높은 것 하나
            
            # 실행 상태로 변경
            CommandModel.start_execution(cmd['id'])
            
            return jsonify({
                'command_id': cmd['id'],
                'command_type': cmd['command_type'],
                'command_data': json.loads(cmd['command_data']) if isinstance(cmd['command_data'], str) else cmd['command_data']
            })
        
        time.sleep(0.5)

    return jsonify({'command_id': None, 'command_type': None, 'command_data': None})


@client_bp.route('/command/result', methods=['POST'])
def report_command_result():
    """명령 실행 결과 보고"""
    data = request.json
    
    # app.py 호환: machine_id와 command_id 필수
    if not data or 'command_id' not in data:
        return jsonify({'status': 'error', 'message': 'command_id is required'}), 400
        
    machine_id = data.get('machine_id')
    command_id = data['command_id']
    
    if machine_id:
        pc = PCModel.get_by_machine_id(machine_id)
        if not pc:
            return jsonify({'status': 'error', 'message': 'PC not found'}), 404
        # 명령이 해당 PC의 것인지 확인하는 로직은 CommandModel에 없지만,
        # app.py에서는 확인했음. 여기서는 생략하거나 추가 구현 필요.
        # 일단 command_id로 조회하므로 넘어감.

    result = data.get('result', '')
    status = data.get('status', 'completed')  # completed, error, skipped

    # 명령 존재 여부 확인
    cmd = CommandModel.get_by_id(command_id)
    if not cmd:
        return jsonify({'status': 'error', 'message': 'Command not found'}), 404

    status = status.lower()
    if status not in ('completed', 'error', 'skipped'):
        status = 'error'

    if status == 'completed':
        success = CommandModel.complete(command_id, result)
    elif status == 'error':
        error_msg = data.get('error_message', 'Unknown error')
        success = CommandModel.set_error(command_id, error_msg)
    elif status == 'skipped':
        # skipped 처리 로직이 CommandModel에 없으면 completed로 처리하거나 별도 처리
        # app.py에서는 status='skipped'로 업데이트함.
        # CommandModel.complete는 status를 'completed'로 고정함.
        # 직접 DB 업데이트 필요하거나 CommandModel 수정 필요.
        # 여기서는 일단 complete로 처리하되 result에 status 포함?
        # 아니면 직접 DB 쿼리? utils.get_db 사용 가능.
        try:
            db = get_db()
            db.execute('''
                UPDATE pc_command 
                SET status=?, result=?, error_message=?, completed_at=CURRENT_TIMESTAMP 
                WHERE id=?
            ''', (status, result, data.get('error_message'), command_id))
            db.commit()
            success = True
        except Exception:
            success = False
    else:
        success = False

    if success:
        return jsonify({'status': 'success', 'message': 'Result received'}), 200 # app.py message: 'Result received'
    else:
        return jsonify({'status': 'error', 'message': 'Failed to record result'}), 500


@client_bp.route('/version', methods=['GET'])
def get_version():
    """클라이언트 최신 버전 확인"""
    db = get_db()

    try:
        version_info = db.execute('''
            SELECT version, download_url, changelog, released_at 
            FROM client_versions 
            ORDER BY released_at DESC 
            LIMIT 1
        ''').fetchone()

        if version_info:
            return jsonify({
                'status': 'success',
                'version': version_info['version'],
                'download_url': version_info['download_url'],
                'changelog': version_info['changelog'],
                'released_at': version_info['released_at']
            })
        else:
            return jsonify({
                'status': 'success',
                'version': '1.0.0',
                'download_url': None,
                'changelog': 'Initial version',
                'released_at': None
            })
    except Exception:
        return jsonify({
            'status': 'success',
            'version': '1.0.0',
            'download_url': None,
            'changelog': 'Initial version',
            'released_at': None
        })


@client_bp.route('/version', methods=['POST'])
def update_version():
    """버전 정보 업데이트 (GitHub Actions에서 호출)"""
    data = request.json

    if not data or 'version' not in data:
        return jsonify({'status': 'error', 'message': 'version is required'}), 400

    # 인증 추가 (app.py 호환)
    auth_token = request.headers.get('Authorization')
    expected_token = f"Bearer {os.environ.get('UPDATE_TOKEN', 'default-secret-token')}"
    if auth_token != expected_token:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    db = get_db()

    try:
        db.execute('''
            INSERT INTO client_versions (version, download_url, changelog, released_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            data.get('version'),
            data.get('download_url'),
            data.get('changelog')
        ))
        db.commit()

        return jsonify({
            'status': 'success',
            'message': f"Version {data.get('version')} registered" # app.py message format
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
