# WCMS
Woosuk Computer Management System

## 📋 문서

- [API 명세서](API.md) - 전체 API 엔드포인트 상세 설명
- [개발 가이드](DEVELOP.md) - 프로젝트 구조 및 개발 방법
- [테스트 가이드](TESTING.md) - 테스트 실행 방법 및 문제 해결
- [프로젝트 상태](STATUS.md) - 개발 진행 상황

## 🧪 빠른 테스트

```bash
# 0. 의존성 설치 (최초 1회)
pip install -r server/requirements.txt
pip install -r client/requirements.txt

# 1. 데이터베이스 초기화 (스키마 변경 후 필요)
cd server
./init_db.sh

# 1-1. 관리자 계정 생성 (admin/admin)
python create_admin.py

# 2. 서버 시작
python app.py

# 3. 새 터미널에서 서버 API 테스트 실행
cd server
python test_web_access.py

# 4. 클라이언트 테스트 실행 (선택)
cd ../client
python test_client.py

# 5. 통합 테스트 실행 (선택)
cd ..
python test_integration.py
```

자세한 테스트 방법은 [TESTING.md](TESTING.md)를 참고하세요.

---

## Server

### 프로젝트 구조

```
server/
├── app.py
├── create_admin.py       # 관리자 계정 생성 유틸
├── init_db.sh            # DB 초기화 스크립트 (migrations/schema.sql 적용)
├── migrations/
│   └── schema.sql
├── templates/
│   ├── base.html           # 공통 레이아웃 + 모달
│   ├── index.html          # PC 카드 목록
│   ├── layout_editor.html  # 좌석 배치 편집기
│   ├── pc_detail.html      # PC 상세정보 (모달 템플릿)
│   └── login.html          # 로그인 페이지
├── test_web_access.py
├── requirements.txt
└── db.sqlite3
```

### Dependencies (Server)
| package         | used for                      |
|-----------------|-------------------------------|
| Flask           | web framework                 |
| flask_cors      | CORS                          |
| flask_socketio  | 실시간 통신 (향후 확장)      |
| flask_session   | 세션 관리 (향후 확장)        |
| requests        | 테스트 스크립트 내 HTTP 호출 |
| bcrypt          | 비밀번호 해시                 |

환경 변수:
- `WCMS_BASE_URL`: 테스트 스크립트 기본 서버 URL 오버라이드 (기본: http://127.0.0.1:5050)

---

## Client

```
[클라이언트 PC]
  ↓ (10분마다)
  1. 시스템 정보 수집
  2. POST /api/client/heartbeat
  ↓
[Flask 서버]
  ↓ (DB 저장)
  
[관리자 → 서버 → 클라이언트]
  1. 관리자: 원격 명령 (종료, 재시작, 계정 생성 등) 전송
  2. 서버: 명령 큐에 저장
  3. 클라이언트: GET /api/client/command (30초마다 폴링)
  4. 클라이언트: 명령 실행
  5. 클라이언트: POST /api/client/command/result
```

### 프로젝트 구조
```
client/
├── main.py            # 메인 실행 파일
├── collector.py       # 시스템 정보 수집
├── executor.py        # 명령 실행 (종료/재시작/CMD/계정 관리)
├── test_client.py     # 클라이언트 기능 테스트
├── requirements.txt
└── build.spec         # PyInstaller 설정
```

### Dependencies (Client)
| package     | used for                                        |
|-------------|--------------------------------------------------|
| psutil      | 시스템/프로세스/디스크/메모리 정보 수집          |
| requests    | 서버 HTTP API 통신                              |
| wmi         | (Windows) 시스템 정보                             |
| pywin32     | (Windows) WinAPI (계정 관리 등)                  |
| pyinstaller | (선택) 배포용 실행파일 빌드                      |

환경 변수:
- `WCMS_SERVER_URL`: 클라이언트가 접속할 서버 URL (기본: http://127.0.0.1:5050/)

---

### 좌석 배치 예시

| PC | PC | PC | PC | 복도 | PC | PC | PC | PC |
|----|----|----|----|------|----|----|----|----|
| PC | PC | PC | PC |      | PC | PC | PC | PC |
| PC | PC | PC | PC |      | PC | PC | PC | PC |
| PC | PC | PC | PC |      | PC | PC | PC | PC |
| PC | PC | PC | PC |      | PC | PC | PC | PC |
| PC | PC | PC | PC |      | PC | PC | PC | PC |
