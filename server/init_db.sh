#!/bin/bash

DB_PATH="db.sqlite3"
SCHEMA_PATH="migrations/schema.sql"

# db.sqlite3 파일 삭제
if [ -f "$DB_PATH" ]; then
    rm "$DB_PATH"
    echo "기존 $DB_PATH 파일 삭제 완료."
fi

# schema.sql로 새 DB 생성
if [ -f "$SCHEMA_PATH" ]; then
    sqlite3 "$DB_PATH" < "$SCHEMA_PATH"
    echo "$SCHEMA_PATH 기반으로 $DB_PATH 생성 완료."
else
    echo "스키마 파일($SCHEMA_PATH)이 존재하지 않습니다."
    exit 1
fi
