"""
관리자 API Blueprint
관리자가 호출하는 API 엔드포인트
"""
from flask import Blueprint, request, jsonify, session
import json
import logging
from models import PCModel, CommandModel, AdminModel
from utils import require_admin, get_db, execute_query

logger = logging.getLogger('wcms.admin_api')

admin_bp = Blueprint('admin', __name__, url_prefix='/api')


def _get_pc_or_404(pc_id: int):
    """PC 조회. 없으면 (None, 404 응답) 반환."""
    pc = PCModel.get_by_id(pc_id)
    if not pc:
        return None, (jsonify({'status': 'error', 'message': 'PC를 찾을 수 없습니다'}), 404)
    return pc, None


def _queue_command(pc_id: int, cmd_type: str, cmd_data=None):
    """PC 존재 확인 후 명령 큐 등록. JSON 응답 반환."""
    _, err = _get_pc_or_404(pc_id)
    if err:
        return err
    try:
        command_id = CommandModel.create(
            pc_id=pc_id,
            command_type=cmd_type,
            command_data=cmd_data,
            admin_username=session.get('username', 'admin')
        )
        logger.info(f"{cmd_type} 명령 생성: PC {pc_id} by {session.get('username')}")
        return jsonify({'status': 'success', 'command_id': command_id}), 200
    except Exception as e:
        logger.error(f"{cmd_type} 명령 생성 실패: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500


@admin_bp.route('/pcs', methods=['GET'])
def list_pcs():
    """모든 PC 목록 조회 (app.py 호환: 인증 불필요, 리스트 반환)"""
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

    # app.py 호환: 딕셔너리 래퍼 없이 리스트 직접 반환
    return jsonify(result), 200


@admin_bp.route('/pc/<int:pc_id>', methods=['GET'])
def get_pc(pc_id):
    """PC 상세 정보 조회 (app.py 호환: 인증 불필요, 객체 직접 반환)"""
    pc = PCModel.get_with_status(pc_id)

    if not pc:
        return jsonify({'error': 'PC not found'}), 404 # app.py error format

    # app.py 호환: 딕셔너리 래퍼 없이 객체 직접 반환
    return jsonify(pc), 200


@admin_bp.route('/pc/<int:pc_id>/history', methods=['GET'])
@require_admin
def get_pc_history(pc_id):
    """PC 상태 기록 조회"""
    db = get_db()

    # PC 존재 여부 확인
    if not PCModel.get_by_id(pc_id):
        # app.py는 "PC not found", 404 문자열 반환했으나, 여기선 JSON 유지하되 app.py 호환성 고려
        # app.py: return "PC not found", 404
        # 하지만 api_pc_history (API)는 JSON 반환.
        # app.py의 api_pc_history는:
        # return jsonify([dict(row) for row in history])
        # PC 존재 여부 체크 안함 (그냥 빈 리스트 반환될듯)
        pass

    limit = request.args.get('limit', default=100, type=int)
    rows = db.execute('''
        SELECT updated_at, current_user, processes
        FROM pc_dynamic_info 
        WHERE pc_id=? AND processes IS NOT NULL
        ORDER BY updated_at DESC 
        LIMIT ?
    ''', (pc_id, limit)).fetchall()

    history = [dict(row) for row in rows]

    # app.py 호환: 리스트 직접 반환
    return jsonify(history), 200


@admin_bp.route('/pc/<int:pc_id>/command', methods=['POST'])
@require_admin
def send_command(pc_id):
    """PC에 명령 전송"""
    data = request.json

    if not data or 'type' not in data:
        logger.warning(f"명령 전송 실패: type 필드 누락 (pc_id={pc_id})")
        return jsonify({'status': 'error', 'message': 'type 필드가 필요합니다'}), 400 # app.py message

    # PC 존재 여부 확인
    if not PCModel.get_by_id(pc_id):
        logger.warning(f"명령 전송 실패: PC 미존재 (pc_id={pc_id})")
        return jsonify({'status': 'error', 'message': 'PC를 찾을 수 없습니다'}), 404 # app.py message

    command_id = CommandModel.create(
        pc_id=pc_id,
        command_type=data.get('type'),
        command_data=data.get('data'),
        admin_username=session.get('username'),
        priority=data.get('priority', 5),
        timeout_seconds=data.get('timeout_seconds', 300)
    )

    logger.info(f"명령 생성 성공: cmd_id={command_id}, pc_id={pc_id}, type={data.get('type')}, admin={session.get('username')}")

    return jsonify({
        'status': 'success',
        'message': '명령 전송 완료', # app.py message
        'command_id': command_id
    }), 200


@admin_bp.route('/pc/<int:pc_id>/reboot', methods=['POST'])
@require_admin
def pc_reboot(pc_id):
    """PC 재시작 명령 전송"""
    return _queue_command(pc_id, 'reboot')


@admin_bp.route('/pc/<int:pc_id>/account/create', methods=['POST'])
@require_admin
def create_account(pc_id):
    """Windows 계정 생성 명령 전송"""
    data = request.json
    if not data or not all(k in data for k in ['username', 'password']):
        return jsonify({'status': 'error', 'message': 'username과 password 필드가 필요합니다'}), 400
    return _queue_command(pc_id, 'create_user', {
        'username': data['username'], 'password': data['password'],
        'full_name': data.get('full_name'), 'comment': data.get('comment'),
        'language': data.get('language')
    })


@admin_bp.route('/pc/<int:pc_id>/account/delete', methods=['POST'])
@require_admin
def delete_account(pc_id):
    """Windows 계정 삭제 명령 전송"""
    data = request.json
    if not data or 'username' not in data:
        return jsonify({'status': 'error', 'message': 'username 필드가 필요합니다'}), 400
    return _queue_command(pc_id, 'delete_user', {'username': data['username']})


@admin_bp.route('/pc/<int:pc_id>/account/password', methods=['POST'])
@require_admin
def change_password(pc_id):
    """Windows 계정 비밀번호 변경 명령 전송"""
    data = request.json
    if not data or not all(k in data for k in ['username', 'new_password']):
        return jsonify({'status': 'error', 'message': 'username과 new_password 필드가 필요합니다'}), 400
    return _queue_command(pc_id, 'change_password', {
        'username': data['username'], 'new_password': data['new_password']
    })


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
            'message': f'PC({pc_id})가 삭제되었습니다.', # app.py message format approximation
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
def debug_pc_dynamic_info():
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


# ==================== 클라이언트 버전 관리 ====================

@admin_bp.route('/client/versions', methods=['GET'])
@require_admin
def get_client_versions():
    """클라이언트 버전 목록 조회"""
    db = get_db()
    try:
        versions = db.execute('''
            SELECT id, version, download_url, changelog, released_at 
            FROM client_versions 
            ORDER BY released_at DESC
        ''').fetchall()

        return jsonify({
            'status': 'success',
            'versions': [dict(v) for v in versions]
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@admin_bp.route('/client/version', methods=['POST'])
@require_admin
def create_client_version():
    """클라이언트 버전 등록 (관리자 전용)"""
    data = request.json

    if not data or 'version' not in data or 'download_url' not in data:
        return jsonify({'status': 'error', 'message': 'version과 download_url이 필요합니다'}), 400

    db = get_db()

    try:
        db.execute('''
            INSERT INTO client_versions (version, download_url, changelog, released_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            data.get('version'),
            data.get('download_url'),
            data.get('changelog', '')
        ))
        db.commit()

        logger.info(f"클라이언트 버전 등록: {data.get('version')} by {session.get('username')}")

        return jsonify({
            'status': 'success',
            'message': f"버전 {data.get('version')} 등록 완료"
        }), 200
    except Exception as e:
        logger.error(f"버전 등록 실패: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': f"등록 실패: {str(e)}"}), 500


@admin_bp.route('/client/version/<int:version_id>', methods=['DELETE'])
@require_admin
def delete_client_version(version_id):
    """클라이언트 버전 삭제"""
    db = get_db()

    try:
        version = db.execute('SELECT version FROM client_versions WHERE id=?', (version_id,)).fetchone()
        if not version:
            return jsonify({'status': 'error', 'message': '버전을 찾을 수 없습니다'}), 404

        db.execute('DELETE FROM client_versions WHERE id=?', (version_id,))
        db.commit()

        logger.info(f"클라이언트 버전 삭제: {version['version']} by {session.get('username')}")

        return jsonify({
            'status': 'success',
            'message': f"버전 {version['version']} 삭제 완료"
        }), 200
    except Exception as e:
        logger.error(f"버전 삭제 실패: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ==================== 등록 토큰 관리 API (v0.8.0) ====================

@admin_bp.route('/admin/registration-token', methods=['POST'])
@require_admin
def create_registration_token():
    """등록 토큰 생성 (PIN 인증)"""
    from models import RegistrationTokenModel

    data = request.json or {}
    usage_type = data.get('usage_type', 'single')  # 기본값: 1회용
    expires_in = data.get('expires_in', 600)  # 기본값: 10분

    # 유효성 검증
    if usage_type not in ['single', 'multi']:
        return jsonify({
            'status': 'error',
            'message': 'usage_type must be "single" or "multi"'
        }), 400

    if not isinstance(expires_in, int) or expires_in < 60 or expires_in > 86400:
        return jsonify({
            'status': 'error',
            'message': 'expires_in must be between 60 and 86400 seconds'
        }), 400

    try:
        created_by = session.get('username', 'admin')
        token_data = RegistrationTokenModel.create(
            created_by=created_by,
            usage_type=usage_type,
            expires_in=expires_in
        )

        logger.info(f"등록 토큰 생성: {token_data['token']} by {created_by}, type={usage_type}")

        return jsonify({
            'status': 'success',
            'id': token_data['id'],
            'token': token_data['token'],
            'usage_type': token_data['usage_type'],
            'expires_at': token_data['expires_at'],
            'created_by': token_data['created_by']
        }), 200

    except Exception as e:
        logger.error(f"토큰 생성 실패: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f"Token creation failed: {str(e)}"
        }), 500


@admin_bp.route('/admin/registration-tokens', methods=['GET'])
@require_admin
def list_registration_tokens():
    """활성 토큰 목록 조회"""
    from models import RegistrationTokenModel

    try:
        # 쿼리 파라미터로 필터링 옵션
        show_all = request.args.get('all', 'false').lower() == 'true'

        if show_all:
            tokens = RegistrationTokenModel.get_all_tokens()
        else:
            tokens = RegistrationTokenModel.get_active_tokens()

        return jsonify({
            'status': 'success',
            'tokens': tokens
        }), 200

    except Exception as e:
        logger.error(f"토큰 목록 조회 실패: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@admin_bp.route('/admin/registration-token/<int:token_id>', methods=['DELETE'])
@require_admin
def delete_registration_token(token_id):
    """토큰 삭제"""
    from models import RegistrationTokenModel

    try:
        db = get_db()

        # 토큰 존재 확인
        token = db.execute(
            'SELECT * FROM pc_registration_tokens WHERE id = ?',
            (token_id,)
        ).fetchone()

        if not token:
            return jsonify({
                'status': 'error',
                'message': 'Token not found'
            }), 404

        # 토큰 삭제
        db.execute('DELETE FROM pc_registration_tokens WHERE id = ?', (token_id,))
        db.commit()

        logger.info(f"토큰 삭제: ID {token_id} by {session.get('username')}")
        return jsonify({
            'status': 'success',
            'message': 'Token deleted successfully'
        }), 200

    except Exception as e:
        logger.error(f"토큰 삭제 실패: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# ==================== PC 관리 API (v0.8.0) ====================

@admin_bp.route('/admin/pcs/unverified', methods=['GET'])
@require_admin
def list_unverified_pcs():
    """미검증 PC 목록 조회"""
    db = get_db()

    try:
        rows = db.execute('''
            SELECT id, hostname, machine_id, ip_address, is_verified, created_at
            FROM pc_info
            WHERE is_verified = 0
            ORDER BY created_at DESC
        ''').fetchall()

        pcs = [dict(row) for row in rows]

        return jsonify({
            'status': 'success',
            'pcs': pcs
        }), 200

    except Exception as e:
        logger.error(f"미검증 PC 목록 조회 실패: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# ==================== PC 명령 API ====================

@admin_bp.route('/pc/<int:pc_id>/shutdown', methods=['POST'])
@require_admin
def send_shutdown_command(pc_id: int):
    """PC 종료 명령"""
    data = request.json or {}
    return _queue_command(pc_id, 'shutdown', {'delay': data.get('delay', 0), 'message': data.get('message', '')})


@admin_bp.route('/pc/<int:pc_id>/restart', methods=['POST'])
@require_admin
def send_restart_command(pc_id: int):
    """PC 재시작 명령"""
    data = request.json or {}
    return _queue_command(pc_id, 'restart', {'delay': data.get('delay', 0), 'message': data.get('message', '')})


@admin_bp.route('/pc/<int:pc_id>/message', methods=['POST'])
@require_admin
def send_message_command(pc_id: int):
    """PC에 메시지 전송"""
    data = request.json or {}
    if not data.get('message'):
        return jsonify({'status': 'error', 'message': 'Message is required'}), 400
    return _queue_command(pc_id, 'message', {'message': data['message'], 'duration': data.get('duration', 10)})


@admin_bp.route('/pc/<int:pc_id>/kill-process', methods=['POST'])
@require_admin
def send_kill_process_command(pc_id: int):
    """프로세스 종료 명령"""
    data = request.json or {}
    if not data.get('process_name'):
        return jsonify({'status': 'error', 'message': 'process_name is required'}), 400
    return _queue_command(pc_id, 'kill_process', {'process_name': data['process_name']})


@admin_bp.route('/pc/<int:pc_id>/install', methods=['POST'])
@require_admin
def send_install_command(pc_id: int):
    """프로그램 설치 명령"""
    data = request.json or {}
    if not data.get('app_id'):
        return jsonify({'status': 'error', 'message': 'app_id is required'}), 400
    return _queue_command(pc_id, 'install', {'app_id': data['app_id']})


@admin_bp.route('/pc/<int:pc_id>/uninstall', methods=['POST'])
@require_admin
def send_uninstall_command(pc_id: int):
    """프로그램 삭제 명령"""
    data = request.json or {}
    if not data.get('app_id'):
        return jsonify({'status': 'error', 'message': 'app_id is required'}), 400
    return _queue_command(pc_id, 'uninstall', {'app_id': data['app_id']})


@admin_bp.route('/admin/processes', methods=['GET'])
@require_admin
def get_all_processes():
    """수집된 모든 프로세스 목록 조회 (중복 제거)"""
    db = get_db()
    try:
        # 최근 1시간 내에 업데이트된 PC들의 프로세스 목록 조회
        rows = db.execute('''
            SELECT processes 
            FROM pc_dynamic_info 
            WHERE processes IS NOT NULL 
              AND processes != '[]'
              AND datetime(updated_at) > datetime('now', '-1 hour')
        ''').fetchall()

        all_processes = set()
        for row in rows:
            try:
                proc_list = json.loads(row['processes'])
                if isinstance(proc_list, list):
                    all_processes.update(proc_list)
            except:
                pass

        return jsonify({
            'status': 'success',
            'total': len(all_processes),
            'processes': sorted(list(all_processes))
        }), 200

    except Exception as e:
        logger.error(f"프로세스 목록 조회 실패: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
