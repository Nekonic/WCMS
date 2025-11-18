# WCMS 통합 가이드

> **최종 업데이트**: 2025.11.18  
> **버전**: 1.0  
> **프로젝트**: Woosuk Computer Management System

---

## 📚 목차

1. [프로젝트 개요](#프로젝트-개요)
2. [주요 기능](#주요-기능)
3. [빠른 시작](#빠른-시작)
4. [테스트 가이드](#테스트-가이드)
5. [API 명세](#api-명세)
6. [개발 가이드](#개발-가이드)
7. [문제 해결](#문제-해결)

---

## 프로젝트 개요

WCMS는 실습실 PC를 원격으로 관리하고 제어하는 웹 기반 시스템입니다.

### 시스템 구성

```
┌─────────────────┐
│   웹 브라우저    │ ← 관리자 접속
└────────┬────────┘
         │ HTTP
         ↓
┌─────────────────┐
│  Flask 서버     │ ← 중앙 관리 서버
│  (SQLite DB)    │
└────────┬────────┘
         │ REST API
         ↓
┌─────────────────┐
│ 클라이언트      │ ← Windows PC (여러 대)
│ (Python)        │
└─────────────────┘
```

### 기술 스택

- **서버**: Flask, SQLite
- **클라이언트**: Python, psutil, WMI
- **프론트엔드**: HTML, CSS, JavaScript
- **통신**: REST API, Long-polling

---

## 주요 기능

### ✨ 원격 제어
- ✅ **CMD 명령 실행**: 임의의 명령줄 명령 실행
- ✅ **프로그램 설치**: winget을 통한 자동 프로그램 설치
- ✅ **파일 다운로드**: URL에서 파일 다운로드
- ✅ **계정 관리**: Windows 계정 생성/삭제/비밀번호 변경
- ✅ **전원 관리**: 원격 종료/재시작/로그아웃

### 📊 일괄 명령
- ✅ **다중 PC 선택**: 드래그 또는 클릭으로 여러 PC 선택
- ✅ **체크박스 UI**: 선택된 PC를 시각적으로 확인
- ✅ **일괄 실행**: 선택된 모든 PC에 동시에 명령 전송
- ✅ **결과 추적**: 성공/실패 개수 즉시 확인

### 🖥️ 모니터링
- ✅ **실시간 상태**: CPU, RAM, 디스크 사용률
- ✅ **프로세스 추적**: 실행 중인 프로그램 모니터링
- ✅ **좌석 배치**: 실습실 레이아웃 관리
- ✅ **상태 표시**: 온라인/오프라인, 부하 상태 색상 구분

---

## 빠른 시작

### 1. 설치

```bash
# 저장소 클론
git clone <repository-url>
cd WCMS

# 의존성 설치
pip install -r server/requirements.txt
pip install -r client/requirements.txt
```

### 2. 서버 설정

```bash
cd server

# 데이터베이스 초기화
./init_db.sh   # Linux/Mac
# 또는
sh init_db.sh  # Windows Git Bash

# 관리자 계정 생성 (admin/admin)
python create_admin.py

# 서버 시작
python app.py
```

서버가 `http://127.0.0.1:5050`에서 실행됩니다.

### 3. 클라이언트 설정 (Windows PC)

```bash
cd client

# 직접 실행
python main.py

# 또는 빌드된 실행 파일 사용
build\main\main.exe
```

### 4. 웹 접속

브라우저에서 `http://127.0.0.1:5050` 접속 후 로그인
- **ID**: `admin`
- **PW**: `admin`

---

## 테스트 가이드

### 🧪 테스트 종류

#### 1. 서버 API 테스트

**목적**: 서버의 모든 API 엔드포인트 검증

```bash
cd server
python test_web_access.py
```

**테스트 항목**:
- ✅ 대시보드 접근
- ✅ 관리자 로그인
- ✅ PC 목록 조회
- ✅ 좌석 배치 조회
- ✅ 클라이언트 등록
- ✅ 하트비트 전송
- ✅ 명령 폴링

#### 2. 통합 테스트

**목적**: 서버-클라이언트 전체 흐름 테스트

```bash
python test_integration.py
```

**테스트 시나리오**:
1. 클라이언트 등록
2. 하트비트 전송
3. 명령 전송 및 실행
4. 명령 결과 보고

#### 3. 일괄 명령 테스트

**목적**: 여러 PC 동시 제어 기능 테스트

```bash
python test_bulk_commands.py
```

**전제 조건**:
- 서버가 실행 중
- 최소 1대 이상의 클라이언트가 온라인

**테스트 항목**:
- ✅ 일괄 CMD 명령 실행
- ✅ 일괄 winget 검색
- ✅ 일괄 파일 다운로드
- ✅ 일괄 계정 관리

### 📊 웹 UI 테스트

#### 일괄 명령 사용하기

1. **선택 모드 활성화**
   - "📋 선택 모드" 버튼 클릭

2. **PC 선택**
   - 마우스 **드래그**로 범위 선택
   - **Ctrl/Cmd + 클릭**으로 개별 추가
   - "✓ 온라인 PC 전체 선택" 버튼

3. **명령 실행**
   - 💻 CMD 실행
   - 📦 프로그램 설치
   - 📥 파일 다운로드
   - 👤 계정 관리
   - 🔌 전원 관리

4. **결과 확인**
   - 성공/실패 개수 알림
   - 선택 자동 해제

#### 개별 PC 제어

1. 선택 모드 **비활성화** 상태
2. PC 좌석 **클릭**
3. 상세 모달에서 개별 명령 실행

---

## API 명세

### 🔐 인증

대부분의 관리 API는 세션 기반 인증이 필요합니다.

```python
POST /login
{
    "username": "admin",
    "password": "admin"
}
```

### 📡 클라이언트 API

#### 등록

```python
POST /api/client/register
{
    "machine_id": "ABC123",
    "hostname": "DESKTOP-001",
    "mac_address": "00:11:22:33:44:55",
    "cpu_model": "Intel Core i5",
    "ram_total": 8192,
    ...
}
```

#### 하트비트

```python
POST /api/client/heartbeat
{
    "machine_id": "ABC123",
    "system_info": {
        "cpu_usage": 45.2,
        "ram_used": 4096,
        "disk_usage": 60.5,
        "ip_address": "192.168.1.100",
        ...
    }
}
```

#### 명령 폴링 (Long-polling)

```python
GET /api/client/command?machine_id=ABC123&timeout=30

# 응답 (명령 있음)
{
    "command_id": 1,
    "command_type": "execute",
    "command_data": "{\"command\": \"hostname\"}"
}

# 응답 (명령 없음)
{
    "command_id": null,
    "command_type": null,
    "command_data": null
}
```

#### 명령 결과 보고

```python
POST /api/client/command/result
{
    "machine_id": "ABC123",
    "command_id": 1,
    "status": "completed",
    "result": "DESKTOP-001"
}
```

### 🎛️ 관리 API

#### PC 목록 조회

```python
GET /api/pcs

# 응답
[
    {
        "id": 1,
        "hostname": "DESKTOP-001",
        "room_name": "1실습실",
        "seat_number": "1, 1",
        "is_online": true,
        "cpu_usage": 45.2,
        ...
    }
]
```

#### 일괄 명령 전송 ⭐

```python
POST /api/pcs/bulk-command
{
    "pc_ids": [1, 2, 3],
    "command_type": "execute",
    "command_data": {
        "command": "hostname"
    }
}

# 응답
{
    "total": 3,
    "success": 3,
    "failed": 0,
    "results": [
        {"pc_id": 1, "command_id": 10, "status": "success"},
        {"pc_id": 2, "command_id": 11, "status": "success"},
        {"pc_id": 3, "command_id": 12, "status": "success"}
    ]
}
```

#### 명령 타입

| 타입 | 설명 | 필수 파라미터 |
|------|------|--------------|
| `execute` | CMD 명령 실행 | `command` |
| `install` | winget 설치 | `app_id` |
| `download` | 파일 다운로드 | `url`, `destination` |
| `account` | 계정 관리 | `action`, `username`, `password` |
| `power` | 전원 관리 | `action` |

**계정 관리 예시**:

```python
# 계정 생성
{
    "command_type": "account",
    "command_data": {
        "action": "create",
        "username": "student01",
        "password": "Pass1234!"
    }
}

# 비밀번호 변경
{
    "command_type": "account",
    "command_data": {
        "action": "change_password",
        "username": "student01",
        "password": "NewPass5678!"
    }
}

# 계정 삭제
{
    "command_type": "account",
    "command_data": {
        "action": "delete",
        "username": "student01"
    }
}
```

**전원 관리 예시**:

```python
{
    "command_type": "power",
    "command_data": {
        "action": "shutdown"  # shutdown, restart, logout
    }
}
```

---

## 개발 가이드

### 프로젝트 구조

```
WCMS/
├── server/              # Flask 서버
│   ├── app.py          # 메인 애플리케이션
│   ├── db.sqlite3      # SQLite 데이터베이스
│   ├── templates/      # HTML 템플릿
│   └── migrations/     # DB 스키마
│
├── client/             # 클라이언트 프로그램
│   ├── main.py        # 메인 실행 파일
│   ├── collector.py   # 시스템 정보 수집
│   └── executor.py    # 명령 실행
│
├── test_*.py          # 테스트 스크립트
└── *.md              # 문서
```

### 데이터베이스 스키마

#### pc_info (PC 기본 정보)
- `id`: PRIMARY KEY
- `machine_id`: 고유 식별자
- `hostname`: PC 이름
- `room_name`: 실습실 이름
- `seat_number`: 좌석 번호
- `is_online`: 온라인 상태
- `last_seen`: 마지막 접속 시간

#### pc_specs (PC 스펙 - 정적)
- `pc_id`: FOREIGN KEY
- `cpu_model`, `cpu_cores`, `cpu_threads`
- `ram_total`, `disk_info`
- `os_edition`, `os_version`

#### pc_status (PC 상태 - 동적)
- `pc_id`: FOREIGN KEY
- `cpu_usage`, `ram_used`, `disk_usage`
- `current_user`, `processes`
- `created_at`: 기록 시간

#### pc_command (명령 큐)
- `id`: PRIMARY KEY
- `pc_id`: FOREIGN KEY
- `command_type`: 명령 타입
- `command_data`: JSON 형식 파라미터
- `status`: pending, executing, completed, error
- `result`: 실행 결과
- `created_at`, `completed_at`

### 클라이언트 동작 흐름

```python
1. 시작
   ↓
2. 서버에 등록 (최초 1회)
   ↓
3. Heartbeat 전송 (10분마다, 백그라운드)
   ↓
4. 명령 폴링 (Long-polling, 메인 스레드)
   ↓
5. 명령 수신 시 실행
   ↓
6. 결과를 서버에 보고
   ↓
7. 4번으로 돌아가서 반복
```

### 명령 실행 구현 (`executor.py`)

```python
class CommandExecutor:
    @staticmethod
    def execute_command(cmd_type, cmd_data):
        if cmd_type == 'execute':
            return CommandExecutor.execute(cmd_data.get('command'))
        
        elif cmd_type == 'install':
            return CommandExecutor.install(cmd_data.get('app_id'))
        
        elif cmd_type == 'download':
            return CommandExecutor.download_file(
                cmd_data.get('url'),
                cmd_data.get('destination')
            )
        
        elif cmd_type == 'account':
            return CommandExecutor.manage_account(
                cmd_data.get('action'),
                cmd_data.get('username'),
                cmd_data.get('password')
            )
        
        elif cmd_type == 'power':
            action = cmd_data.get('action')
            if action == 'shutdown':
                return CommandExecutor.shutdown()
            elif action == 'restart':
                return CommandExecutor.reboot()
            elif action == 'logout':
                return CommandExecutor.execute('shutdown /l')
```

---

## 문제 해결

### 서버 연결 실패

**증상**:
```
Connection refused: [Errno 61]
```

**해결**:
1. 서버가 실행 중인지 확인
2. 포트 5050이 사용 가능한지 확인
3. 방화벽 설정 확인

### 클라이언트 등록 실패

**증상**:
```
등록 실패: 500 - 이미 등록된 PC입니다
```

**해결**:
- 정상 동작입니다. 클라이언트는 자동으로 하트비트를 시작합니다.
- 재등록이 필요한 경우 DB에서 해당 PC 레코드 삭제

### 명령 실행 타임아웃

**증상**:
```
명령 실행 타임아웃 (30초 초과)
```

**해결**:
- `executor.py`의 `timeout` 값을 늘리세요
- 장시간 소요 명령(winget 설치)은 이미 300초로 설정됨

### winget 미설치 오류

**증상**:
```
오류: winget이 설치되어 있지 않습니다
```

**해결**:
- Windows 11 또는 최신 Windows 10 필요
- Microsoft Store에서 "앱 설치 관리자" 업데이트

### 계정 관리 권한 오류

**증상**:
```
계정 생성 실패: 액세스가 거부되었습니다
```

**해결**:
- 클라이언트를 **관리자 권한**으로 실행
- Windows 계정 관리는 관리자 권한 필수

### 모듈 임포트 오류

**증상**:
```
ModuleNotFoundError: No module named 'collector'
```

**해결**:
```bash
# client 디렉토리에서 실행
cd client
python main.py

# 또는 sys.path 수정
import sys
sys.path.insert(0, 'client')
```

---

## 참고 자료

### 추가 문서
- [STATUS.md](STATUS.md) - 프로젝트 진행 상황
- [API.md](API.md) - 상세 API 명세서 (레거시)
- [DEVELOP.md](DEVELOP.md) - 개발 세부사항 (레거시)

### 외부 라이브러리
- [Flask](https://flask.palletsprojects.com/)
- [psutil](https://psutil.readthedocs.io/)
- [WMI](https://pypi.org/project/WMI/)
- [requests](https://requests.readthedocs.io/)

---

## 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

---

**작성일**: 2025.11.18  
**작성자**: WCMS Development Team  
**버전**: 1.0

