CREATE TABLE admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL
);

CREATE TABLE pc_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    machine_id TEXT UNIQUE NOT NULL,
    room_name TEXT NOT NULL,
    seat_number INTEGER NOT NULL,
    hostname TEXT,
    ip_address TEXT,
    mac_address TEXT,
    is_online BOOLEAN DEFAULT 0,
    last_seen TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(room_name, seat_number)
);

CREATE TABLE pc_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pc_id INTEGER NOT NULL,
    cpu_model TEXT,
    cpu_cores INTEGER,
    cpu_threads INTEGER,
    cpu_usage REAL,
    cpu_temperature REAL,
    ram_total INTEGER,
    ram_used INTEGER,
    ram_usage_percent REAL,
    ram_type TEXT,
    disk_info TEXT,
    os_edition TEXT,
    os_version TEXT,
    os_build TEXT,
    os_activated BOOLEAN,
    os_last_update TEXT,
    ip_address TEXT,
    mac_address TEXT,
    network_usage TEXT,
    gpu_model TEXT,
    gpu_vram INTEGER,
    gpu_driver TEXT,
    current_user TEXT,
    last_login TEXT,
    uptime INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pc_id) REFERENCES pc_info(id) ON DELETE CASCADE
);

CREATE TABLE pc_command (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pc_id INTEGER NOT NULL,
    command_type TEXT NOT NULL,
    command_data TEXT,
    executed BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pc_id) REFERENCES pc_info(id) ON DELETE CASCADE
);

CREATE TABLE pc_pending (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    machine_id TEXT UNIQUE NOT NULL,
    hostname TEXT,
    ip_address TEXT,
    assigned BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    processes TEXT NOT NULL,
    FOREIGN KEY (pc_id) REFERENCES pc_info(id) ON DELETE CASCADE
);

CREATE TABLE admin_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id INTEGER NOT NULL,
    pc_id INTEGER,
    action TEXT NOT NULL,
    details TEXT,
    result TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (admin_id) REFERENCES admins(id),
    FOREIGN KEY (pc_id) REFERENCES pc_info(id) ON DELETE SET NULL
);

CREATE TABLE seat_layout (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_name TEXT UNIQUE NOT NULL,
    cols INTEGER DEFAULT 10,
    rows INTEGER DEFAULT 4,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE seat_map (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_name TEXT NOT NULL,
    row INTEGER NOT NULL,
    col INTEGER NOT NULL,
    pc_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pc_id) REFERENCES pc_info(id) ON DELETE SET NULL,
    UNIQUE(room_name, row, col)
);

-- 인덱싱 (성능 최적화)
CREATE INDEX idx_pc_status_pc_id ON pc_status(pc_id);
CREATE INDEX idx_pc_status_created_at ON pc_status(created_at DESC);
CREATE INDEX idx_pc_command_pc_id_executed ON pc_command(pc_id, executed);
CREATE INDEX idx_seat_map_room ON seat_map(room_name);

-- 초기 데이터
INSERT INTO seat_layout (room_name, cols, rows) VALUES ('1실습실', 10, 4);
INSERT INTO seat_layout (room_name, cols, rows) VALUES ('2실습실', 10, 4);

-- admin 계정 (비밀번호: admin)
INSERT INTO admins (username, password_hash) VALUES (
    'admin',
    '$2b$12$Wc3N7Dnwx7t/ZSsANlAu2OvVpVSwLbHTdpIZrjzrqFbYQ6t8C7Kui'
);