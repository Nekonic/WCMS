import pythoncom
import wmi
import psutil
import platform
import os
import time
import json
import socket


def get_active_network_info():
    """활성 네트워크 인터페이스의 IP와 MAC 주소 조회"""
    try:
        interfaces = psutil.net_if_addrs()
        for interface_name, addrs in interfaces.items():
            if interface_name.startswith('Loopback'):
                continue
            for addr in addrs:
                if addr.family == socket.AF_INET:
                    ip = addr.address
                    mac = get_mac_address(interface_name)
                    if mac:
                        return ip, mac
        return '127.0.0.1', '00:00:00:00:00:00'
    except Exception as e:
        print(f"[-] 네트워크 정보 조회 오류: {e}")
        return '127.0.0.1', '00:00:00:00:00:00'


def get_mac_address(interface_name):
    """특정 인터페이스의 MAC 주소 조회"""
    try:
        pythoncom.CoInitialize()
        c = wmi.WMI()
        for adapter in c.Win32_NetworkAdapter():
            if interface_name.lower() in adapter.Name.lower() or adapter.Name.lower() in interface_name.lower():
                return adapter.MACAddress
        pythoncom.CoUninitialize()
    except Exception as e:
        print(f"[-] MAC 주소 조회 오류 ({interface_name}): {e}")
    try:
        addrs = psutil.net_if_addrs()
        if interface_name in addrs:
            for addr in addrs[interface_name]:
                if addr.family == psutil.AF_LINK:
                    return addr.address
    except:
        pass
    return None


def collect_static_info():
    """정적 시스템 정보 수집 (최초 1회)"""
    pythoncom.CoInitialize()
    try:
        disk_info = {}
        try:
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disk_info[partition.device] = {'total': usage.total}
                except (PermissionError, OSError):
                    continue
        except Exception as e:
            print(f"[-] 디스크 정보 수집 오류: {e}")
            disk_info = {}

        _, mac_address = get_active_network_info()

        result = {
            'cpu_model': platform.processor(),
            'cpu_cores': psutil.cpu_count(logical=False),
            'cpu_threads': psutil.cpu_count(logical=True),
            'ram_total': int(psutil.virtual_memory().total / (1024 * 1024)),
            'disk_info': json.dumps(disk_info),
            'os_edition': platform.platform(),
            'os_version': platform.version(),
            'mac_address': mac_address,
            'hostname': socket.gethostname()
        }
        return result
    except Exception as e:
        print(f"[-] 정적 정보 수집 오류: {e}")
        return {}
    finally:
        pythoncom.CoUninitialize()


def collect_running_processes():
    """설치된 프로그램 위주의 실행 중인 프로세스 목록 수집"""
    interesting_processes = set()
    system_paths = [
        os.environ.get('SystemRoot', 'C:\\Windows').lower(),
        os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)').lower(),
        os.environ.get('ProgramFiles', 'C:\\Program Files').lower()
    ]
    # 제외할 특정 시스템 프로세스
    exclude_list = {
        'explorer.exe', 'svchost.exe', 'conhost.exe', 'runtimebroker.exe',
        'onedrive.exe', 'ctfmon.exe', 'fontdrhost.exe', 'sihost.exe',
        'startmenuexperiencehost.exe', 'searchapp.exe', 'taskhostw.exe',
        'memcompression', 'mpdefendercoreservice.exe', 'msmpeng.exe', 'nissrv.exe', 'registry'
    }

    for proc in psutil.process_iter(['name', 'exe']):
        try:
            proc_name = proc.info['name']
            proc_exe = proc.info['exe']

            if not proc_exe or proc_name.lower() in exclude_list:
                continue

            # 시스템 경로에 포함되지 않는 프로세스만 선택
            is_system_proc = any(proc_exe.lower().startswith(p) for p in system_paths)
            if not is_system_proc:
                interesting_processes.add(proc_name)

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return sorted(list(interesting_processes))


def collect_dynamic_info():
    """동적 시스템 정보 수집 (주기적)"""
    try:
        disk_usage_info = {}
        try:
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disk_usage_info[partition.device] = {
                        'used': usage.used,
                        'free': usage.free,
                    }
                except (PermissionError, OSError):
                    continue
        except Exception as e:
            print(f"[-] 디스크 사용량 수집 오류: {e}")
            disk_usage_info = {}

        ip_address, _ = get_active_network_info()
        processes = collect_running_processes()

        result = {
            'cpu_usage': psutil.cpu_percent(interval=1),
            'ram_used': int(psutil.virtual_memory().used / (1024 * 1024)),
            'ram_usage_percent': psutil.virtual_memory().percent,
            'disk_usage': json.dumps(disk_usage_info),
            'ip_address': ip_address,
            'current_user': os.getenv('USERNAME'),
            'uptime': int(time.time() - psutil.boot_time()),
            'processes': json.dumps(processes)
        }
        return result
    except Exception as e:
        print(f"[-] 동적 정보 수집 오류: {e}")
        return {}
