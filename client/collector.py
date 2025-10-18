import platform
import psutil

def collect_system_info():
    return {
        "cpu_model": platform.processor(),
        "cpu_cores": psutil.cpu_count(logical=False),
        "cpu_threads": psutil.cpu_count(logical=True),
        "cpu_usage": psutil.cpu_percent(interval=1),
        "ram_total": int(psutil.virtual_memory().total / 1024 / 1024),
        "ram_used": int(psutil.virtual_memory().used / 1024 / 1024),
        "ram_usage_percent": psutil.virtual_memory().percent,
        "disk_info": str({part.device: {
            "total": int(psutil.disk_usage(part.mountpoint).total / 1024 / 1024),
            "used": int(psutil.disk_usage(part.mountpoint).used / 1024 / 1024),
            "type": "SSD/HDD"  # 실제 구분은 나중애
        } for part in psutil.disk_partitions() if 'cdrom' not in part.opts}),
        "os_edition": platform.system() + " " + platform.release(),
        "os_version": platform.version(),
        "ip_address": psutil.net_if_addrs()['Ethernet'][0].address if 'Ethernet' in psutil.net_if_addrs() else "127.0.0.1",
        "mac_address": psutil.net_if_addrs()['Ethernet'][0].address if 'Ethernet' in psutil.net_if_addrs() else "00:00:00:00:00:00",
        "current_user": platform.node(),
        "uptime": int(psutil.boot_time())
    }
