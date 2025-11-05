# WCMS
Woosuk Computer Management System

## Server

### 프로젝트 구조

```
server/
├── app.py
├── migrations/
│   └── schema.sql
├── templates/
│   ├── base.html
│   ├── index.html
│   └── ...
└── db.sqlite3
```
### dependancy
| package | used for | 
| --- | --- |
| flask | web framework |
| bcrypt | password hashing |

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
  1. 관리자: 종료 버튼 클릭
  2. 서버: 명령 큐에 저장
  3. 클라이언트: GET /api/client/command (5초마다 폴링)
  4. 클라이언트: 명령 실행
  5. 클라이언트: POST /api/client/command/result
```
### 프로젝트 구조
```
client/
├── config.py           # 설정 (서버 URL, 기기 정보)
├── main.py            # 메인 실행 파일
├── collector.py       # 시스템 정보 수집
├── api.py             # 서버 통신
├── executor.py        # 명령 실행 (종료/재시작/CMD)
├── requirements.txt
└── build.spec         # PyInstaller 설정
```
### dependancy
| package | used for | 
| --- | --- |
| wmi | get system info |
| psutil | get process info |
| pywin32 | background |
| requests | server api |
| pyinstaller | build exe |

| PC | PC | PC | PC | 복도 | PC | PC | PC | PC |
|----|----|----|----|----|----|----|----|----|
| PC | PC | PC | PC |    | PC | PC | PC | PC |
| PC | PC | PC | PC |    | PC | PC | PC | PC |
| PC | PC | PC | PC |    | PC | PC | PC | PC |
| PC | PC | PC | PC |    | PC | PC | PC | PC |
| PC | PC | PC | PC |    | PC | PC | PC | PC |
