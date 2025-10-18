CREATE TABLE pc_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pc_id INTEGER NOT NULL,

    -- CPU 정보
    cpu_model TEXT,
    cpu_cores INTEGER,
    cpu_threads INTEGER,
    cpu_usage REAL,
    cpu_temperature REAL,

    -- 메모리 정보
    ram_total INTEGER,                -- MB 단위
    ram_used INTEGER,
    ram_usage_percent REAL,
    ram_type TEXT,                    -- DDR4/DDR5

    -- 디스크 정보 (JSON)
    disk_info TEXT,                   -- [{"drive": "C:", "total": 500, "used": 200, "type": "SSD"}]

    -- Windows 정보
    os_edition TEXT,                  -- Pro/Home/Education
    os_version TEXT,                  -- 22H2, 23H2
    os_build TEXT,
    os_activated BOOLEAN,
    os_last_update TEXT,

    -- 네트워크 정보
    ip_address TEXT,
    mac_address TEXT,
    network_usage TEXT,               -- JSON: {"sent": 1024, "recv": 2048}

    -- GPU 정보
    gpu_model TEXT,
    gpu_vram INTEGER,                 -- MB
    gpu_driver TEXT,

    -- 기타
    current_user TEXT,
    last_login TEXT,
    uptime INTEGER,                   -- 초 단위

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pc_id) REFERENCES pc_info(id) ON DELETE CASCADE
);

CREATE TABLE pc_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    machine_id TEXT UNIQUE NOT NULL,  -- 기기 고유 ID
    room_name TEXT NOT NULL,          -- 실습실 이름 (예: "1실습실")
    seat_number INTEGER NOT NULL,     -- 좌석 번호
    hostname TEXT,
    last_seen TIMESTAMP,              -- 마지막 접속 시간
    is_online BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address TEXT,
    mac_address TEXT,
    UNIQUE(room_name, seat_number)
);

CREATE TABLE installed_programs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pc_id INTEGER NOT NULL,
    program_name TEXT NOT NULL,
    version TEXT,
    publisher TEXT,
    install_date TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pc_id) REFERENCES pc_info(id) ON DELETE CASCADE,
    UNIQUE(pc_id, program_name, version)
);

CREATE TABLE running_processes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pc_id INTEGER NOT NULL,
    snapshot_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processes TEXT NOT NULL,          -- JSON: [{"name": "chrome.exe", "pid": 1234, "memory": 500}]
    FOREIGN KEY (pc_id) REFERENCES pc_info(id) ON DELETE CASCADE
);

CREATE TABLE admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL
);


CREATE TABLE admin_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id INTEGER NOT NULL,
    pc_id INTEGER,
    action TEXT NOT NULL,             -- shutdown, reboot, execute_cmd, bulk_shutdown
    details TEXT,                     -- JSON: {"command": "ipconfig", "target_pcs": [1,2,3]}
    result TEXT,                      -- success/failed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (admin_id) REFERENCES admins(id),
    FOREIGN KEY (pc_id) REFERENCES pc_info(id)
);

--- 테스트 데이터

-- 비밀번호: admin
INSERT INTO admins (id,username, password_hash) VALUES (
    0,
    'admin',
    '$2b$12$Wc3N7Dnwx7t/ZSsANlAu2OvVpVSwLbHTdpIZrjzrqFbYQ6t8C7Kui'
);


