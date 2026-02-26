-- ==================== WCMS 데이터베이스 스키마 ====================
-- 버전: 3.0 (v0.9.2)
-- 변경: admin_logs 제거, 미사용 뷰 제거, retry 필드 제거, network_events 추가

-- ==================== 관리자 ====================
CREATE TABLE admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    email TEXT,
    is_active BOOLEAN DEFAULT 1,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_admins_username ON admins(username);
CREATE INDEX idx_admins_active ON admins(is_active);

-- ==================== 등록 토큰 (v0.8.0 PIN 인증) ====================
CREATE TABLE pc_registration_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token TEXT UNIQUE NOT NULL,
    usage_type TEXT NOT NULL DEFAULT 'single',   -- single: 1회, multi: 재사용
    expires_in INTEGER NOT NULL DEFAULT 600,
    is_expired BOOLEAN DEFAULT 0,
    used_count INTEGER DEFAULT 0,
    created_by TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);

CREATE INDEX idx_registration_tokens_token ON pc_registration_tokens(token);
CREATE INDEX idx_registration_tokens_expires ON pc_registration_tokens(expires_at);
CREATE INDEX idx_registration_tokens_created_by ON pc_registration_tokens(created_by);

-- ==================== PC 기본 정보 ====================
CREATE TABLE pc_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    machine_id TEXT UNIQUE NOT NULL,
    hostname TEXT NOT NULL,
    mac_address TEXT NOT NULL,
    room_name TEXT,
    seat_number TEXT,          -- "3, 2" 형식 (row, col)
    ip_address TEXT,
    is_online BOOLEAN DEFAULT 0,
    last_seen TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_verified BOOLEAN DEFAULT 0,
    registered_with_token TEXT,
    verified_at TIMESTAMP
);

CREATE INDEX idx_pc_info_machine_id ON pc_info(machine_id);
CREATE INDEX idx_pc_info_room ON pc_info(room_name, is_online);
CREATE INDEX idx_pc_info_online ON pc_info(is_online, last_seen DESC);
CREATE INDEX idx_pc_info_verified ON pc_info(is_verified);

-- ==================== PC 하드웨어 스펙 (정적 정보) ====================
CREATE TABLE pc_specs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pc_id INTEGER UNIQUE NOT NULL,
    cpu_model TEXT NOT NULL,
    cpu_cores INTEGER NOT NULL,
    cpu_threads INTEGER NOT NULL,
    ram_total REAL NOT NULL,       -- GB
    disk_info TEXT NOT NULL,       -- JSON: {"C:\\": {"total_gb": 237.0, "fstype": "NTFS"}}
    os_edition TEXT NOT NULL,
    os_version TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pc_id) REFERENCES pc_info(id) ON DELETE CASCADE
);

CREATE INDEX idx_pc_specs_pc_id ON pc_specs(pc_id);

-- ==================== PC 동적 상태 ====================
CREATE TABLE pc_dynamic_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pc_id INTEGER UNIQUE NOT NULL,
    cpu_usage REAL NOT NULL,
    ram_used REAL NOT NULL,            -- GB
    ram_usage_percent REAL NOT NULL,
    disk_usage TEXT,                   -- JSON: {"C:\\": {"used_gb": 107.2, "percent": 45.2}}
    current_user TEXT,
    uptime INTEGER NOT NULL,           -- 초
    processes TEXT,                    -- JSON: ["chrome.exe", "Code.exe"]
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pc_id) REFERENCES pc_info(id) ON DELETE CASCADE
);

CREATE INDEX idx_pc_dynamic_info_pc_id ON pc_dynamic_info(pc_id);
CREATE INDEX idx_pc_dynamic_info_updated ON pc_dynamic_info(updated_at DESC);

-- ==================== 명령 큐 ====================
CREATE TABLE commands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pc_id INTEGER NOT NULL,
    admin_username TEXT,
    command_type TEXT NOT NULL,        -- shutdown, reboot, create_user, execute, ...
    command_data TEXT,                 -- JSON 파라미터
    priority INTEGER DEFAULT 5,        -- 1(긴급) ~ 10(낮음)
    status TEXT DEFAULT 'pending',     -- pending, executing, completed, error, timeout
    result TEXT,
    error_message TEXT,
    timeout_seconds INTEGER DEFAULT 300,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (pc_id) REFERENCES pc_info(id) ON DELETE CASCADE
);

-- pc_id + pending 상태 필터링에 최적화된 부분 인덱스
CREATE INDEX idx_commands_pending ON commands(pc_id, priority ASC, created_at ASC)
    WHERE status = 'pending';
