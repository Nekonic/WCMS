"""
관리자 API Blueprint
관리자가 호출하는 API 엔드포인트
"""
from flask import Blueprint, request, jsonify, session
import json
from models import PCModel, CommandModel, AdminModel
from utils import require_admin, get_db, execute_query

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


# ==================== 추가된 API (복구) ====================

@admin_bp.route('/pcs/bulk-command', methods=['POST'])
@require_admin
def bulk_command():
    """여러 PC에 동시에 명령 전송"""
    data = request.json
    pc_ids = data.get('pc_ids', [])
    command_type = data.get('command_type')
    command_data = data.get('command_data', {})

    if not pc_ids or not command_type:
        return jsonify({'error': 'pc_ids와 command_type은 필수입니다'}), 400

    results = []
    for pc_id in pc_ids:
        try:
            command_id = CommandModel.create(
                pc_id=pc_id,
                command_type=command_type,
                command_data=command_data,
                admin_username=session.get('username')
            )
            results.append({
                'pc_id': pc_id,
                'command_id': command_id,
                'status': 'success'
            })
        except Exception as e:
            results.append({
                'pc_id': pc_id,
                'status': 'error',
                'message': str(e)
            })

    return jsonify({
        'total': len(pc_ids),
        'success': len([r for r in results if r['status'] == 'success']),
        'failed': len([r for r in results if r['status'] == 'error']),
        'results': results
    })