-- PC 기본 정보 (실습실 1: 20대, 실습실 2: 20대)
INSERT INTO pc_info (machine_id, room_name, seat_number, hostname, is_online, ip_address, mac_address) VALUES
-- 1실습실
('MACHINE-101', '1실습실', 1, 'PC-101', 1, '192.168.1.101', 'AA:BB:CC:DD:EE:01'),
('MACHINE-102', '1실습실', 2, 'PC-102', 0, '192.168.1.102', 'AA:BB:CC:DD:EE:02'),
('MACHINE-103', '1실습실', 3, 'PC-103', 1, '192.168.1.103', 'AA:BB:CC:DD:EE:03'),
('MACHINE-104', '1실습실', 4, 'PC-104', 1, '192.168.1.104', 'AA:BB:CC:DD:EE:04'),
('MACHINE-105', '1실습실', 5, 'PC-105', 0, '192.168.1.105', 'AA:BB:CC:DD:EE:05'),
('MACHINE-106', '1실습실', 6, 'PC-106', 1, '192.168.1.106', 'AA:BB:CC:DD:EE:06'),
('MACHINE-107', '1실습실', 7, 'PC-107', 1, '192.168.1.107', 'AA:BB:CC:DD:EE:07'),
('MACHINE-108', '1실습실', 8, 'PC-108', 0, '192.168.1.108', 'AA:BB:CC:DD:EE:08'),
('MACHINE-109', '1실습실', 9, 'PC-109', 1, '192.168.1.109', 'AA:BB:CC:DD:EE:09'),
('MACHINE-110', '1실습실', 10, 'PC-110', 1, '192.168.1.110', 'AA:BB:CC:DD:EE:10'),
('MACHINE-111', '1실습실', 11, 'PC-111', 0, '192.168.1.111', 'AA:BB:CC:DD:EE:11'),
('MACHINE-112', '1실습실', 12, 'PC-112', 1, '192.168.1.112', 'AA:BB:CC:DD:EE:12'),
('MACHINE-113', '1실습실', 13, 'PC-113', 1, '192.168.1.113', 'AA:BB:CC:DD:EE:13'),
('MACHINE-114', '1실습실', 14, 'PC-114', 0, '192.168.1.114', 'AA:BB:CC:DD:EE:14'),
('MACHINE-115', '1실습실', 15, 'PC-115', 1, '192.168.1.115', 'AA:BB:CC:DD:EE:15'),
('MACHINE-116', '1실습실', 16, 'PC-116', 1, '192.168.1.116', 'AA:BB:CC:DD:EE:16'),
('MACHINE-117', '1실습실', 17, 'PC-117', 0, '192.168.1.117', 'AA:BB:CC:DD:EE:17'),
('MACHINE-118', '1실습실', 18, 'PC-118', 1, '192.168.1.118', 'AA:BB:CC:DD:EE:18'),
('MACHINE-119', '1실습실', 19, 'PC-119', 1, '192.168.1.119', 'AA:BB:CC:DD:EE:19'),
('MACHINE-120', '1실습실', 20, 'PC-120', 0, '192.168.1.120', 'AA:BB:CC:DD:EE:20'),
-- 2실습실
('MACHINE-201', '2실습실', 1, 'PC-201', 1, '192.168.2.101', 'AA:BB:CC:DD:FF:01'),
('MACHINE-202', '2실습실', 2, 'PC-202', 0, '192.168.2.102', 'AA:BB:CC:DD:FF:02'),
('MACHINE-203', '2실습실', 3, 'PC-203', 1, '192.168.2.103', 'AA:BB:CC:DD:FF:03'),
('MACHINE-204', '2실습실', 4, 'PC-204', 1, '192.168.2.104', 'AA:BB:CC:DD:FF:04'),
('MACHINE-205', '2실습실', 5, 'PC-205', 0, '192.168.2.105', 'AA:BB:CC:DD:FF:05'),
('MACHINE-206', '2실습실', 6, 'PC-206', 1, '192.168.2.106', 'AA:BB:CC:DD:FF:06'),
('MACHINE-207', '2실습실', 7, 'PC-207', 1, '192.168.2.107', 'AA:BB:CC:DD:FF:07'),
('MACHINE-208', '2실습실', 8, 'PC-208', 0, '192.168.2.108', 'AA:BB:CC:DD:FF:08'),
('MACHINE-209', '2실습실', 9, 'PC-209', 1, '192.168.2.109', 'AA:BB:CC:DD:FF:09'),
('MACHINE-210', '2실습실', 10, 'PC-210', 1, '192.168.2.110', 'AA:BB:CC:DD:FF:10'),
('MACHINE-211', '2실습실', 11, 'PC-211', 0, '192.168.2.111', 'AA:BB:CC:DD:FF:11'),
('MACHINE-212', '2실습실', 12, 'PC-212', 1, '192.168.2.112', 'AA:BB:CC:DD:FF:12'),
('MACHINE-213', '2실습실', 13, 'PC-213', 1, '192.168.2.113', 'AA:BB:CC:DD:FF:13'),
('MACHINE-214', '2실습실', 14, 'PC-214', 0, '192.168.2.114', 'AA:BB:CC:DD:FF:14'),
('MACHINE-215', '2실습실', 15, 'PC-215', 1, '192.168.2.115', 'AA:BB:CC:DD:FF:15'),
('MACHINE-216', '2실습실', 16, 'PC-216', 1, '192.168.2.116', 'AA:BB:CC:DD:FF:16'),
('MACHINE-217', '2실습실', 17, 'PC-217', 0, '192.168.2.117', 'AA:BB:CC:DD:FF:17'),
('MACHINE-218', '2실습실', 18, 'PC-218', 1, '192.168.2.118', 'AA:BB:CC:DD:FF:18'),
('MACHINE-219', '2실습실', 19, 'PC-219', 1, '192.168.2.119', 'AA:BB:CC:DD:FF:19'),
('MACHINE-220', '2실습실', 20, 'PC-220', 0, '192.168.2.120', 'AA:BB:CC:DD:FF:20');

