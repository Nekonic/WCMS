#!/bin/bash

# WCMS 서버 초기 설정 스크립트
# 사용법: bash setup.sh [실습실_개수]
# 예시: bash setup.sh 6  (6개 실습실 생성)

DB_PATH="db.sqlite3"
SCHEMA_PATH="migrations/schema.sql"
NUM_ROOMS=${1:-4}  # 기본값: 4개 실습실

echo "========================================="
echo "WCMS 서버 초기 설정 스크립트"
echo "========================================="

# Python3 확인
if ! command -v python3 &> /dev/null; then
    echo "[✗] python3가 설치되어 있지 않습니다."
    echo "    Ubuntu/Debian: sudo apt install python3 python3-pip"
    echo "    CentOS/RHEL: sudo yum install python3 python3-pip"
    exit 1
fi

echo "[✓] Python3 확인 완료"

# pip3 확인
if ! command -v pip3 &> /dev/null; then
    echo "[✗] pip3가 설치되어 있지 않습니다."
    exit 1
fi

echo "[✓] pip3 확인 완료"

# 의존성 설치
echo ""
echo "[*] Python 패키지 설치 중..."
if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt -q
    if [ $? -eq 0 ]; then
        echo "[✓] 패키지 설치 완료"
    else
        echo "[✗] 패키지 설치 실패"
        exit 1
    fi
else
    echo "[✗] requirements.txt 파일이 없습니다."
    exit 1
fi

# 기존 DB 삭제
echo ""
if [ -f "$DB_PATH" ]; then
    read -p "기존 데이터베이스를 삭제하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm "$DB_PATH"
        echo "[✓] 기존 $DB_PATH 파일 삭제 완료."
    else
        echo "[!] 기존 데이터베이스를 유지합니다."
        echo "[!] 초기화를 원하시면 수동으로 삭제하세요: rm $DB_PATH"
        exit 0
    fi
fi

# schema.sql로 새 DB 생성
echo ""
echo "[*] 데이터베이스 생성 중..."
if [ -f "$SCHEMA_PATH" ]; then
    sqlite3 "$DB_PATH" < "$SCHEMA_PATH"
    echo "[✓] $SCHEMA_PATH 기반으로 $DB_PATH 생성 완료."
else
    echo "[✗] 스키마 파일($SCHEMA_PATH)이 존재하지 않습니다."
    exit 1
fi

# create_admin.py로 관리자 계정 생성
echo ""
echo "[*] 관리자 계정 생성 중..."
python3 create_admin.py admin admin123

# create_seats.py로 기본 좌석 배치 생성
echo ""
echo "[*] 좌석 배치 생성 중 (${NUM_ROOMS}개 실습실)..."
python3 create_seats.py $NUM_ROOMS

echo ""
echo "========================================="
echo "✅ WCMS 서버 초기 설정 완료!"
echo "========================================="
echo ""
echo "📊 설정 정보:"
echo "  - 데이터베이스: $DB_PATH"
echo "  - 관리자 계정: admin / admin123"
echo "  - 실습실 개수: ${NUM_ROOMS}개 (1실습실 ~ ${NUM_ROOMS}실습실)"
echo ""
echo "🚀 서버 시작:"
echo "  python3 app.py"
echo ""
echo "🌐 웹 접속:"
echo "  http://localhost:5050"
echo "  http://[서버_IP]:5050"
echo ""
echo "⚠️  보안 경고:"
echo "  반드시 로그인 후 관리자 비밀번호를 변경하세요!"
echo "========================================="





