"""
클라이언트 API Blueprint
클라이언트가 호출하는 API 엔드포인트
"""
from flask import Blueprint, request, jsonify
import json
import time
import logging
from models import PCModel, CommandModel
from utils import get_db

logger = logging.getLogger('wcms.client_api')

client_bp = Blueprint('client', __name__, url_prefix='/api/client')


@client_bp.route('/register', methods=['POST'])
def register():
    """클라이언트 등록 (PIN 인증 필수 - v0.8.0)"""
    data = request.json
    if not data or 'machine_id' not in data:
        return jsonify({'status': 'error', 'message': 'machine_id is required'}), 400

    machine_id = data['machine_id']
    pin = data.get('pin')

    # PIN 검증 (v0.8.0+)
    if not pin:
        return jsonify({
            'status': 'error',
            'message': 'PIN required (use 6-digit registration token)'
        }), 400

    from models import RegistrationTokenModel

    is_valid, error_msg = RegistrationTokenModel.validate(pin)
    if not is_valid:
        logger.warning(f"등록 실패: PIN 검증 실패 (machine_id={machine_id}, pin={pin}, error={error_msg})")
        return jsonify({
            'status': 'error',
            'message': error_msg
        }), 403

    # PC 정보
    hostname = data.get('hostname') or 'Unknown-PC'
    mac_address = data.get('mac_address') or '00:00:00:00:00:00'
    ip_address = data.get('ip_address')

    # PC 등록 (is_verified=True, registered_with_token=pin)
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

    # PC 검증 처리
    from utils import get_db
    db = get_db()
    db.execute('''
        UPDATE pc_info 
        SET is_verified=1, registered_with_token=?, verified_at=CURRENT_TIMESTAMP
        WHERE id=?
    ''', (pin, pc_id))
    db.commit()

    # 토큰 사용 처리
    RegistrationTokenModel.mark_used(pin)

    # 동적 정보 저장 (v0.8.0 - 등록 시 디스크/프로세스 정보도 함께)
    system_info = data.get('system_info')
    if system_info:
        try:
            PCModel.update_dynamic_info(pc_id, system_info)
            logger.debug(f"등록 시 동적 정보 저장 완료: PC {pc_id}")
        except Exception as e:
            logger.warning(f"등록 시 동적 정보 저장 실패: {e}")

    logger.info(f"PC 등록 성공: {hostname} (machine_id={machine_id}, pin={pin})")

    return jsonify({
        'status': 'success',
        'message': 'Registration successful',
        'pc_id': pc_id
    }), 200


@client_bp.route('/heartbeat', methods=['POST'])
def heartbeat():
    """클라이언트 하트비트 (전체/경량 구분)

    full_update=true: 전체 하트비트 (프로세스 목록 포함)
    full_update=false: 경량 하트비트 (CPU, RAM, IP만) - 명령 조회와 통합 권장
    """
    data = request.json
    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400

    pc_id = data.get('pc_id')
    machine_id = data.get('machine_id')
    full_update = data.get('full_update', True)  # 기본값: 전체 업데이트

    if not pc_id and not machine_id:
        return jsonify({'status': 'error', 'message': 'machine_id or pc_id is required'}), 400

    if machine_id:
        pc = PCModel.get_by_machine_id(machine_id)
        if pc:
            pc_id = pc['id']
        else:
            return jsonify({'status': 'error', 'message': 'PC not registered'}), 404
    
    # PC 존재 여부 확인
    if not PCModel.get_by_id(pc_id):
        return jsonify({'status': 'error', 'message': 'PC not found'}), 404

    # system_info 필드 처리
    info = data.get('system_info', data)

    # IP 주소 업데이트 (항상 처리)
    ip_changed = False
    ip_address = info.get('ip_address')
    if ip_address and ip_address != 'Unknown':
        from utils import get_db
        db = get_db()

        # 현재 IP 조회
        current_ip = db.execute(
            'SELECT ip_address FROM pc_info WHERE id=?',
            (pc_id,)
        ).fetchone()

        if current_ip and current_ip['ip_address'] != ip_address:
            ip_changed = True
            logger.info(f"IP 변경 감지 (하트비트): pc_id={pc_id}, {current_ip['ip_address']} → {ip_address}")

        db.execute('UPDATE pc_info SET ip_address=? WHERE id=?', (ip_address, pc_id))
        db.commit()

    # 전체 하트비트: 모든 정보 저장
    if full_update:
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
    # 경량 하트비트: CPU, RAM만 저장 (기존 값 유지)
    else:
        success = PCModel.update_light_heartbeat(
            pc_id=pc_id,
            cpu_usage=info.get('cpu_usage', 0),
            ram_usage_percent=info.get('ram_usage_percent', 0)
        )

    if success:
        return jsonify({
            'status': 'success',
            'message': 'Heartbeat received',
            'full_update': full_update,
            'ip_changed': ip_changed
        }), 200
    else:
        return jsonify({'status': 'error', 'message': 'Failed to record heartbeat'}), 500