-- PC 상세 상태 (온라인인 PC만 샘플 데이터)
INSERT INTO pc_status (pc_id, cpu_model, cpu_cores, cpu_threads, cpu_usage, ram_total, ram_used, ram_usage_percent, ram_type, disk_info, os_edition, os_version, os_build, os_activated, ip_address, mac_address, gpu_model, gpu_vram, current_user, uptime) VALUES
(1, 'Intel i5-10400', 6, 12, 45.2, 8192, 4096, 50.0, 'DDR4', '{"C:": {"total": 500, "used": 250, "type": "SSD"}}', 'Windows 10 Pro', '22H2', '19045', 1, '192.168.1.101', 'AA:BB:CC:DD:EE:01', 'NVIDIA GTX 1650', 4096, 'student01', 3600),
(3, 'Intel i5-10400', 6, 12, 32.1, 8192, 3500, 42.7, 'DDR4', '{"C:": {"total": 500, "used": 200, "type": "SSD"}}', 'Windows 10 Pro', '22H2', '19045', 1, '192.168.1.103', 'AA:BB:CC:DD:EE:03', 'NVIDIA GTX 1650', 4096, 'student03', 7200),
(4, 'Intel i5-10400', 6, 12, 78.5, 8192, 6000, 73.2, 'DDR4', '{"C:": {"total": 500, "used": 450, "type": "SSD"}}', 'Windows 10 Pro', '22H2', '19045', 1, '192.168.1.104', 'AA:BB:CC:DD:EE:04', 'NVIDIA GTX 1650', 4096, 'student04', 1800),
(6, 'Intel i5-10400', 6, 12, 25.0, 8192, 3000, 36.6, 'DDR4', '{"C:": {"total": 500, "used": 180, "type": "SSD"}}', 'Windows 10 Pro', '22H2', '19045', 1, '192.168.1.106', 'AA:BB:CC:DD:EE:06', 'NVIDIA GTX 1650', 4096, 'student06', 5400),
(21, 'Intel i7-10700', 8, 16, 55.3, 16384, 8192, 50.0, 'DDR4', '{"C:": {"total": 1000, "used": 500, "type": "SSD"}}', 'Windows 11 Edu', '23H2', '22631', 1, '192.168.2.101', 'AA:BB:CC:DD:FF:01', 'NVIDIA RTX 3060', 8192, 'student21', 4200),
(23, 'Intel i7-10700', 8, 16, 41.2, 16384, 7000, 42.7, 'DDR4', '{"C:": {"total": 1000, "used": 400, "type": "SSD"}}', 'Windows 11 Edu', '23H2', '22631', 1, '192.168.2.103', 'AA:BB:CC:DD:FF:03', 'NVIDIA RTX 3060', 8192, 'student23', 6000);
