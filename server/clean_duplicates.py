#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
중복 PC 데이터 정리 스크립트
- machine_id가 같은 PC는 최신 것만 남기고 삭제
- hostname만 같은 PC는 사용자에게 확인 후 처리
"""

import sqlite3
import os
import sys
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'db.sqlite3')


def get_db():
    """데이터베이스 연결"""
    if not os.path.exists(DB_PATH):
        print(f"❌ 데이터베이스를 찾을 수 없습니다: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def find_duplicates_by_machine_id(db):
    """machine_id가 중복된 PC 찾기"""
    cursor = db.execute('''
        SELECT machine_id, COUNT(*) as cnt
        FROM pc_info
        WHERE machine_id IS NOT NULL AND machine_id != ''
        GROUP BY machine_id
        HAVING cnt > 1
    ''')

    duplicates = cursor.fetchall()
    return duplicates


def find_duplicates_by_hostname(db):
    """hostname이 중복된 PC 찾기 (machine_id는 다른 경우)"""
    cursor = db.execute('''
        SELECT hostname, COUNT(*) as cnt
        FROM pc_info
        WHERE hostname IS NOT NULL AND hostname != ''
        GROUP BY hostname
        HAVING cnt > 1
    ''')

    duplicates = cursor.fetchall()

    # machine_id가 모두 다른지 확인
    real_duplicates = []
    for dup in duplicates:
        pcs = db.execute('''
            SELECT id, machine_id, hostname, created_at, last_seen
            FROM pc_info
            WHERE hostname = ?
        ''', (dup['hostname'],)).fetchall()

        machine_ids = set(pc['machine_id'] for pc in pcs if pc['machine_id'])
        if len(machine_ids) > 1:
            real_duplicates.append((dup['hostname'], pcs))

    return real_duplicates


def clean_machine_id_duplicates(db):
    """machine_id 중복 자동 정리 (최신 것만 유지)"""
    duplicates = find_duplicates_by_machine_id(db)

    if not duplicates:
        print("✅ machine_id 중복 없음")
        return 0

    print(f"\n⚠️  machine_id 중복 발견: {len(duplicates)}개")
    print("=" * 80)

    total_deleted = 0

    for dup in duplicates:
        machine_id = dup['machine_id']

        # 해당 machine_id를 가진 모든 PC 조회 (최신순)
        pcs = db.execute('''
            SELECT id, hostname, created_at, last_seen, is_online
            FROM pc_info
            WHERE machine_id = ?
            ORDER BY last_seen DESC, created_at DESC
        ''', (machine_id,)).fetchall()

        # 첫 번째(최신) PC는 유지
        keep_pc = pcs[0]
        delete_pcs = pcs[1:]

        print(f"\n📌 machine_id: {machine_id}")
        print(f"   ✅ 유지: ID={keep_pc['id']}, hostname={keep_pc['hostname']}, last_seen={keep_pc['last_seen']}")

        for pc in delete_pcs:
            print(f"   ❌ 삭제: ID={pc['id']}, hostname={pc['hostname']}, last_seen={pc['last_seen']}")

            # 관련 데이터 삭제
            db.execute('DELETE FROM pc_status WHERE pc_id = ?', (pc['id'],))
            db.execute('DELETE FROM pc_specs WHERE pc_id = ?', (pc['id'],))
            db.execute('DELETE FROM pc_command WHERE pc_id = ?', (pc['id'],))
            db.execute('DELETE FROM seat_map WHERE pc_id = ?', (pc['id'],))
            db.execute('DELETE FROM pc_info WHERE id = ?', (pc['id'],))

            total_deleted += 1

    db.commit()
    print(f"\n✅ machine_id 중복 정리 완료: {total_deleted}개 PC 삭제됨")
    return total_deleted


def clean_hostname_duplicates(db):
    """hostname 중복 처리 (사용자 확인 필요)"""
    duplicates = find_duplicates_by_hostname(db)

    if not duplicates:
        print("✅ hostname 중복 없음 (machine_id 다른 경우)")
        return 0

    print(f"\n⚠️  hostname 중복 발견 (machine_id는 다름): {len(duplicates)}개")
    print("=" * 80)

    for hostname, pcs in duplicates:
        print(f"\n📌 hostname: {hostname}")
        for i, pc in enumerate(pcs, 1):
            print(f"   [{i}] ID={pc['id']}, machine_id={pc['machine_id']}, created_at={pc['created_at']}, last_seen={pc['last_seen']}")

        print("   ⚠️  이 PC들은 machine_id가 다르므로 별도 PC입니다.")
        print("   ⚠️  필요시 수동으로 확인 후 삭제하세요.")

    return 0


def show_database_status(db):
    """데이터베이스 상태 표시"""
    total_pcs = db.execute('SELECT COUNT(*) as cnt FROM pc_info').fetchone()['cnt']
    online_pcs = db.execute('SELECT COUNT(*) as cnt FROM pc_info WHERE is_online = 1').fetchone()['cnt']

    print("\n" + "=" * 80)
    print("📊 데이터베이스 상태")
    print("=" * 80)
    print(f"전체 PC 수: {total_pcs}대")
    print(f"온라인 PC 수: {online_pcs}대")
    print(f"오프라인 PC 수: {total_pcs - online_pcs}대")


def main():
    """메인 함수"""
    print("=" * 80)
    print("🔧 WCMS 중복 PC 데이터 정리 도구")
    print("=" * 80)

    db = get_db()

    # 현재 상태 확인
    show_database_status(db)

    # machine_id 중복 확인
    machine_id_dups = find_duplicates_by_machine_id(db)
    hostname_dups = find_duplicates_by_hostname(db)

    if not machine_id_dups and not hostname_dups:
        print("\n✅ 중복된 PC가 없습니다!")
        db.close()
        return

    print(f"\n발견된 중복:")
    print(f"  - machine_id 중복: {len(machine_id_dups)}개")
    print(f"  - hostname 중복 (machine_id 다름): {len(hostname_dups)}개")

    # 사용자 확인
    print("\n⚠️  경고: 이 작업은 데이터를 삭제합니다!")
    print("   - machine_id가 같은 PC는 최신 것만 남기고 자동 삭제됩니다.")
    print("   - hostname만 같은 PC는 확인만 하고 삭제하지 않습니다.")

    answer = input("\n계속하시겠습니까? (yes/no): ").strip().lower()

    if answer not in ('yes', 'y'):
        print("❌ 작업이 취소되었습니다.")
        db.close()
        return

    # 백업 권장
    print("\n💡 백업을 먼저 생성하는 것을 권장합니다.")
    backup_answer = input("백업을 생성하시겠습니까? (yes/no): ").strip().lower()

    if backup_answer in ('yes', 'y'):
        backup_path = f"{DB_PATH}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        import shutil
        shutil.copy2(DB_PATH, backup_path)
        print(f"✅ 백업 생성됨: {backup_path}")

    # 정리 시작
    print("\n" + "=" * 80)
    print("🧹 중복 정리 시작")
    print("=" * 80)

    deleted_count = clean_machine_id_duplicates(db)
    clean_hostname_duplicates(db)

    # 최종 상태
    show_database_status(db)

    print("\n" + "=" * 80)
    print(f"✅ 정리 완료! 총 {deleted_count}개의 중복 PC가 삭제되었습니다.")
    print("=" * 80)

    db.close()


if __name__ == '__main__':
    main()

