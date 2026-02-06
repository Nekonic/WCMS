#!/bin/bash
set -e

echo "[WCMS] 서버 시작 준비..."

# DB 파일 경로 확인 (환경변수 또는 기본값)
DB_PATH="${WCMS_DB_PATH:-/app/server/db.sqlite3}"
DB_DIR=$(dirname "$DB_PATH")

# DB 디렉토리 생성
mkdir -p "$DB_DIR"

# DB 파일 확인 및 초기화
if [ ! -f "$DB_PATH" ]; then
    echo "[WCMS] DB 파일 없음 - 초기화 중..."
    python /app/manage.py init-db --force
    echo "[WCMS] DB 초기화 완료"
else
    # 테이블 개수 확인
    TABLE_COUNT=$(sqlite3 "$DB_PATH" "SELECT count(*) FROM sqlite_master WHERE type='table';" 2>/dev/null || echo "0")
    if [ "$TABLE_COUNT" = "0" ]; then
        echo "[WCMS] DB 비어있음 - 초기화 중..."
        python /app/manage.py init-db --force
        echo "[WCMS] DB 초기화 완료"
    else
        echo "[WCMS] 기존 DB 사용 ($TABLE_COUNT 테이블)"
    fi
fi

echo "[WCMS] 서버 시작..."
exec "$@"