@client_bp.route('/shutdown', methods=['POST'])
def shutdown_signal():
    """클라이언트 종료 신호 수신 (즉시 오프라인 처리)"""
    data = request.json
    if not data or 'machine_id' not in data:
        return jsonify({'status': 'error', 'message': 'machine_id is required'}), 400

    machine_id = data['machine_id']

    pc = PCModel.get_by_machine_id(machine_id)
    if not pc:
        return jsonify({'status': 'error', 'message': 'PC not found'}), 404

    pc_id = pc['id']
    db = get_db()
    db.execute('UPDATE pc_info SET is_online=0, last_seen=CURRENT_TIMESTAMP WHERE id=?', (pc_id,))

    # 열린 network_events 레코드가 없으면 새로 생성
    existing = db.execute(
        'SELECT id FROM network_events WHERE pc_id=? AND online_at IS NULL',
        (pc_id,)
    ).fetchone()
    if not existing:
        db.execute(
            'INSERT INTO network_events (pc_id, offline_at, reason) VALUES (?, CURRENT_TIMESTAMP, ?)',
            (pc_id, 'shutdown')
        )
    db.commit()

    logger.info(f"[종료] PC {pc_id} ({machine_id}) 종료 신호 수신")
    return jsonify({'status': 'success', 'message': 'Shutdown signal received'}), 200


@client_bp.route('/commands', methods=['GET'])
def poll_commands():
    """명령 대기 (Long-polling, GET)

    GET /api/client/commands?machine_id=X&timeout=30
    - 서버가 timeout초 동안 연결 유지, 0.5초마다 명령 확인
    - 연결 시작 시 last_seen 즉시 업데이트 (연결 자체가 생존 신호)
    - 오프라인이었던 PC 재연결 시 is_online=1 복원 + network_events 기록
    """
    machine_id = request.args.get('machine_id')
    timeout = min(int(request.args.get('timeout', 30)), 60)

    if not machine_id:
        return jsonify({
            'status': 'error',
            'error': {'code': 'MISSING_IDENTIFIER', 'message': 'machine_id required'}
        }), 400

    pc = PCModel.get_by_machine_id(machine_id)
    if not pc:
        return jsonify({
            'status': 'error',
            'error': {'code': 'PC_NOT_FOUND', 'message': f'PC not registered: {machine_id}'}
        }), 404

    pc_id = pc['id']
    db = get_db()

    # 재연결 감지: 오프라인이었으면 온라인으로 복원 + network_events 닫기
    was_offline = not pc['is_online']
    if was_offline:
        db.execute('UPDATE pc_info SET is_online=1, last_seen=CURRENT_TIMESTAMP WHERE id=?', (pc_id,))
        open_event = db.execute(
            'SELECT id, offline_at FROM network_events WHERE pc_id=? AND online_at IS NULL ORDER BY offline_at DESC LIMIT 1',
            (pc_id,)
        ).fetchone()
        if open_event:
            db.execute('''
                UPDATE network_events
                SET online_at=CURRENT_TIMESTAMP,
                    duration_sec=CAST((julianday('now') - julianday(offline_at)) * 86400 AS INTEGER)
                WHERE id=?
            ''', (open_event['id'],))
        db.commit()
        logger.info(f"[재연결] PC {pc_id} ({machine_id}) 온라인 복원")
    else:
        # 연결 시작 시 last_seen 즉시 업데이트
        db.execute('UPDATE pc_info SET is_online=1, last_seen=CURRENT_TIMESTAMP WHERE id=?', (pc_id,))
        db.commit()

    # Long-poll: timeout초 동안 명령 대기 (0.5초마다 확인, 최소 1회 실행)
    deadline = time.time() + timeout
    while True:
        cmds = CommandModel.get_pending_for_pc(pc_id)
        if cmds:
            cmd = cmds[0]
            logger.info(f"[명령조회] 명령 발견: PC {pc_id}, 명령 {cmd['id']} ({cmd['command_type']})")
            CommandModel.start_execution(cmd['id'])

            command_data = cmd['command_data']
            if isinstance(command_data, str):
                try:
                    command_data = json.loads(command_data)
                except Exception:
                    command_data = {}

            return jsonify({
                'status': 'success',
                'data': {
                    'has_command': True,
                    'command': {
                        'id': cmd['id'],
                        'type': cmd['command_type'],
                        'parameters': command_data,
                        'timeout': cmd.get('timeout_seconds', 300),
                        'priority': cmd.get('priority', 5),
                        'created_at': cmd.get('created_at')
                    }
                }
            }), 200
        if time.time() >= deadline:
            break
        time.sleep(0.5)

    # timeout 만료 - 명령 없음, 클라이언트 즉시 재연결
    return jsonify({'status': 'success', 'data': {'has_command': False, 'command': None}}), 200


