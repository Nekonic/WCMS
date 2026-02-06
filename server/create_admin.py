#!/usr/bin/env python3
"""
WCMS 관리자 계정 생성 스크립트
"""

import sqlite3
import bcrypt
import os

# 환경변수 또는 기본 경로 사용
DB_PATH = os.getenv('WCMS_DB_PATH', os.path.join(os.path.dirname(__file__), 'db.sqlite3'))

def create_admin(username='admin', password='admin'):
    """관리자 계정 생성"""
    # 비밀번호 해시 생성
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    # 데이터베이스 연결
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # 기존 admin 계정 확인
        cursor.execute('SELECT id FROM admins WHERE username=?', (username,))
        existing = cursor.fetchone()

        if existing:
            print(f"⚠️  '{username}' 계정이 이미 존재합니다. 비밀번호를 업데이트합니다...")
            cursor.execute('UPDATE admins SET password_hash=? WHERE username=?', (password_hash, username))
            print(f"✅ '{username}' 계정 비밀번호가 업데이트되었습니다.")
        else:
            # 새 관리자 계정 생성
            cursor.execute('''
                INSERT INTO admins (username, password_hash, is_active)
                VALUES (?, ?, 1)
            ''', (username, password_hash))
            print(f"✅ '{username}' 계정이 생성되었습니다.")

        conn.commit()
        print(f"\n계정 정보:")
        print(f"  - 사용자명: {username}")
        print(f"  - 비밀번호: {password}")
        print(f"\n⚠️  프로덕션 환경에서는 반드시 비밀번호를 변경하세요!")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    import sys

    if len(sys.argv) == 3:
        username = sys.argv[1]
        password = sys.argv[2]
        create_admin(username, password)
    else:
        print("관리자 계정 생성 중...")
        create_admin('admin', 'admin')

