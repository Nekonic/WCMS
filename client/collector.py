"""
시스템 정보 수집 모듈
정적 정보(CPU, RAM, 디스크)와 동적 정보(CPU/RAM 사용률, 프로세스)를 수집합니다.
"""
import psutil
import platform
import socket
import json
import os
import sys
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

# 클라이언트 디렉토리를 sys.path에 추가 (이 모듈이 실행될 때마다)
client_dir = Path(__file__).parent
if str(client_dir) not in sys.path:
    sys.path.insert(0, str(client_dir))

from utils import load_json_file

logger = logging.getLogger('wcms')


def _load_system_processes() -> set:
    """시스템 프로세스 목록을 JSON 파일에서 로드"""
    json_path = os.path.join(os.path.dirname(__file__), 'data', 'system_processes.json')
    processes = load_json_file(json_path, default=[])
    return set(processes) if isinstance(processes, list) else set()

# 시스템 프로세스 로드 (한 번만)
WINDOWS_SYSTEM_PROCESSES = _load_system_processes()


def collect_static_info() -> Optional[Dict[str, Any]]:
    """정적 시스템 정보 수집 (한 번만 수집)"""
    try:
        # CPU 정보 - WMI로 정확한 모델명 가져오기
        cpu_model = "Unknown CPU"
        try:
            import wmi
            c = wmi.WMI()
            for processor in c.Win32_Processor():
                cpu_model = processor.Name.strip()
                break
        except:
            # WMI 실패 시 platform 사용
            cpu_model = platform.processor() or "Unknown CPU"

        cpu_cores = psutil.cpu_count(logical=False) or 1
        cpu_threads = psutil.cpu_count(logical=True) or 1

        # RAM 정보 - GB 단위로 변경
        ram = psutil.virtual_memory()
        ram_total_gb = round(ram.total / (1024 ** 3), 2)  # GB 단위, 소수점 2자리

        # 디스크 정보 - GB 단위로 변경 (고정 디스크만)
        disk_info = {}
        for partition in psutil.disk_partitions(all=False):
            if 'fixed' not in partition.opts.lower():
                continue
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_info[partition.device] = {
                    "total_gb": round(usage.total / (1024 ** 3), 2),
                    "fstype": partition.fstype,
                    "mountpoint": partition.mountpoint
                }
            except:
                pass

        # OS 정보 - Windows 에디션 및 버전 정확하게 감지
        os_name = platform.system()
        os_release = platform.release()
        os_edition_detail = ""

        if os_name == "Windows":
            try:
                import sys
                # Windows 11 감지 (빌드 번호 22000 이상)
                if sys.getwindowsversion().build >= 22000:
                    os_release = "11"

                # WMI로 상세 에디션 정보 가져오기
                try:
                    import wmi
                    c = wmi.WMI()
                    for os_info in c.Win32_OperatingSystem():
                        # Caption 예: "Microsoft Windows 11 Pro"
                        caption = os_info.Caption
                        if caption:
                            # "Microsoft Windows" 제거하고 버전과 에디션만 추출
                            caption = caption.replace("Microsoft Windows", "").strip()
                            # 숫자(10, 11)를 제외한 나머지가 에디션
                            parts = caption.split()
                            edition_parts = []
                            for part in parts:
                                if part not in ['10', '11', 'Windows']:
                                    edition_parts.append(part)
                            if edition_parts:
                                os_edition_detail = " ".join(edition_parts)
                        break
                except:
                    pass

                # WMI 실패 시 레지스트리로 시도
                if not os_edition_detail:
                    try:
                        import winreg
                        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                            r"SOFTWARE\Microsoft\Windows NT\CurrentVersion")
                        os_edition_detail, _ = winreg.QueryValueEx(key, "EditionID")
                        winreg.CloseKey(key)
                    except:
                        pass
            except:
                pass

        # 최종 OS 에디션 문자열 구성
        if os_edition_detail:
            os_edition = f"{os_name} {os_release} {os_edition_detail}"
        else:
            os_edition = f"{os_name} {os_release}"

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
            "ram_total": ram_total_gb,  # GB 단위
            "disk_info": disk_info,  # dict 그대로 전송 (이중 인코딩 방지)
            "os_edition": os_edition,
            "os_version": os_version
        }
    except Exception as e:
        print(f"[!] 정적 정보 수집 오류: {e}")
        return None


def collect_dynamic_info() -> Optional[Dict[str, Any]]:
    """동적 시스템 정보 수집 (주기적으로 수집)"""
    try:
        # CPU 사용률
        cpu_usage = psutil.cpu_percent(interval=1)

        # RAM 사용량 - GB 단위로 변경
        ram = psutil.virtual_memory()
        ram_used_gb = round(ram.used / (1024 ** 3), 2)  # GB 단위
        ram_usage_percent = ram.percent

        # 디스크 사용량 - GB 단위로 변경 (고정 디스크만)
        disk_usage = {}
        for partition in psutil.disk_partitions(all=False):
            if 'fixed' not in partition.opts.lower():
                continue
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_usage[partition.device] = {
                    "used_gb": round(usage.used / (1024 ** 3), 2),
                    "free_gb": round(usage.free / (1024 ** 3), 2),
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
            "ram_used": ram_used_gb,  # GB 단위
            "ram_usage_percent": ram_usage_percent,
            "disk_usage": disk_usage,  # dict 그대로 전송 (이중 인코딩 방지)
            "ip_address": ip_address,
            "current_user": current_user,
            "uptime": uptime,
            "processes": processes  # list 그대로 전송 (이중 인코딩 방지)
        }
    except Exception as e:
        print(f"[!] 동적 정보 수집 오류: {e}")
        return None


def collect_running_processes() -> List[Dict[str, Any]]:
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