@client_bp.route('/offline', methods=['POST'])
def report_offline():
    """클라이언트 네트워크 오프라인 신호 (즉시 오프라인 처리)"""
    data = request.json or {}
    machine_id = data.get('machine_id')
    if not machine_id:
        return jsonify({'status': 'error', 'message': 'machine_id required'}), 400

    pc = PCModel.get_by_machine_id(machine_id)
    if not pc:
        return jsonify({'status': 'error', 'message': 'PC not found'}), 404

    pc_id = pc['id']
    db = get_db()
    db.execute('UPDATE pc_info SET is_online=0 WHERE id=?', (pc_id,))

    # 열린 이벤트가 없으면 새로 생성
    existing = db.execute(
        'SELECT id FROM network_events WHERE pc_id=? AND online_at IS NULL',
        (pc_id,)
    ).fetchone()
    if not existing:
        db.execute(
            'INSERT INTO network_events (pc_id, offline_at, reason) VALUES (?, CURRENT_TIMESTAMP, ?)',
            (pc_id, 'network_error')
        )
    db.commit()

    logger.info(f"[오프라인] PC {pc_id} ({machine_id}) 네트워크 오프라인 신호")
    return jsonify({'status': 'success'}), 200


@client_bp.route('/commands/<int:command_id>/result', methods=['POST'])
def submit_command_result(command_id: int):
    """명령 실행 결과 제출

    RESTful 경로: /api/client/commands/{command_id}/result
    """
    data = request.json or {}

    # 명령 존재 확인
    cmd = CommandModel.get_by_id(command_id)
    if not cmd:
        return jsonify({
            'status': 'error',
            'error': {
                'code': 'COMMAND_NOT_FOUND',
                'message': f'Command not found: {command_id}'
            }
        }), 404

    # 결과 데이터 검증
    result_status = data.get('status', 'completed')
    output = data.get('output', '')
    error_message = data.get('error_message')
    exit_code = data.get('exit_code')

    logger.info(f"[명령결과] 명령 {command_id}: status={result_status}, output={output[:100] if output else 'None'}...")

    # 상태별 처리
    try:
        if result_status == 'success' or result_status == 'completed':
            success = CommandModel.complete(command_id, output)
        elif result_status == 'error' or result_status == 'failed':
            error_msg = error_message or output or 'Unknown error'
            success = CommandModel.set_error(command_id, error_msg)
        elif result_status == 'timeout':
            success = CommandModel.set_timeout(command_id)
        else:
            # 알 수 없는 상태는 에러로 처리
            success = CommandModel.set_error(command_id, f'Unknown status: {result_status}')

        if success:
            logger.info(f"[명령결과] 성공: 명령 {command_id}, 상태 {result_status}")
            return jsonify({
                'status': 'success',
                'data': {
                    'message': 'Result recorded',
                    'command_id': command_id,
                    'final_status': result_status
                }
            }), 200
        else:
            logger.error(f"[명령결과] 실패: 명령 {command_id} 업데이트 실패")
            return jsonify({
                'status': 'error',
                'error': {
                    'code': 'UPDATE_FAILED',
                    'message': 'Failed to update command status'
                }
            }), 500

    except Exception as e:
        logger.error(f"[명령결과] 예외: 명령 {command_id}, {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': str(e)
            }
        }), 500


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

