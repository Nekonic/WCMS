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


def find_duplicates_by_identity(db):
    """IP, MAC, hostname이 모두 같지만 machine_id가 다른 PC 찾기 (실질적 중복)"""
    duplicates = []

    # IP + MAC + hostname 조합으로 그룹화
    cursor = db.execute('''
        SELECT ip_address, mac_address, hostname, COUNT(*) as cnt
        FROM pc_info
        WHERE ip_address IS NOT NULL AND mac_address IS NOT NULL AND hostname IS NOT NULL
        GROUP BY ip_address, mac_address, hostname
        HAVING cnt > 1
    ''')

    identity_dups = cursor.fetchall()

    for dup in identity_dups:
        pcs = db.execute('''
            SELECT id, machine_id, hostname, ip_address, mac_address, created_at, last_seen, is_online
            FROM pc_info
            WHERE ip_address = ? AND mac_address = ? AND hostname = ?
            ORDER BY last_seen DESC, created_at DESC
        ''', (dup['ip_address'], dup['mac_address'], dup['hostname'])).fetchall()

        # machine_id가 다른지 확인
        machine_ids = set(pc['machine_id'] for pc in pcs if pc['machine_id'])
        if len(machine_ids) > 1:
            duplicates.append({
                'ip': dup['ip_address'],
                'mac': dup['mac_address'],
                'hostname': dup['hostname'],
                'pcs': pcs
            })

    return duplicates


def find_duplicates_by_hostname(db):
    """hostname만 중복된 PC 찾기 (참고용)"""
    cursor = db.execute('''
        SELECT hostname, COUNT(*) as cnt
        FROM pc_info
        WHERE hostname IS NOT NULL AND hostname != ''
        GROUP BY hostname
        HAVING cnt > 1
    ''')

    duplicates = cursor.fetchall()

    # IP나 MAC이 다른지 확인 (실제로 다른 PC일 가능성)
    real_duplicates = []
    for dup in duplicates:
        pcs = db.execute('''
            SELECT id, machine_id, hostname, ip_address, mac_address, created_at, last_seen
            FROM pc_info
            WHERE hostname = ?
        ''', (dup['hostname'],)).fetchall()

        # IP 또는 MAC이 다르면 실제로 다른 PC
        ips = set(pc['ip_address'] for pc in pcs if pc['ip_address'])
        macs = set(pc['mac_address'] for pc in pcs if pc['mac_address'])

        if len(ips) > 1 or len(macs) > 1:
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


def clean_identity_duplicates(db):
    """실질적 중복 처리 (IP+MAC+hostname 같지만 machine_id 다름)"""
    duplicates = find_duplicates_by_identity(db)

    if not duplicates:
        print("✅ 실질적 중복 없음 (IP+MAC+hostname 같은 경우)")
        return 0

    print(f"\n⚠️  실질적 중복 발견 (같은 PC인데 machine_id만 다름): {len(duplicates)}개")
    print("=" * 80)

    total_deleted = 0

    for dup_group in duplicates:
        pcs = dup_group['pcs']

        print(f"\n📌 {dup_group['hostname']} (IP: {dup_group['ip']}, MAC: {dup_group['mac']})")
        print("   이 PC들은 IP, MAC, hostname이 모두 같습니다. (실질적으로 같은 PC)")
        print()

        for i, pc in enumerate(pcs, 1):
            status = "✅ 유지" if i == 1 else "❌ 삭제 대상"
            print(f"   [{i}] {status}")
            print(f"       ID={pc['id']}, machine_id={pc['machine_id']}")
            print(f"       생성: {pc['created_at']}, 최종 접속: {pc['last_seen']}")
            print(f"       상태: {'온라인' if pc['is_online'] else '오프라인'}")

        print()
        answer = input(f"   최신 PC(ID={pcs[0]['id']})만 남기고 나머지 {len(pcs)-1}개를 삭제하시겠습니까? (yes/no): ").strip().lower()

        if answer in ('yes', 'y'):
            # 첫 번째(최신) PC만 유지하고 나머지 삭제
            for pc in pcs[1:]:
                db.execute('DELETE FROM pc_status WHERE pc_id = ?', (pc['id'],))
                db.execute('DELETE FROM pc_specs WHERE pc_id = ?', (pc['id'],))
                db.execute('DELETE FROM pc_command WHERE pc_id = ?', (pc['id'],))
                db.execute('DELETE FROM seat_map WHERE pc_id = ?', (pc['id'],))
                db.execute('DELETE FROM pc_info WHERE id = ?', (pc['id'],))
                print(f"   ✅ 삭제 완료: ID={pc['id']}")
                total_deleted += 1

            db.commit()
        else:
            print("   ⏭️  건너뜀")

    if total_deleted > 0:
        print(f"\n✅ 실질적 중복 정리 완료: {total_deleted}개 PC 삭제됨")

    return total_deleted


def clean_hostname_duplicates(db):
    """hostname만 중복 처리 (IP/MAC 다름 - 실제로 다른 PC)"""
    duplicates = find_duplicates_by_hostname(db)

    if not duplicates:
        print("✅ hostname만 중복된 경우 없음 (실제로 다른 PC)")
        return 0

    print(f"\n📋 참고: hostname은 같지만 IP/MAC이 다른 PC: {len(duplicates)}개")
    print("=" * 80)

    for hostname, pcs in duplicates:
        print(f"\n📌 hostname: {hostname}")
        for i, pc in enumerate(pcs, 1):
            print(f"   [{i}] ID={pc['id']}, machine_id={pc['machine_id']}")
            print(f"       IP={pc['ip_address']}, MAC={pc['mac_address']}")
            print(f"       최종 접속: {pc['last_seen']}")

        print("   ℹ️  이 PC들은 IP 또는 MAC이 다르므로 실제로 다른 PC입니다.")
        print("   ℹ️  hostname이 같은 것은 정상일 수 있습니다 (예: 이미지 복제 등)")

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

    # 중복 검사
    machine_id_dups = find_duplicates_by_machine_id(db)
    identity_dups = find_duplicates_by_identity(db)
    hostname_dups = find_duplicates_by_hostname(db)

    if not machine_id_dups and not identity_dups and not hostname_dups:
        print("\n✅ 중복된 PC가 없습니다!")
        db.close()
        return

    print(f"\n발견된 중복:")
    print(f"  - machine_id 중복: {len(machine_id_dups)}개")
    print(f"  - 실질적 중복 (IP+MAC+hostname 같음): {len(identity_dups)}개")
    print(f"  - hostname만 중복 (IP/MAC 다름): {len(hostname_dups)}개")

    # 사용자 확인
    print("\n⚠️  경고: 이 작업은 데이터를 삭제합니다!")
    print("   - machine_id가 같은 PC는 최신 것만 남기고 자동 삭제됩니다.")
    print("   - IP+MAC+hostname이 같은 PC는 사용자 확인 후 삭제됩니다.")
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

    deleted_count = 0

    # 1. machine_id 중복 정리 (자동)
    deleted_count += clean_machine_id_duplicates(db)

    # 2. 실질적 중복 정리 (사용자 확인)
    deleted_count += clean_identity_duplicates(db)

    # 3. hostname만 중복 (참고만)
    clean_hostname_duplicates(db)

    # 최종 상태
    show_database_status(db)

    print("\n" + "=" * 80)
    print(f"✅ 정리 완료! 총 {deleted_count}개의 중복 PC가 삭제되었습니다.")
    print("=" * 80)

    db.close()


if __name__ == '__main__':
    main()