CREATE INDEX idx_commands_pc_status ON commands(pc_id, status, created_at DESC);
CREATE INDEX idx_commands_admin ON commands(admin_username, created_at DESC);

-- ==================== 좌석 배치 ====================
CREATE TABLE seat_layout (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_name TEXT UNIQUE NOT NULL,
    rows INTEGER NOT NULL DEFAULT 6,
    cols INTEGER NOT NULL DEFAULT 8,
    description TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_seat_layout_room ON seat_layout(room_name, is_active);

CREATE TABLE seat_map (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_name TEXT NOT NULL,
    row INTEGER NOT NULL,
    col INTEGER NOT NULL,
    pc_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pc_id) REFERENCES pc_info(id) ON DELETE SET NULL,
    FOREIGN KEY (room_name) REFERENCES seat_layout(room_name) ON DELETE CASCADE,
    UNIQUE(room_name, row, col)
);

CREATE INDEX idx_seat_map_room ON seat_map(room_name);
CREATE INDEX idx_seat_map_pc ON seat_map(pc_id);

-- ==================== 네트워크 이벤트 (v0.9.2) ====================
-- PC 오프라인/온라인 이력 (shutdown / network_error / timeout)
CREATE TABLE network_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pc_id INTEGER NOT NULL,
    offline_at TIMESTAMP NOT NULL,
    online_at TIMESTAMP,
    duration_sec INTEGER,
    reason TEXT NOT NULL DEFAULT 'unknown',
    FOREIGN KEY (pc_id) REFERENCES pc_info(id) ON DELETE CASCADE
);

CREATE INDEX idx_network_events_pc ON network_events(pc_id, offline_at DESC);
CREATE INDEX idx_network_events_open ON network_events(pc_id, offline_at DESC)
    WHERE online_at IS NULL;

-- ==================== 클라이언트 버전 관리 ====================
CREATE TABLE client_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version TEXT NOT NULL,
    download_url TEXT,
    changelog TEXT,
    released_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_client_versions_released ON client_versions(released_at DESC);

-- ==================== 트리거 ====================

-- pc_info 업데이트 시 updated_at 갱신
CREATE TRIGGER update_pc_info_timestamp
AFTER UPDATE ON pc_info
FOR EACH ROW
BEGIN
    UPDATE pc_info SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- pc_specs 업데이트 시 updated_at 갱신
CREATE TRIGGER update_pc_specs_timestamp
AFTER UPDATE ON pc_specs
FOR EACH ROW
BEGIN
    UPDATE pc_specs SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- seat_layout 업데이트 시 updated_at 갱신
CREATE TRIGGER update_seat_layout_timestamp
AFTER UPDATE ON seat_layout
FOR EACH ROW
BEGIN
    UPDATE seat_layout SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER update_seat_map_timestamp
AFTER UPDATE ON seat_map
FOR EACH ROW
BEGIN
    UPDATE seat_map SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- pc_dynamic_info INSERT → PC 온라인 표시
CREATE TRIGGER update_pc_online_status_insert
AFTER INSERT ON pc_dynamic_info
FOR EACH ROW
BEGIN
    UPDATE pc_info
    SET is_online = 1,
        last_seen = CURRENT_TIMESTAMP,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.pc_id;
END;

-- pc_dynamic_info UPDATE → PC 온라인 표시
CREATE TRIGGER update_pc_online_status_update
AFTER UPDATE ON pc_dynamic_info
FOR EACH ROW
BEGIN
    UPDATE pc_info
    SET is_online = 1,
        last_seen = CURRENT_TIMESTAMP,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.pc_id;
END;

-- 명령 executing 전환 시 started_at 자동 설정
CREATE TRIGGER set_command_started_at
AFTER UPDATE ON commands
FOR EACH ROW
WHEN NEW.status = 'executing' AND OLD.status = 'pending'
BEGIN
    UPDATE commands SET started_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- 명령 완료/에러 시 completed_at 자동 설정
CREATE TRIGGER set_command_completed_at
AFTER UPDATE ON commands
FOR EACH ROW
WHEN NEW.status IN ('completed', 'error') AND OLD.status != NEW.status
BEGIN
    UPDATE commands SET completed_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- ==================== 초기 데이터 ====================

INSERT INTO seat_layout (room_name, rows, cols, description) VALUES
('1실습실', 6, 8, '소프트웨어학과 실습실 1'),
('2실습실', 6, 8, '소프트웨어학과 실습실 2');

-- ==================== DB 설정 ====================

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;
PRAGMA auto_vacuum = INCREMENTAL;
PRAGMA cache_size = 2000;
PRAGMA synchronous = NORMAL;