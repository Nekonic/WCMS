import platform
import psutil
import wmi


def get_disk_types():
    c = wmi.WMI()
    disk_types = {}

    try:
        # Windows 8+ : MSFT_PhysicalDisk 사용
        for disk in c.MSFT_PhysicalDisk():
            disk_type = {3: "HDD", 4: "SSD", 5: "SCM"}.get(disk.MediaType, "Unknown")
            disk_types[disk.DeviceId] = disk_type

        # 논리 드라이브와 물리 디스크 매핑
        drive_types = {}
        for partition in c.Win32_DiskPartition():
            disk_index = partition.DiskIndex
            for logical in c.Win32_LogicalDisk():
                for assoc in c.Win32_LogicalDiskToPartition():
                    if (assoc.Dependent.DeviceID == logical.DeviceID and
                            assoc.Antecedent.DeviceID == partition.DeviceID):
                        drive_types[logical.DeviceID + "\\"] = disk_types.get(str(disk_index), "Unknown")
        return drive_types
    except:
        # 폴백: Win32_DiskDrive 사용
        drive_types = {}
        for disk in c.Win32_DiskDrive():
            model = disk.Model.upper() if disk.Model else ""
            disk_type = "SSD" if ("SSD" in model or "NVME" in model) else "HDD"
            for partition in disk.associators("Win32_DiskDriveToDiskPartition"):
                for logical in partition.associators("Win32_LogicalDiskToPartition"):
                    drive_types[logical.DeviceID + "\\"] = disk_type
        return drive_types

def collect_system_info():
    disk_types = get_disk_types()

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
            "type": disk_types.get(part.device, "Unknown")  # 변경됨
        } for part in psutil.disk_partitions() if 'cdrom' not in part.opts}),
        "os_edition": platform.system() + " " + platform.release(),
        "os_version": platform.version(),
        "ip_address": psutil.net_if_addrs()['Ethernet'][0].address if 'Ethernet' in psutil.net_if_addrs() else "127.0.0.1",
        "mac_address": psutil.net_if_addrs()['Ethernet'][0].address if 'Ethernet' in psutil.net_if_addrs() else "00:00:00:00:00:00",
        "current_user": platform.node(),
        "uptime": int(psutil.boot_time())
    }
