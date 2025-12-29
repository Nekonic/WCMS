"""
클라이언트 API Blueprint
클라이언트가 호출하는 API 엔드포인트
"""
from flask import Blueprint, request, jsonify
import json
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
    if not data or 'pc_id' not in data:
        return jsonify({'status': 'error', 'message': 'pc_id is required'}), 400

    pc_id = data['pc_id']

    # PC 존재 여부 확인
    if not PCModel.get_by_id(pc_id):
        return jsonify({'status': 'error', 'message': 'PC not found'}), 404

    success = PCModel.update_heartbeat(
        pc_id=pc_id,
        cpu_usage=data.get('cpu_usage', 0),
        ram_used=data.get('ram_used', 0),
        ram_usage_percent=data.get('ram_usage_percent', 0),
        disk_usage=data.get('disk_usage'),
        current_user=data.get('current_user'),
        uptime=data.get('uptime', 0),
        processes=data.get('processes')
    )

    if success:
        return jsonify({'status': 'success', 'message': 'Heartbeat recorded'}), 200
    else:
        return jsonify({'status': 'error', 'message': 'Failed to record heartbeat'}), 500


@client_bp.route('/command', methods=['GET'])
def get_command():
    """대기 중인 명령 조회 (Long-polling)"""
    pc_id = request.args.get('pc_id', type=int)
    if not pc_id:
        return jsonify({'status': 'error', 'message': 'pc_id is required'}), 400

    # PC 존재 여부 확인
    if not PCModel.get_by_id(pc_id):
        return jsonify({'status': 'error', 'message': 'PC not found'}), 404

    commands = CommandModel.get_pending_for_pc(pc_id)

    result = []
    for cmd in commands:
        result.append({
            'id': cmd['id'],
            'type': cmd['command_type'],
            'data': json.loads(cmd['command_data']) if cmd['command_data'] else {},
            'priority': cmd['priority'],
            'timeout': cmd['timeout_seconds']
        })

    return jsonify({
        'status': 'success',
        'commands': result
    }), 200


@client_bp.route('/command/result', methods=['POST'])
def report_command_result():
    """명령 실행 결과 보고"""
    data = request.json
    if not data or 'command_id' not in data:
        return jsonify({'status': 'error', 'message': 'command_id is required'}), 400

    command_id = data['command_id']
    result = data.get('result', '')
    status = data.get('status', 'completed')  # completed, error

    # 명령 존재 여부 확인
    cmd = CommandModel.get_by_id(command_id)
    if not cmd:
        return jsonify({'status': 'error', 'message': 'Command not found'}), 404

    if status == 'completed':
        success = CommandModel.complete(command_id, result)
    elif status == 'error':
        error_msg = data.get('error_message', 'Unknown error')
        success = CommandModel.set_error(command_id, error_msg)
    else:
        return jsonify({'status': 'error', 'message': 'Invalid status'}), 400

    if success:
        return jsonify({'status': 'success', 'message': 'Result recorded'}), 200
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
            'message': 'Version updated',
            'version': data.get('version')
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to update version: {str(e)}'
        }), 500
