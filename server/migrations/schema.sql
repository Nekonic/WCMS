-- ==================== WCMS 최적화된 데이터베이스 스키마 ====================
-- 버전: 2.0
-- 최적화 목표: 정적/동적 데이터 분리, 디스크 사용량 70% 감소, 쿼리 성능 향상

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

-- ==================== PC 기본 정보 ====================
CREATE TABLE pc_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    machine_id TEXT UNIQUE NOT NULL,
    hostname TEXT NOT NULL,
    mac_address TEXT NOT NULL,
    room_name TEXT,
    seat_number TEXT,  -- "3, 2" 형식
    ip_address TEXT,
    is_online BOOLEAN DEFAULT 0,
    last_seen TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_pc_info_machine_id ON pc_info(machine_id);
CREATE INDEX idx_pc_info_room ON pc_info(room_name, is_online);
CREATE INDEX idx_pc_info_online ON pc_info(is_online, last_seen DESC);

-- ==================== PC 하드웨어 스펙 (정적 정보) ====================
-- 거의 변하지 않는 정보 - 1회만 저장
CREATE TABLE pc_specs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pc_id INTEGER UNIQUE NOT NULL,
    cpu_model TEXT NOT NULL,
    cpu_cores INTEGER NOT NULL,
    cpu_threads INTEGER NOT NULL,
    ram_total REAL NOT NULL,  -- GB 단위 (소수점)
    disk_info TEXT NOT NULL,     -- JSON: {"C:\\": {"total_gb": 237.0, "fstype": "NTFS", "mountpoint": "C:\\"}}
    os_edition TEXT NOT NULL,
    os_version TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pc_id) REFERENCES pc_info(id) ON DELETE CASCADE
);

CREATE INDEX idx_pc_specs_pc_id ON pc_specs(pc_id);

-- ==================== PC 동적 상태 (자주 변하는 정보만) ====================
-- 10분마다 수집되는 정보
CREATE TABLE pc_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pc_id INTEGER NOT NULL,
    cpu_usage REAL NOT NULL,         -- 0.0 ~ 100.0
    ram_used REAL NOT NULL,          -- GB 단위 (소수점)
    ram_usage_percent REAL NOT NULL, -- 0.0 ~ 100.0
    disk_usage TEXT,                 -- JSON: {"C:\\": {"used_gb": 107.2, "free_gb": 129.9, "percent": 45.2}}
    current_user TEXT,
    uptime INTEGER NOT NULL,         -- 초 단위
    processes TEXT,                  -- JSON: ["chrome.exe", "Code.exe"]
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pc_id) REFERENCES pc_info(id) ON DELETE CASCADE
);

-- 파티셔닝 대신 인덱스로 최적화
CREATE INDEX idx_pc_status_pc_id_time ON pc_status(pc_id, created_at DESC);
CREATE INDEX idx_pc_status_created_at ON pc_status(created_at DESC);

-- 오래된 데이터 자동 삭제 트리거 (옵션: 3개월 이상 데이터)
CREATE TRIGGER cleanup_old_status
AFTER INSERT ON pc_status
BEGIN
    DELETE FROM pc_status
    WHERE created_at < datetime('now', '-3 months');
END;

-- ==================== 명령 큐 (최적화) ====================
CREATE TABLE pc_command (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pc_id INTEGER NOT NULL,
    admin_username TEXT,             -- 명령을 내린 관리자
    command_type TEXT NOT NULL,      -- shutdown, reboot, create_user, etc.
    command_data TEXT,               -- JSON: 명령별 파라미터
    priority INTEGER DEFAULT 5,      -- 1(긴급) ~ 10(낮음)
    status TEXT DEFAULT 'pending',   -- pending, executing, completed, error, timeout
    result TEXT,                     -- 실행 결과 메시지
    error_message TEXT,              -- 에러 발생 시 상세 메시지
    retry_count INTEGER DEFAULT 0,   -- 재시도 횟수
    max_retries INTEGER DEFAULT 3,   -- 최대 재시도 횟수
    timeout_seconds INTEGER DEFAULT 300,  -- 타임아웃 (초)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,            -- 실행 시작 시각
    completed_at TIMESTAMP,          -- 완료 시각
    FOREIGN KEY (pc_id) REFERENCES pc_info(id) ON DELETE CASCADE
);

-- 복합 인덱스로 쿼리 최적화
CREATE INDEX idx_pc_command_pending ON pc_command(pc_id, status, priority DESC, created_at ASC)
    WHERE status = 'pending';
CREATE INDEX idx_pc_command_pc_status ON pc_command(pc_id, status, created_at DESC);
CREATE INDEX idx_pc_command_admin ON pc_command(admin_username, created_at DESC);

-- 완료된 명령 자동 아카이브 (30일 후)
CREATE TRIGGER archive_completed_commands
AFTER UPDATE ON pc_command
WHEN NEW.status IN ('completed', 'error')
BEGIN
    DELETE FROM pc_command
    WHERE id = NEW.id
    AND completed_at < datetime('now', '-30 days');
