"""
WCMS 클라이언트 기능 테스트 (pytest용)
- collector.py의 시스템 정보 수집 기능 테스트
- executor.py의 명령 실행 기능 테스트 (안전한 명령만)
"""

import sys
import json
import os
import pytest

# 프로젝트 루트를 sys.path에 추가하여 모듈 임포트 가능하게 함
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../client')))

from collector import collect_static_info, collect_dynamic_info, collect_running_processes
from executor import CommandExecutor

# ==================== Collector 테스트 ====================

def test_collect_static_info():
    """정적 시스템 정보 수집 테스트"""
    info = collect_static_info()
    assert info is not None, "정적 정보 수집 실패"

    required_fields = ['hostname', 'mac_address', 'cpu_model', 'cpu_cores',
                     'cpu_threads', 'ram_total', 'disk_info', 'os_edition', 'os_version']
    missing = [f for f in required_fields if f not in info or info[f] is None]
    
    assert not missing, f"누락된 필드: {', '.join(missing)}"

def test_collect_dynamic_info():
    """동적 시스템 정보 수집 테스트"""
    info = collect_dynamic_info()
    assert info is not None, "동적 정보 수집 실패"

    required_fields = ['cpu_usage', 'ram_used', 'ram_usage_percent',
                     'disk_usage', 'ip_address', 'current_user', 'uptime', 'processes']
    missing = [f for f in required_fields if f not in info or info[f] is None]

    assert not missing, f"누락된 필드: {', '.join(missing)}"

    # 프로세스 목록이 JSON 파싱 가능한지 확인
    assert isinstance(info['processes'], list), "프로세스 목록이 리스트가 아님"

def test_collect_running_processes():
    """실행 중인 프로세스 목록 수집 테스트"""
    processes = collect_running_processes()
    assert processes is not None, "프로세스 목록 수집 실패"
    
    # 비어있을 수는 있지만, None이어서는 안 됨
    assert isinstance(processes, list)

# ==================== Executor 테스트 ====================

def test_execute_command_safe():
    """안전한 명령어 실행 테스트"""
    test_commands = [
        ('execute', {'command': 'echo Hello WCMS'}, 'Hello WCMS'),
        ('execute', {'command': 'hostname'}, os.environ.get('COMPUTERNAME')),
    ]

    for cmd_type, cmd_data, expected_output in test_commands:
        result = CommandExecutor.execute_command(cmd_type, cmd_data)
        assert result is not None
        assert '실패' not in result and '오류' not in result
        
        if expected_output:
            # 대소문자 무시 및 공백 제거 후 비교
            assert expected_output.lower().strip() in result.lower().strip()

def test_command_validation():
    """명령어 파라미터 검증 테스트"""
    test_cases = [
        ('install', {}, '필수 파라미터 누락 (app_name)'),
        ('execute', {}, '필수 파라미터 누락 (command)'),
        ('download', {}, '필수 파라미터 누락 (url)'),  # url 누락 테스트로 변경
        ('create_user', {'username': 'test'}, '필수 파라미터 누락 (password)'),
        ('delete_user', {}, '필수 파라미터 누락 (username)'),
        ('change_password', {'username': 'test'}, '필수 파라미터 누락 (new_password)'),
        ('unknown_command', {}, '알 수 없는 명령'),
    ]

    for cmd_type, cmd_data, description in test_cases:
        result = CommandExecutor.execute_command(cmd_type, cmd_data)
        # '오류', '알 수 없는', '프로세스 이름', '실패' 중 하나라도 포함되어야 함
        assert any(keyword in result for keyword in ['오류', '알 수 없는', '프로세스 이름', '실패']), \
            f"검증 실패: {description} -> {result}"

@pytest.mark.skip(reason="실제 시스템에 영향을 줄 수 있으므로 기본적으로 실행하지 않음")
def test_dangerous_commands():
    """위험한 명령 테스트 (실제 실행 안 함)"""
    # 이 테스트는 수동으로 실행하거나, CI 환경에서 격리된 상태로 실행해야 함
    result = CommandExecutor.execute_command('shutdown', {'delay': 0})
    assert "종료 명령 실행됨" in result

# ==================== 통합 테스트 ====================

def test_full_workflow_simulation():
    """전체 워크플로우 시뮬레이션"""
    # 1. 정적 정보 수집 (등록용)
    static_info = collect_static_info()
    assert static_info is not None

    # 2. 동적 정보 수집 (하트비트용)
    dynamic_info = collect_dynamic_info()
    assert dynamic_info is not None

    # 3. 명령 실행 시뮬레이션
    result = CommandExecutor.execute_command('execute', {'command': 'echo test'})
    assert result is not None and 'test' in result
