CREATE TABLE admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL
);

CREATE TABLE pc_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    machine_id TEXT UNIQUE NOT NULL,
    hostname TEXT,
    room_name TEXT,
    seat_number INTEGER,
    ip_address TEXT,
    is_online BOOLEAN DEFAULT 0,
    last_seen TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE pc_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pc_id INTEGER NOT NULL,
    cpu_model TEXT,
    cpu_usage REAL,
    ram_total INTEGER,
    ram_used INTEGER,
    disk_info TEXT,
    os_edition TEXT,
    ip_address TEXT,
    mac_address TEXT,
    current_user TEXT,
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

CREATE TABLE seat_layout (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_name TEXT UNIQUE NOT NULL,
    rows INTEGER DEFAULT 5,
    cols INTEGER DEFAULT 8
);

CREATE TABLE seat_map (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_name TEXT NOT NULL,
    row INTEGER NOT NULL,
    col INTEGER NOT NULL,
    pc_id INTEGER,
    FOREIGN KEY (pc_id) REFERENCES pc_info(id) ON DELETE SET NULL,
    UNIQUE(room_name, row, col)
);

CREATE INDEX idx_pc_status_pc_id ON pc_status(pc_id);
CREATE INDEX idx_pc_command_pc_id ON pc_command(pc_id);