@admin_bp.route('/pc/<int:pc_id>/commands/clear', methods=['DELETE'])
@require_admin
def clear_pc_commands(pc_id):
    """특정 PC의 대기 중인 명령 모두 삭제"""
    try:
        db = get_db()
        cursor = db.execute(
            "DELETE FROM pc_command WHERE pc_id = ? AND status = 'pending'",
            (pc_id,)
        )
        db.commit()
        deleted_count = cursor.rowcount
        return jsonify({
            'status': 'success',
            'message': f'{deleted_count}개의 대기 중인 명령이 삭제되었습니다.',
            'deleted_count': deleted_count
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@admin_bp.route('/pcs/commands/clear', methods=['DELETE'])
@require_admin
def clear_all_commands():
    """여러 PC의 대기 중인 명령 일괄 삭제"""
    pc_ids = request.json.get('pc_ids', [])
    if not pc_ids:
        return jsonify({'error': 'pc_ids는 필수입니다'}), 400

    results, total_deleted = [], 0
    db = get_db()
    
    for pc_id in pc_ids:
        try:
            cursor = db.execute(
                "DELETE FROM pc_command WHERE pc_id = ? AND status = 'pending'",
                (pc_id,)
            )
            deleted = cursor.rowcount
            total_deleted += deleted
            results.append({'pc_id': pc_id, 'deleted_count': deleted, 'status': 'success'})
        except Exception as e:
            results.append({'pc_id': pc_id, 'status': 'error', 'message': str(e)})

    db.commit()
    return jsonify({
        'total': len(pc_ids),
        'success': len([r for r in results if r['status'] == 'success']),
        'failed': len([r for r in results if r['status'] == 'error']),
        'total_deleted': total_deleted,
        'results': results
    })


@admin_bp.route('/commands/pending', methods=['GET'])
@require_admin
def get_pending_commands():
    """대기 중인 명령 목록 조회"""
    commands = CommandModel.get_all_pending()
    
    # PC 정보 추가 (조인 대신 개별 조회로 단순화, 성능 이슈 시 조인으로 변경)
    result = []
    for cmd in commands:
        pc = PCModel.get_by_id(cmd['pc_id'])
        if pc:
            cmd['hostname'] = pc['hostname']
            cmd['seat_number'] = pc['seat_number']
            cmd['room_name'] = pc['room_name']
            result.append(cmd)

    return jsonify({
        'total': len(result),
        'commands': result
    })


@admin_bp.route('/commands/results', methods=['POST'])
@require_admin
def get_command_results():
    """명령 실행 결과 조회 (폴링용)"""
    data = request.json
    command_ids = data.get('command_ids', [])

    if not command_ids:
        return jsonify({'error': 'command_ids는 필수입니다'}), 400

    results = []
    for cmd_id in command_ids:
        cmd = CommandModel.get_by_id(cmd_id)
        if cmd:
            pc = PCModel.get_by_id(cmd['pc_id'])
            if pc:
                cmd['hostname'] = pc['hostname']
                cmd['seat_number'] = pc['seat_number']
            results.append(cmd)

    return jsonify({
        'total': len(results),
        'results': results
    })


@admin_bp.route('/pcs/duplicates', methods=['GET'])
@require_admin
def get_duplicates():
    """중복된 호스트명의 PC 목록 조회"""
    db = get_db()
    try:
        duplicates = db.execute('''
            SELECT hostname, COUNT(*) as count, GROUP_CONCAT(id) as ids
            FROM pc_info
            WHERE hostname IS NOT NULL
            GROUP BY hostname
            HAVING count > 1
            ORDER BY hostname
        ''').fetchall()

        result = []
        for dup in duplicates:
            pc_ids = [int(id) for id in dup['ids'].split(',')]
            pcs = []
            for pid in pc_ids:
                pc = PCModel.get_by_id(pid)
                if pc:
                    pcs.append(pc)

            result.append({
                'hostname': dup['hostname'],
                'count': dup['count'],
                'pcs': pcs
            })

        return jsonify({
            'total_duplicate_groups': len(result),
            'duplicates': result
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@admin_bp.route('/pc/<int:pc_id>', methods=['DELETE'])
@require_admin
def delete_pc(pc_id):
    """PC 삭제"""
    if PCModel.delete(pc_id):
        return jsonify({
            'status': 'success',
            'message': 'PC가 삭제되었습니다.',
            'deleted_pc_id': pc_id
        })
    else:
        return jsonify({'status': 'error', 'message': 'PC 삭제 실패'}), 500


@admin_bp.route('/rooms', methods=['GET'])
@require_admin
def get_rooms():
    """모든 실습실 목록 조회"""
    db = get_db()
    try:
        rooms = db.execute('''
            SELECT 
                sl.id,
                sl.room_name,
                sl.rows,
                sl.cols,
                sl.description,
                sl.is_active,
                sl.created_at,
                COUNT(pi.id) as pc_count
            FROM seat_layout sl
            LEFT JOIN pc_info pi ON sl.room_name = pi.room_name
            GROUP BY sl.id, sl.room_name, sl.rows, sl.cols, sl.description, sl.is_active, sl.created_at
            ORDER BY sl.room_name
        ''').fetchall()

        return jsonify({
            'total': len(rooms),
            'rooms': [dict(room) for room in rooms]
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@admin_bp.route('/rooms', methods=['POST'])
@require_admin
def create_room():
    """새 실습실 생성"""
    data = request.json
    if not data or 'room_name' not in data:
        return jsonify({'status': 'error', 'message': 'room_name is required'}), 400

    room_name = data['room_name']
    rows = data.get('rows', 6)
    cols = data.get('cols', 8)
    description = data.get('description', '')

    db = get_db()
    try:
        # 중복 확인
        existing = db.execute('SELECT id FROM seat_layout WHERE room_name=?', (room_name,)).fetchone()
        if existing:
            return jsonify({'status': 'error', 'message': '이미 존재하는 실습실 이름입니다'}), 400

        cursor = db.execute('''
            INSERT INTO seat_layout (room_name, rows, cols, description, is_active)
            VALUES (?, ?, ?, ?, 1)
        ''', (room_name, rows, cols, description))
        db.commit()

        return jsonify({
            'status': 'success',
            'message': f'{room_name}이(가) 생성되었습니다.',
            'room_id': cursor.lastrowid
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@admin_bp.route('/rooms/<int:room_id>', methods=['PUT'])
@require_admin
def update_room(room_id):
    """실습실 정보 수정"""
    data = request.json
    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400

    db = get_db()
    try:
        room = db.execute('SELECT * FROM seat_layout WHERE id=?', (room_id,)).fetchone()
        if not room:
            return jsonify({'status': 'error', 'message': 'Room not found'}), 404

        old_name = room['room_name']
        new_name = data.get('room_name', old_name)
        rows = data.get('rows', room['rows'])
        cols = data.get('cols', room['cols'])
        description = data.get('description', room['description'])
        is_active = data.get('is_active', room['is_active'])

        if new_name != old_name:
            existing = db.execute('SELECT id FROM seat_layout WHERE room_name=? AND id!=?',
                                 (new_name, room_id)).fetchone()
            if existing:
                return jsonify({'status': 'error', 'message': '이미 존재하는 실습실 이름입니다'}), 400

            db.execute('UPDATE pc_info SET room_name=? WHERE room_name=?', (new_name, old_name))
            db.execute('UPDATE seat_map SET room_name=? WHERE room_name=?', (new_name, old_name))

        db.execute('''
            UPDATE seat_layout 
            SET room_name=?, rows=?, cols=?, description=?, is_active=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
        ''', (new_name, rows, cols, description, is_active, room_id))
        db.commit()

        return jsonify({
            'status': 'success',
            'message': f'{new_name}이(가) 수정되었습니다.'
        })
    except Exception as e:
        db.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@admin_bp.route('/rooms/<int:room_id>', methods=['DELETE'])
@require_admin
def delete_room(room_id):
    """실습실 삭제"""
    db = get_db()
    try:
        room = db.execute('SELECT room_name FROM seat_layout WHERE id=?', (room_id,)).fetchone()
        if not room:
            return jsonify({'status': 'error', 'message': 'Room not found'}), 404

        room_name = room['room_name']
        pc_count = db.execute('SELECT COUNT(*) as cnt FROM pc_info WHERE room_name=?',
                             (room_name,)).fetchone()['cnt']

        if pc_count > 0:
            return jsonify({
                'status': 'error',
                'message': f'이 실습실에는 {pc_count}대의 PC가 배치되어 있습니다. 먼저 PC를 제거하세요.'
            }), 400

        db.execute('DELETE FROM seat_layout WHERE id=?', (room_id,))
        db.commit()

        return jsonify({
            'status': 'success',
            'message': f'{room_name}이(가) 삭제되었습니다.'
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@admin_bp.route('/layout/map/<room_name>', methods=['GET', 'POST'])
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


@admin_bp.route('/debug/pc-status', methods=['GET'])
@require_admin
def debug_pc_status():
    """PC 상태 디버깅 정보"""
    # 오프라인 상태 업데이트 (PCService 활용)
    from services import PCService
    PCService.update_offline_status()

    db = get_db()
    try:
        pcs = db.execute("""
            SELECT 
                id,
                hostname,
                machine_id,
                is_online,
                last_seen,
                created_at,
                datetime('now') as server_time,
                (julianday('now') - julianday(last_seen)) * 24 * 60 as minutes_since_last_seen
            FROM pc_info
            ORDER BY is_online DESC, last_seen DESC
        """).fetchall()

        return jsonify({
            'total': len(pcs),
            'online_count': len([p for p in pcs if p['is_online']]),
            'offline_count': len([p for p in pcs if not p['is_online']]),
            'pcs': [dict(pc) for pc in pcs]
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