END;

-- ==================== 좌석 배치 ====================
CREATE TABLE seat_layout (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_name TEXT UNIQUE NOT NULL,
    rows INTEGER NOT NULL DEFAULT 6,
    cols INTEGER NOT NULL DEFAULT 8,
    description TEXT,                 -- 실습실 설명
    is_active BOOLEAN DEFAULT 1,      -- 사용 중인 레이아웃인지
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
    is_blocked BOOLEAN DEFAULT 0,     -- 막힌 좌석 (복도 등)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pc_id) REFERENCES pc_info(id) ON DELETE SET NULL,
    FOREIGN KEY (room_name) REFERENCES seat_layout(room_name) ON DELETE CASCADE,
    UNIQUE(room_name, row, col)
);

CREATE INDEX idx_seat_map_room ON seat_map(room_name);
CREATE INDEX idx_seat_map_pc ON seat_map(pc_id);

-- ==================== 관리자 활동 로그 ====================
CREATE TABLE admin_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_username TEXT NOT NULL,
    action TEXT NOT NULL,             -- login, logout, send_command, delete_user, etc.
    target_pc_id INTEGER,
    command_type TEXT,                -- shutdown, reboot, create_user, etc.
    details TEXT,                     -- JSON: 추가 정보
    ip_address TEXT,
    user_agent TEXT,
    success BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (target_pc_id) REFERENCES pc_info(id) ON DELETE SET NULL
);

-- 파티션 효과를 위한 복합 인덱스
CREATE INDEX idx_admin_logs_user_date ON admin_logs(admin_username, created_at DESC);
CREATE INDEX idx_admin_logs_action_date ON admin_logs(action, created_at DESC);
CREATE INDEX idx_admin_logs_pc_date ON admin_logs(target_pc_id, created_at DESC);

-- 오래된 로그 자동 삭제 (6개월)
CREATE TRIGGER cleanup_old_logs
AFTER INSERT ON admin_logs
BEGIN
    DELETE FROM admin_logs
    WHERE created_at < datetime('now', '-6 months');
END;

-- ==================== 트리거 (자동 업데이트) ====================

-- PC 정보 업데이트 시 updated_at 자동 갱신
CREATE TRIGGER update_pc_info_timestamp
AFTER UPDATE ON pc_info
FOR EACH ROW
BEGIN
    UPDATE pc_info SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- PC 스펙 업데이트 시 updated_at 자동 갱신
CREATE TRIGGER update_pc_specs_timestamp
AFTER UPDATE ON pc_specs
FOR EACH ROW
BEGIN
    UPDATE pc_specs SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- 좌석 배치 업데이트 시 updated_at 자동 갱신
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

-- PC 온라인 상태 자동 업데이트
CREATE TRIGGER update_pc_online_status
AFTER INSERT ON pc_status
FOR EACH ROW
BEGIN
    UPDATE pc_info
    SET is_online = 1,
        last_seen = CURRENT_TIMESTAMP,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.pc_id;
END;

-- 명령 실행 시작 시 started_at 자동 설정
CREATE TRIGGER set_command_started_at
AFTER UPDATE ON pc_command
FOR EACH ROW
WHEN NEW.status = 'executing' AND OLD.status = 'pending'
BEGIN
    UPDATE pc_command
    SET started_at = CURRENT_TIMESTAMP
    WHERE id = NEW.id;
END;

-- 명령 완료 시 completed_at 자동 설정
CREATE TRIGGER set_command_completed_at
AFTER UPDATE ON pc_command
FOR EACH ROW
WHEN NEW.status IN ('completed', 'error') AND OLD.status != NEW.status
BEGIN
    UPDATE pc_command
    SET completed_at = CURRENT_TIMESTAMP
    WHERE id = NEW.id;
END;

-- ==================== 뷰 (성능 최적화) ====================

-- 1. 경량 뷰: 대시보드용 (목록 조회)
CREATE VIEW v_pc_status_light AS
SELECT
    pi.id,
    pi.machine_id,
    pi.hostname,
    pi.room_name,
    pi.seat_number,
    pi.is_online,
    pi.last_seen,
    ps.cpu_usage,
    ps.ram_usage_percent,
    ps.current_user,
    ps.created_at as status_updated_at
FROM pc_info pi
LEFT JOIN (
    SELECT
        pc_id,
        cpu_usage,
        ram_usage_percent,
        current_user,
        created_at,
        ROW_NUMBER() OVER (PARTITION BY pc_id ORDER BY created_at DESC) as rn
    FROM pc_status
) ps ON pi.id = ps.pc_id AND ps.rn = 1;

