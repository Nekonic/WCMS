/**
 * DB 초기화 스크립트
 * 사용법: npm run db:init [username] [password]
 */
import Database from 'better-sqlite3'
import { hashSync } from 'bcryptjs'

const dbPath = process.env.WCMS_DB_PATH ?? '../db/wcms.sqlite3'
const username = process.argv[2] ?? 'admin'
const password = process.argv[3] ?? 'admin'

const sqlite = new Database(dbPath)
sqlite.pragma('journal_mode = WAL')
sqlite.pragma('foreign_keys = ON')

sqlite.exec(`
  CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    email TEXT,
    is_active BOOLEAN DEFAULT 1,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
  CREATE TABLE IF NOT EXISTS pc_registration_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token TEXT UNIQUE NOT NULL,
    usage_type TEXT NOT NULL DEFAULT 'single',
    expires_in INTEGER NOT NULL DEFAULT 600,
    is_expired BOOLEAN DEFAULT 0,
    used_count INTEGER DEFAULT 0,
    created_by TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
  );
  CREATE TABLE IF NOT EXISTS pc_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    machine_id TEXT UNIQUE NOT NULL,
    hostname TEXT NOT NULL,
    mac_address TEXT NOT NULL,
    room_name TEXT,
    seat_number TEXT,
    ip_address TEXT,
    is_online BOOLEAN DEFAULT 0,
    last_seen TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_verified BOOLEAN DEFAULT 0,
    registered_with_token TEXT,
    verified_at TIMESTAMP
  );
  CREATE TABLE IF NOT EXISTS pc_specs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pc_id INTEGER UNIQUE NOT NULL,
    cpu_model TEXT NOT NULL,
    cpu_cores INTEGER NOT NULL,
    cpu_threads INTEGER NOT NULL,
    ram_total REAL NOT NULL,
    disk_info TEXT NOT NULL,
    os_edition TEXT NOT NULL,
    os_version TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pc_id) REFERENCES pc_info(id) ON DELETE CASCADE
  );
  CREATE TABLE IF NOT EXISTS pc_dynamic_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pc_id INTEGER UNIQUE NOT NULL,
    cpu_usage REAL NOT NULL,
    ram_used REAL NOT NULL,
    ram_usage_percent REAL NOT NULL,
    disk_usage TEXT,
    current_user TEXT,
    uptime INTEGER NOT NULL,
    processes TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pc_id) REFERENCES pc_info(id) ON DELETE CASCADE
  );
  CREATE TABLE IF NOT EXISTS commands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pc_id INTEGER NOT NULL,
    admin_username TEXT,
    command_type TEXT NOT NULL,
    command_data TEXT,
    priority INTEGER DEFAULT 5,
    status TEXT DEFAULT 'pending',
    result TEXT,
    error_message TEXT,
    timeout_seconds INTEGER DEFAULT 300,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (pc_id) REFERENCES pc_info(id) ON DELETE CASCADE
  );
  CREATE TABLE IF NOT EXISTS seat_layout (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_name TEXT UNIQUE NOT NULL,
    rows INTEGER NOT NULL DEFAULT 6,
    cols INTEGER NOT NULL DEFAULT 8,
    description TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
  CREATE TABLE IF NOT EXISTS seat_map (
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
  CREATE TABLE IF NOT EXISTS network_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pc_id INTEGER NOT NULL,
    offline_at TIMESTAMP NOT NULL,
    online_at TIMESTAMP,
    duration_sec INTEGER,
    reason TEXT NOT NULL DEFAULT 'unknown',
    FOREIGN KEY (pc_id) REFERENCES pc_info(id) ON DELETE CASCADE
  );
  CREATE TABLE IF NOT EXISTS client_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version TEXT NOT NULL,
    download_url TEXT,
    changelog TEXT,
    released_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
`)

// 관리자 계정 (없으면 생성)
const existing = sqlite.prepare('SELECT id FROM admins WHERE username = ?').get(username)
if (!existing) {
  sqlite.prepare(
    'INSERT INTO admins (username, password_hash, is_active) VALUES (?, ?, 1)'
  ).run(username, hashSync(password, 10))
  console.log(`[ok] 관리자 계정 생성: ${username}`)
} else {
  console.log(`[skip] 관리자 계정 이미 존재: ${username}`)
}

console.log(`[ok] DB 초기화 완료: ${dbPath}`)
sqlite.close()