"""
관리자 API Blueprint
관리자가 호출하는 API 엔드포인트
"""
from flask import Blueprint, request, jsonify, session
import json
from models import PCModel, CommandModel, AdminModel
from utils import require_admin, get_db

admin_bp = Blueprint('admin', __name__, url_prefix='/api')


@admin_bp.route('/pcs', methods=['GET'])
@require_admin
def list_pcs():
    """모든 PC 목록 조회"""
    room = request.args.get('room')

    if room:
        pcs = PCModel.get_all_by_room(room)
    else:
        pcs = PCModel.get_all()

    # 각 PC의 최신 상태 추가
    result = []
    for pc in pcs:
        pc_with_status = PCModel.get_with_status(pc['id'])
        if pc_with_status:
            result.append(pc_with_status)

    return jsonify({
        'status': 'success',
        'count': len(result),
        'pcs': result
    }), 200


@admin_bp.route('/pc/<int:pc_id>', methods=['GET'])
@require_admin
def get_pc(pc_id):
    """PC 상세 정보 조회"""
    pc = PCModel.get_with_status(pc_id)

    if not pc:
        return jsonify({'status': 'error', 'message': 'PC not found'}), 404

    return jsonify({
        'status': 'success',
        'pc': pc
    }), 200


@admin_bp.route('/pc/<int:pc_id>/history', methods=['GET'])
@require_admin
def get_pc_history(pc_id):
    """PC 상태 기록 조회"""
    db = get_db()

    # PC 존재 여부 확인
    if not PCModel.get_by_id(pc_id):
        return jsonify({'status': 'error', 'message': 'PC not found'}), 404

    limit = request.args.get('limit', default=100, type=int)
    rows = db.execute('''
        SELECT * FROM pc_status 
        WHERE pc_id=? 
        ORDER BY created_at DESC 
        LIMIT ?
    ''', (pc_id, limit)).fetchall()

    history = [dict(row) for row in rows]

    return jsonify({
        'status': 'success',
        'count': len(history),
        'history': history
    }), 200


@admin_bp.route('/pc/<int:pc_id>/command', methods=['POST'])
@require_admin
def send_command(pc_id):
    """PC에 명령 전송"""
    data = request.json

    if not data or 'type' not in data:
        return jsonify({'status': 'error', 'message': 'Command type is required'}), 400

    # PC 존재 여부 확인
    if not PCModel.get_by_id(pc_id):
        return jsonify({'status': 'error', 'message': 'PC not found'}), 404

    command_id = CommandModel.create(
        pc_id=pc_id,
        command_type=data.get('type'),
        command_data=data.get('data'),
        admin_username=session.get('username'),
        priority=data.get('priority', 5),
        max_retries=data.get('max_retries', 3),
        timeout_seconds=data.get('timeout_seconds', 300)
    )

    return jsonify({
        'status': 'success',
        'message': 'Command sent',
        'command_id': command_id
    }), 200


@admin_bp.route('/pc/<int:pc_id>/shutdown', methods=['POST'])
@require_admin
def pc_shutdown(pc_id):
    """PC 종료 명령 전송"""
    if not PCModel.get_by_id(pc_id):
        return jsonify({'status': 'error', 'message': 'PC not found'}), 404

    command_id = CommandModel.create(
        pc_id=pc_id,
        command_type='shutdown',
        admin_username=session.get('username')
    )

    return jsonify({
        'status': 'success',
        'message': 'Shutdown command sent',
        'command_id': command_id
    }), 200


@admin_bp.route('/pc/<int:pc_id>/reboot', methods=['POST'])
@require_admin
def pc_reboot(pc_id):
    """PC 재시작 명령 전송"""
    if not PCModel.get_by_id(pc_id):
        return jsonify({'status': 'error', 'message': 'PC not found'}), 404

    command_id = CommandModel.create(
        pc_id=pc_id,
        command_type='reboot',
        admin_username=session.get('username')
    )

    return jsonify({
        'status': 'success',
        'message': 'Reboot command sent',
        'command_id': command_id
    }), 200


@admin_bp.route('/pc/<int:pc_id>/account/create', methods=['POST'])
@require_admin
def create_account(pc_id):
    """Windows 계정 생성 명령 전송"""
    data = request.json

    if not data or not all(k in data for k in ['username', 'password']):
        return jsonify({'status': 'error', 'message': 'username and password are required'}), 400

    if not PCModel.get_by_id(pc_id):
        return jsonify({'status': 'error', 'message': 'PC not found'}), 404

    command_id = CommandModel.create(
        pc_id=pc_id,
        command_type='create_user',
        command_data={
            'username': data['username'],
            'password': data['password'],
            'full_name': data.get('full_name'),
            'comment': data.get('comment')
        },
        admin_username=session.get('username')
    )

    return jsonify({
        'status': 'success',
        'message': 'Account creation command sent',
        'command_id': command_id
    }), 200


@admin_bp.route('/pc/<int:pc_id>/account/delete', methods=['POST'])
@require_admin
def delete_account(pc_id):
    """Windows 계정 삭제 명령 전송"""
    data = request.json

    if not data or 'username' not in data:
        return jsonify({'status': 'error', 'message': 'username is required'}), 400

    if not PCModel.get_by_id(pc_id):
        return jsonify({'status': 'error', 'message': 'PC not found'}), 404

    command_id = CommandModel.create(
        pc_id=pc_id,
        command_type='delete_user',
        command_data={'username': data['username']},
        admin_username=session.get('username')
    )

    return jsonify({
        'status': 'success',
        'message': 'Account deletion command sent',
        'command_id': command_id
    }), 200


@admin_bp.route('/pc/<int:pc_id>/account/password', methods=['POST'])
@require_admin
def change_password(pc_id):
    """Windows 계정 비밀번호 변경 명령 전송"""
    data = request.json

    if not data or not all(k in data for k in ['username', 'new_password']):
        return jsonify({'status': 'error', 'message': 'username and new_password are required'}), 400

    if not PCModel.get_by_id(pc_id):
        return jsonify({'status': 'error', 'message': 'PC not found'}), 404

    command_id = CommandModel.create(
        pc_id=pc_id,
        command_type='change_password',
        command_data={
            'username': data['username'],
            'new_password': data['new_password']
        },
        admin_username=session.get('username')
    )

    return jsonify({
        'status': 'success',
        'message': 'Password change command sent',
        'command_id': command_id
    }), 200