-- 2. 전체 뷰: 상세 페이지용
CREATE VIEW v_pc_status_full AS
SELECT
    -- PC 기본 정보
    pi.id,
    pi.machine_id,
    pi.hostname,
    pi.mac_address,
    pi.room_name,
    pi.seat_number,
    pi.ip_address,
    pi.is_online,
    pi.last_seen,
    pi.created_at as pc_created_at,

    -- 하드웨어 스펙 (정적)
    specs.cpu_model,
    specs.cpu_cores,
    specs.cpu_threads,
    specs.ram_total,
    specs.disk_info,
    specs.os_edition,
    specs.os_version,

    -- 현재 상태 (동적)
    status.cpu_usage,
    status.ram_used,
    status.ram_usage_percent,
    status.disk_usage,
    status.current_user,
    status.uptime,
    status.processes,
    status.created_at as status_updated_at
FROM pc_info pi
LEFT JOIN pc_specs specs ON pi.id = specs.pc_id
LEFT JOIN (
    SELECT
        pc_id,
        cpu_usage, ram_used, ram_usage_percent,
        disk_usage, current_user, uptime, processes,
        created_at,
        ROW_NUMBER() OVER (PARTITION BY pc_id ORDER BY created_at DESC) as rn
    FROM pc_status
) status ON pi.id = status.pc_id AND status.rn = 1;

-- 3. 대기 중인 명령 뷰
CREATE VIEW v_pending_commands AS
SELECT
    c.id,
    c.pc_id,
    c.admin_username,
    c.command_type,
    c.command_data,
    c.priority,
    c.created_at,
    c.timeout_seconds,
    pi.hostname,
    pi.machine_id,
    pi.room_name,
    pi.is_online
FROM pc_command c
JOIN pc_info pi ON c.pc_id = pi.id
WHERE c.status = 'pending'
ORDER BY c.priority ASC, c.created_at ASC;

-- 4. 명령 실행 통계 뷰
CREATE VIEW v_command_stats AS
SELECT
    pc_id,
    COUNT(*) as total_commands,
    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
    SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as errors,
    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
    AVG(CASE
        WHEN completed_at IS NOT NULL AND started_at IS NOT NULL
        THEN (julianday(completed_at) - julianday(started_at)) * 86400
        ELSE NULL
    END) as avg_execution_time_seconds
FROM pc_command
GROUP BY pc_id;

-- 5. 실습실 현황 요약 뷰
CREATE VIEW v_room_summary AS
SELECT
    room_name,
    COUNT(*) as total_pcs,
    SUM(CASE WHEN is_online = 1 THEN 1 ELSE 0 END) as online_pcs,
    SUM(CASE WHEN is_online = 0 THEN 1 ELSE 0 END) as offline_pcs,
    ROUND(AVG(CASE WHEN is_online = 1 THEN cpu_usage ELSE NULL END), 2) as avg_cpu_usage,
    ROUND(AVG(CASE WHEN is_online = 1 THEN ram_usage_percent ELSE NULL END), 2) as avg_ram_usage
FROM v_pc_status_light
WHERE room_name IS NOT NULL
GROUP BY room_name;

-- ==================== 초기 데이터 ====================

-- 기본 실습실 레이아웃
INSERT INTO seat_layout (room_name, rows, cols, description) VALUES
('1실습실', 6, 8, '소프트웨어학과 실습실 1'),
('2실습실', 6, 8, '소프트웨어학과 실습실 2');

-- ==================== 데이터베이스 설정 ====================

-- WAL 모드 활성화 (동시성 향상)
PRAGMA journal_mode = WAL;

-- 외래 키 제약 조건 활성화
PRAGMA foreign_keys = ON;

-- 자동 VACUUM 활성화 (디스크 공간 자동 정리)
PRAGMA auto_vacuum = INCREMENTAL;

-- 캐시 크기 설정 (메모리 2000 페이지 = 약 8MB)
PRAGMA cache_size = 2000;

-- 동기화 모드 (성능/안정성 균형)
PRAGMA synchronous = NORMAL;

-- ==================== 유지보수 쿼리 ====================

-- 수동 VACUUM (필요시 실행)
-- VACUUM;

-- 통계 업데이트 (쿼리 플래너 최적화)
-- ANALYZE;

-- 인덱스 재구성
-- REINDEX;

-- ==================== 마이그레이션 가이드 ====================
/*
기존 데이터베이스에서 마이그레이션:

1. 백업
   cp db.sqlite3 db.sqlite3.backup

2. 데이터 추출
   sqlite3 db.sqlite3 ".dump pc_info" > pc_info_backup.sql
   sqlite3 db.sqlite3 ".dump pc_status" > pc_status_backup.sql

3. 새 스키마 적용
   sqlite3 db_new.sqlite3 < schema_v2.sql

4. 데이터 변환 및 임포트
   - pc_info: 그대로 임포트
   - pc_status: 첫 번째 레코드 → pc_specs, 나머지 → pc_status (정적 필드 제거)

5. 검증 후 교체
   mv db_new.sqlite3 db.sqlite3
*/