import pythoncom
import wmi
import psutil
import platform
import os
import time
import json
import socket
import subprocess


def get_active_network_info():
    """활성 네트워크 인터페이스의 IP와 MAC 주소 조회"""
    try:
        # 모든 네트워크 인터페이스 정보
        interfaces = psutil.net_if_addrs()

        # 활성 인터페이스 찾기 (loopback 제외)
        for interface_name, addrs in interfaces.items():
            if interface_name.startswith('Loopback'):
                continue

            for addr in addrs:
                # IPv4 주소 찾기
                if addr.family == socket.AF_INET:
                    ip = addr.address
                    # MAC 주소는 따로 조회
                    mac = get_mac_address(interface_name)
                    if mac:
                        return ip, mac

        # 활성 인터페이스 없으면 127.0.0.1 반환
        return '127.0.0.1', '00:00:00:00:00:00'
    except Exception as e:
        print(f"[-] 네트워크 정보 조회 오류: {e}")
        return '127.0.0.1', '00:00:00:00:00:00'


def get_mac_address(interface_name):
    """특정 인터페이스의 MAC 주소 조회"""
    try:
        pythoncom.CoInitialize()
        c = wmi.WMI()

        # Win32_NetworkAdapterConfiguration으로 MAC 주소 조회
        for adapter in c.Win32_NetworkAdapter():
            if interface_name.lower() in adapter.Name.lower() or adapter.Name.lower() in interface_name.lower():
                return adapter.MACAddress

        pythoncom.CoUninitialize()
    except Exception as e:
        print(f"[-] MAC 주소 조회 오류 ({interface_name}): {e}")

    # 폴백: psutil에서 MAC 주소 가져오기
    try:
        addrs = psutil.net_if_addrs()
        if interface_name in addrs:
            for addr in addrs[interface_name]:
                if addr.family == psutil.AF_LINK:
                    return addr.address
    except:
        pass

    return None


def get_disk_types():
    """WMI를 사용하여 디스크 타입 조회"""
    pythoncom.CoInitialize()
    try:
        c = wmi.WMI()
        disk_types = {}

        try:
            for disk in c.MSFT_PhysicalDisk():
                disk_type = {3: "HDD", 4: "SSD", 5: "SCM"}.get(disk.MediaType, "Unknown")
                disk_types[disk.DeviceId] = disk_type
        except Exception as e:
            print(f"[-] MSFT_PhysicalDisk 쿼리 실패: {e}")

        # 논리 드라이브와 물리 디스크 매핑
        drive_types = {}
        try:
            for partition in c.Win32_DiskPartition():
                disk_index = partition.DiskIndex
                for logical in c.Win32_LogicalDisk():
                    for assoc in c.Win32_LogicalDiskToPartition():
                        if (assoc.Dependent.DeviceID == logical.DeviceID and
                                assoc.Antecedent.DeviceID == partition.DeviceID):
                            drive_types[logical.DeviceID + "\\"] = disk_types.get(str(disk_index), "Unknown")
        except Exception as e:
            print(f"[-] 드라이브 타입 매핑 실패: {e}")

        return drive_types
    except Exception as e:
        print(f"[-] WMI 디스크 정보 오류: {e}")
        return {}
    finally:
        pythoncom.CoUninitialize()


def collect_system_info():
    """시스템 정보 수집"""
    pythoncom.CoInitialize()
    try:
        # 디스크 정보 수집 (문자열로 직렬화)
        disk_info = {}
        try:
            for partition in psutil.disk_partitions():
                drive = partition.mountpoint
                usage = psutil.disk_usage(drive)
                disk_info[drive] = {
                    'total': int(usage.total / (1024 * 1024)),  # MB 단위
                    'used': int(usage.used / (1024 * 1024)),
                    'free': int(usage.free / (1024 * 1024))
                }
        except Exception as e:
            print(f"[-] 디스크 정보 수집 오류: {e}")
            disk_info = {}

        # IP와 MAC 주소 조회
        ip_address, mac_address = get_active_network_info()

        result = {
            'cpu_model': platform.processor(),
            'cpu_cores': psutil.cpu_count(logical=False),
            'cpu_threads': psutil.cpu_count(logical=True),
            'cpu_usage': psutil.cpu_percent(interval=1),
            'ram_total': int(psutil.virtual_memory().total / (1024 * 1024)),  # MB 단위
            'ram_used': int(psutil.virtual_memory().used / (1024 * 1024)),
            'ram_usage_percent': psutil.virtual_memory().percent,
            'disk_info': json.dumps(disk_info),
            'os_edition': platform.platform(),
            'os_version': platform.version(),
            'ip_address': ip_address,  # ← 실제 IP
            'mac_address': mac_address,  # ← 실제 MAC
            'current_user': os.getenv('USERNAME'),
            'uptime': int(time.time() - psutil.boot_time())
        }

        return result
    except Exception as e:
        print(f"[-] 시스템 정보 수집 오류: {e}")
        return {}
    finally:
        pythoncom.CoUninitialize()
