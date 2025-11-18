# WCMS
Woosuk Computer Management System

# WCMS
Woosuk Computer Management System

> 실습실 PC를 원격으로 모니터링하고 제어하는 웹 기반 관리 시스템

## 📚 문서

- **[통합 가이드](GUIDE.md)** ⭐ - 설치, 사용법, API, 문제 해결 (권장)
- [프로젝트 상태](STATUS.md) - 개발 진행 상황 및 로드맵

## ✨ 주요 기능

### 원격 제어
- ✅ CMD 명령 실행, 프로그램 설치, 파일 다운로드
- ✅ Windows 계정 관리, 전원 관리

### 일괄 명령
- ✅ 드래그로 여러 PC 선택
- ✅ 선택된 모든 PC에 동시에 명령 전송

### 모니터링
- ✅ 실시간 CPU/RAM/디스크 사용률
- ✅ 프로세스 추적, 좌석 배치 관리

## 🚀 빠른 시작

```bash
# 1. 의존성 설치
pip install -r server/requirements.txt
pip install -r client/requirements.txt

# 2. 서버 설정
cd server
./init_db.sh              # DB 초기화
python create_admin.py    # 관리자 생성 (admin/admin)
python app.py             # 서버 시작

# 3. 클라이언트 실행 (Windows PC)
cd client
python main.py

# 4. 웹 접속
# http://127.0.0.1:5050
```

## 🧪 테스트

```bash
# 통합 테스트 (모든 테스트 실행)
python test_all.py

# 옵션
python test_all.py --server    # 서버 API만
python test_all.py --client    # 클라이언트만
python test_all.py --bulk      # 일괄 명령만
```

자세한 내용은 [GUIDE.md](GUIDE.md)를 참고하세요.

## 📊 프로젝트 진행률

**전체: 88%**

```
Phase 1 (서버):     ████████████████████ 100%
Phase 2 (클라이언트): ████████████████████ 100%
Phase 3 (제어):     ██████████████████░░  90%
Phase 4 (문서화):   ███████████████████░  95%
Phase 5 (배포):     ███░░░░░░░░░░░░░░░░░  15%
```

자세한 진행 상황은 [STATUS.md](STATUS.md) 참조

## 📁 프로젝트 구조

```
WCMS/
├── server/              # Flask 서버
│   ├── app.py          # 메인 애플리케이션
│   ├── templates/      # HTML 템플릿
│   └── migrations/     # DB 스키마
├── client/             # 클라이언트 프로그램
│   ├── main.py        # 메인 실행 파일
│   ├── collector.py   # 시스템 정보 수집
│   └── executor.py    # 명령 실행
├── test_all.py        # 통합 테스트 ⭐
├── GUIDE.md           # 통합 가이드 ⭐
└── STATUS.md          # 프로젝트 상태
```

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
