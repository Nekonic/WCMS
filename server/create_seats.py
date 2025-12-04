#!/usr/bin/env python3
"""
WCMS 기본 좌석 배치 생성 스크립트

사용법:
    python3 create_seats.py           # 기본: 1~4실습실 생성
    python3 create_seats.py 6         # 1~6실습실 생성
    python3 create_seats.py 10        # 1~10실습실 생성
"""

import sqlite3
import os
import sys

DB_PATH = os.path.join(os.path.dirname(__file__), 'db.sqlite3')

def create_default_seats(num_rooms=4):
    """기본 좌석 배치 생성

    Args:
        num_rooms: 생성할 실습실 개수 (기본: 4)
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # 1~num_rooms 실습실 좌석 배치 생성
        for room_num in range(1, num_rooms + 1):
            room_name = f"{room_num}실습실"

            # seat_layout에 실습실 추가
            cursor.execute('''
                INSERT OR IGNORE INTO seat_layout (room_name, rows, cols, is_active)
                VALUES (?, 6, 8, 1)
            ''', (room_name,))

            print(f"[✓] {room_name} 좌석 배치 생성 (6행 x 8열)")

        conn.commit()
        print(f"\n✅ 총 {num_rooms}개 실습실 좌석 배치가 생성되었습니다.")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    # 명령줄 인자로 실습실 개수 지정 가능
    if len(sys.argv) > 1:
        try:
            num_rooms = int(sys.argv[1])
            if num_rooms < 1:
                print("❌ 실습실 개수는 1 이상이어야 합니다.")
                sys.exit(1)
            create_default_seats(num_rooms)
        except ValueError:
            print("❌ 올바른 숫자를 입력하세요.")
            print("사용법: python3 create_seats.py [실습실_개수]")
            sys.exit(1)
    else:
        # 기본값: 4개 실습실
        create_default_seats(4)

