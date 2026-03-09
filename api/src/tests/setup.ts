import Database from 'better-sqlite3'
import { drizzle } from 'drizzle-orm/better-sqlite3'
import { hashSync } from 'bcryptjs'
import * as schema from '../db/schema.js'
import { sql } from 'drizzle-orm'

// 테스트마다 격리된 인메모리 DB 생성
export function createTestDb() {
  const sqlite = new Database(':memory:')
  sqlite.pragma('foreign_keys = ON')

  const db = drizzle(sqlite, { schema })

  // 스키마 생성
  sqlite.exec(`
    CREATE TABLE admins (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      username TEXT UNIQUE NOT NULL,
      password_hash TEXT NOT NULL,
      email TEXT,
      is_active BOOLEAN DEFAULT 1,
      last_login TIMESTAMP,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE pc_registration_tokens (
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
    CREATE TABLE pc_info (
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
    CREATE TABLE pc_specs (
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
    CREATE TABLE pc_dynamic_info (
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
    CREATE TABLE commands (
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
    CREATE TABLE network_events (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      pc_id INTEGER NOT NULL,
      offline_at TIMESTAMP NOT NULL,
      online_at TIMESTAMP,
      duration_sec INTEGER,
      reason TEXT NOT NULL DEFAULT 'unknown',
      FOREIGN KEY (pc_id) REFERENCES pc_info(id) ON DELETE CASCADE
    );
    CREATE TABLE client_versions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      version TEXT NOT NULL,
      download_url TEXT,
      changelog TEXT,
      released_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
  `)

  // 테스트 관리자 계정
  db.insert(schema.admins).values({
    username:     'admin',
    passwordHash: hashSync('password123', 10),
    isActive:     true,
  }).run()

  return { db, sqlite }
}

// 유효한 테스트 토큰 삽입
export function insertToken(db: ReturnType<typeof createTestDb>['db'], options?: {
  token?: string
  usageType?: 'single' | 'multi'
  expired?: boolean
}) {
  const token = options?.token ?? '123456'
  const expiresAt = options?.expired
    ? new Date(Date.now() - 1000).toISOString()  // 이미 만료
    : new Date(Date.now() + 600_000).toISOString()

  db.insert(schema.pcRegistrationTokens).values({
    token,
    usageType:  options?.usageType ?? 'single',
    expiresIn:  600,
    createdBy:  'admin',
    expiresAt,
  }).run()

  return token
}

// 테스트용 등록된 PC 삽입
export function insertPc(db: ReturnType<typeof createTestDb>['db'], machineId = 'test-machine-001') {
  const result = db.insert(schema.pcInfo).values({
    machineId,
    hostname:   'TEST-PC',
    macAddress: 'AA:BB:CC:DD:EE:FF',
    isVerified: true,
  }).returning({ id: schema.pcInfo.id }).get()
  return result.id
}