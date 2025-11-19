import psutil
import platform
import socket
import json

# Windows 기본 시스템 프로세스 리스트
WINDOWS_SYSTEM_PROCESSES = {
    # 커널 및 코어 프로세스
    'System Idle', 'Registry', 'MemCompression', 'Memory Compression',
    'smss.exe', 'csrss.exe', 'wininit.exe', 'services.exe', 'lsass.exe',
    'lsaiso.exe', 'winlogon.exe', 'fontdrvhost.exe',

    # 서비스 호스트 및 관련 프로세스
    'svchost.exe', 'dllhost.exe', 'taskhost.exe', 'taskhostex.exe',
    'taskhostw.exe', 'RuntimeBroker.exe', 'sihost.exe',

    # 탐색기 및 GUI 관련
    'explorer.exe', 'dwm.exe', 'ShellExperienceHost.exe',
    'StartMenuExperienceHost.exe', 'SearchHost.exe', 'SearchUI.exe',
    'SearchApp.exe', 'SearchIndexer.exe',

    # Windows 보안 및 업데이트
    'SecurityHealthService.exe', 'SecurityHealthSystray.exe',
    'MsMpEng.exe', 'NisSrv.exe', 'SgrmBroker.exe',
    'smartscreen.exe', 'MpCmdRun.exe',

    # Windows 업데이트 및 설치
    'WUDFHost.exe', 'TiWorker.exe', 'TrustedInstaller.exe',
    'usocoreworker.exe', 'UsoClient.exe', 'wuauclt.exe',

    # Windows 스토어 및 앱
    'ApplicationFrameHost.exe', 'WinStore.App.exe',
    'AppInstaller.exe', 'WindowsInternal.ComposableShell.Experiences.TextInput.InputApp.exe',

    # 시스템 서비스
    'spoolsv.exe', 'conhost.exe', 'backgroundTaskHost.exe',
    'ctfmon.exe', 'TextInputHost.exe', 'TabTip.exe',
    'LogonUI.exe', 'LockApp.exe', 'UserOOBEBroker.exe',

    # Windows 이벤트 및 로그
    'wininit.exe', 'WmiPrvSE.exe', 'audiodg.exe',

    # 기타 Windows 기본 프로세스
    'SystemSettingsBroker.exe', 'SystemSettings.exe',
    'PickerHost.exe', 'Widgets.exe', 'WidgetService.exe',
    'PhoneExperienceHost.exe', 'YourPhone.exe',
    'ProcessWindowsTerminal',
}

def collect_static_info():
    """정적 시스템 정보 수집 (한 번만 수집)"""
    try:
        # CPU 정보
        cpu_model = platform.processor() or "Unknown CPU"
        cpu_cores = psutil.cpu_count(logical=False) or 1
        cpu_threads = psutil.cpu_count(logical=True) or 1

        # RAM 정보
        ram = psutil.virtual_memory()
        ram_total = ram.total // (1024 * 1024)  # MB 단위

        # 디스크 정보
        disk_info = {}
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_info[partition.device] = {
                    "total": usage.total,
                    "fstype": partition.fstype,
                    "mountpoint": partition.mountpoint
                }
            except:
                pass

        # OS 정보
        os_edition = f"{platform.system()} {platform.release()}"
        os_version = platform.version()

        # 호스트명
        hostname = socket.gethostname()

        # MAC 주소
        mac_address = None
        for interface, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if addr.family == psutil.AF_LINK:
                    mac_address = addr.address
                    break
            if mac_address:
                break

        return {
            "hostname": hostname,
            "mac_address": mac_address or "00:00:00:00:00:00",
            "cpu_model": cpu_model,
            "cpu_cores": cpu_cores,
            "cpu_threads": cpu_threads,
            "ram_total": ram_total,
            "disk_info": json.dumps(disk_info),
            "os_edition": os_edition,
            "os_version": os_version
        }
    except Exception as e:
        print(f"[!] 정적 정보 수집 오류: {e}")
        return None


def collect_dynamic_info():
    """동적 시스템 정보 수집 (주기적으로 수집)"""
    try:
        # CPU 사용률
        cpu_usage = psutil.cpu_percent(interval=1)

        # RAM 사용량
        ram = psutil.virtual_memory()
        ram_used = ram.used // (1024 * 1024)  # MB
        ram_usage_percent = ram.percent

        # 디스크 사용량
        disk_usage = {}
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_usage[partition.device] = {
                    "used": usage.used,
                    "free": usage.free,
                    "percent": usage.percent
                }
            except:
                pass

        # IP 주소
        ip_address = "Unknown"
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip_address = s.getsockname()[0]
            s.close()
        except:
            pass

        # 현재 사용자
        import getpass
        current_user = getpass.getuser()

        # 업타임 (부팅 후 경과 시간)
        import time
        uptime = int(time.time() - psutil.boot_time())

        # 실행 중인 프로세스
        processes = []
        for proc in psutil.process_iter(['name']):
            try:
                proc_name = proc.info['name']
                if proc_name not in WINDOWS_SYSTEM_PROCESSES:
                    processes.append(proc_name)
            except:
                pass
        # 중복 제거 및 정렬
        processes = sorted(list(set(processes)))

        return {
            "cpu_usage": cpu_usage,
            "ram_used": ram_used,
            "ram_usage_percent": ram_usage_percent,
            "disk_usage": json.dumps(disk_usage),
            "ip_address": ip_address,
            "current_user": current_user,
            "uptime": uptime,
            "processes": json.dumps(processes)
        }
    except Exception as e:
        print(f"[!] 동적 정보 수집 오류: {e}")
        return None


def collect_running_processes():
    """실행 중인 프로세스 목록 수집"""
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'username', 'memory_info']):
            try:
                processes.append({
                    'pid': proc.info['pid'],
                    'name': proc.info['name'],
                    'username': proc.info['username'],
                    'memory': proc.info['memory_info'].rss // (1024 * 1024)  # MB
                })
            except:
                pass
        return processes
    except Exception as e:
        print(f"[!] 프로세스 목록 수집 오류: {e}")
        return []

