# WCMS API 명세서

**버전**: v1.0.0  
**최종 수정일**: 2025-11-17  
**베이스 URL**: `http://your-server:5050/api`

---

## 목차

1. [개요](#1-개요)
2. [인증](#2-인증)
3. [공통 규칙](#3-공통-규칙)
4. [관리자 API](#4-관리자-api)
5. [클라이언트 API](#5-클라이언트-api)
6. [에러 코드](#6-에러-코드)
7. [Quick Start](#7-quick-start)

---

## 1. 개요

WCMS(Woosuk Computer Management System)는 대학 실습실 PC를 원격으로 모니터링하고 제어하기 위한 RESTful API를 제공합니다.

### 1.1. 지원 환경

- **프로토콜**: HTTP (프로덕션 환경에서는 HTTPS 권장)
- **데이터 형식**: JSON
- **문자 인코딩**: UTF-8

### 1.2. 환경별 엔드포인트

| 환경 | 베이스 URL |
|------|-----------|
| 개발 | `http://localhost:5050/api` |
| 프로덕션 | `http://your-server:5050/api` |

---

## 2. 인증

### 2.1. 관리자 인증

관리자 API는 **세션 기반 인증**을 사용합니다.

#### 로그인
```http
POST /login
Content-Type: application/x-www-form-urlencoded

username=admin&password=your_password
```

**응답 (성공)**:
- HTTP 302 Redirect to `/`
- 세션 쿠키 설정

**응답 (실패)**:
- HTTP 200 OK (로그인 페이지 재표시)
- 에러 메시지 포함

#### 로그아웃
```http
POST /logout
```

**응답**:
- HTTP 302 Redirect to `/`

### 2.2. 클라이언트 인증

클라이언트 API는 `machine_id`를 통한 식별 방식을 사용합니다. 별도의 인증 토큰은 필요하지 않습니다.

---

## 3. 공통 규칙

### 3.1. 명명 규칙

- **URL 경로**: snake_case (`/api/client/register`)
- **JSON 필드**: snake_case (`machine_id`, `command_type`)
- **Enum 값**: UPPER_SNAKE_CASE 또는 lowercase (`SHUTDOWN`, `shutdown`)

### 3.2. HTTP 상태 코드

| 코드 | 의미 | 사용 예 |
|------|------|---------|
| 200 | OK | 요청 성공 |
| 400 | Bad Request | 잘못된 요청 형식 |
| 401 | Unauthorized | 인증 실패 |
| 404 | Not Found | 리소스를 찾을 수 없음 |
| 500 | Internal Server Error | 서버 내부 오류 |

### 3.3. 공통 에러 응답 형식

```json
{
  "status": "error",
  "message": "에러 메시지",
  "code": "ERROR_CODE"
}
```

### 3.4. Timeout 설정

- **클라이언트 등록/하트비트**: 5-10초
- **명령 폴링**: 30초 (Long-polling)

---

## 4. 관리자 API

관리자가 웹 UI를 통해 PC를 제어하거나 정보를 조회할 때 사용하는 API입니다.

### 4.1. PC 상세 정보 조회

특정 PC의 상세 정보를 JSON으로 반환합니다.

#### 요청

```http
GET /api/pc/{pc_id}
```

#### Path Parameters

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| `pc_id` | integer | ✓ | PC의 고유 ID |

#### 응답 (200 OK)

```json
{
  "id": 5,
  "machine_id": "A1B2C3D4E5F6",
  "hostname": "LAB1-PC05",
  "mac_address": "A1:B2:C3:D4:E5:F6",
  "room_name": "1실습실",
  "seat_number": "3, 2",
  "ip_address": "192.168.1.105",
  "is_online": 1,
  "last_seen": "2024-11-17 10:30:00",
  "cpu_model": "Intel Core i7-9700",
  "cpu_cores": 8,
  "cpu_threads": 8,
  "cpu_usage": 45.2,
  "ram_total": 16384,
  "ram_used": 8192,
  "ram_usage_percent": 50.0,
  "disk_info": "{\"C:\": {\"total\": 256000000000}}",
  "os_edition": "Windows 10 Pro",
  "current_user": "student01"
}
```

#### 응답 (404 Not Found)

```json
{
  "error": "PC not found"
}
```

---

### 4.2. 원격 명령 전송

관리자가 특정 PC에 원격 명령을 전송합니다.

#### 요청

```http
POST /api/pc/{pc_id}/command
Content-Type: application/json
```

#### Path Parameters

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| `pc_id` | integer | ✓ | 대상 PC의 고유 ID |

#### Request Body

```json
{
  "type": "COMMAND_TYPE",
  "data": {
    "key": "value"
  }
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `type` | string | ✓ | 명령 유형 |
| `data` | object | ✓ | 명령별 추가 데이터 (없으면 `{}`) |

#### 지원하는 명령 유형

##### 4.2.1. PC 종료

```json
{
  "type": "shutdown",
  "data": {}
}
```

##### 4.2.2. PC 재시작

```json
{
  "type": "reboot",
  "data": {}
}
```

##### 4.2.3. CMD 명령어 실행

```json
{
  "type": "execute",
  "data": {
    "command": "ipconfig /all"
  }
```

| 필드 | 타입 | 필수 | 설명 | 제약사항 |
|------|------|------|------|---------|
| `command` | string | ✓ | 실행할 CMD 명령어 | 30초 timeout |

##### 4.2.4. 프로그램 설치 (winget)

```json
{
  "type": "install",
  "data": {
    "app_name": "Google.Chrome"
  }
}
```

| 필드 | 타입 | 필수 | 설명 | 제약사항 |
|------|------|------|------|---------|
| `app_name` | string | ✓ | winget 패키지 ID | 300초 timeout |

##### 4.2.5. 파일 다운로드

```json
{
  "type": "download",
  "data": {
    "url": "https://example.com/file.zip",
    "path": "C:\\Downloads\\file.zip"
  }
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `url` | string | ✓ | 다운로드할 파일의 URL |
| `path` | string | ✓ | 저장할 로컬 경로 |

##### 4.2.6. Windows 계정 생성

```json
{
  "type": "create_user",
  "data": {
    "username": "student01",
    "password": "SecureP@ss123",
    "full_name": "홍길동",
    "comment": "2024학년도 신입생"
  }
}
```

| 필드 | 타입 | 필수 | 설명 | 제약사항 |
|------|------|------|------|---------|
| `username` | string | ✓ | 사용자 계정명 | 3-20자, 영숫자와 언더스코어만 |
| `password` | string | ✓ | 비밀번호 | 최소 8자 권장 |
| `full_name` | string | ✗ | 전체 이름 | 최대 100자 |
| `comment` | string | ✗ | 계정 설명 | 최대 255자 |

> [!WARNING]
> **보안 주의사항**: 비밀번호는 반드시 HTTPS를 통해 전송해야 하며, 클라이언트 측에서 평문으로 로그에 기록하지 마세요.

##### 4.2.7. Windows 계정 삭제

```json
{
  "type": "delete_user",
  "data": {
    "username": "student01"
  }
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `username` | string | ✓ | 삭제할 사용자 계정명 |

##### 4.2.8. Windows 계정 비밀번호 변경

```json
{
  "type": "change_password",
  "data": {
    "username": "student01",
    "new_password": "NewP@ss456"
  }
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `username` | string | ✓ | 사용자 계정명 |
| `new_password` | string | ✓ | 새 비밀번호 |

#### 응답 (200 OK)

```json
{
  "message": "명령 전송 완료"
}
```

#### 응답 (401 Unauthorized)

```json
{
  "error": "Unauthorized"
}
```

#### 예제 요청

**cURL**
```bash
curl -X POST http://localhost:5050/api/pc/5/command \
  -H "Content-Type: application/json" \
  -b "session=your_session_cookie" \
  -d '{
    "type": "create_user",
    "data": {
      "username": "student01",
      "password": "SecureP@ss123",
      "full_name": "홍길동"
    }
  }'
```

**Python (requests)**
```python
import requests

session = requests.Session()
# 먼저 로그인
session.post('http://localhost:5050/login', data={
    'username': 'admin',
    'password': 'your_password'
})

# 명령 전송
response = session.post(
    'http://localhost:5050/api/pc/5/command',
    json={
        'type': 'create_user',
        'data': {
            'username': 'student01',
            'password': 'SecureP@ss123',
            'full_name': '홍길동'
        }
    }
)
print(response.json())
```

---

### 4.3. 프로세스 실행 기록 조회

특정 PC의 프로세스 실행 기록을 조회합니다.

#### 요청

```http
GET /api/pc/{pc_id}/history
```

#### Path Parameters

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| `pc_id` | integer | ✓ | PC의 고유 ID |

#### 응답 (200 OK)

```json
[
  {
    "created_at": "2025-11-17 10:30:00",
    "current_user": "student01",
    "processes": "[\"chrome.exe\", \"Code.exe\", \"notepad.exe\"]"
  },
  {
    "created_at": "2025-11-17 10:20:00",
    "current_user": "student01",
    "processes": "[\"chrome.exe\", \"explorer.exe\"]"
  }
]
```

---

### 4.4. 좌석 배치 관리

#### 4.4.1. 좌석 배치 조회

```http
GET /api/layout/map/{room_name}
```

#### Path Parameters

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| `room_name` | string | ✓ | 실습실 이름 (예: "1실습실") |

#### 응답 (200 OK)

```json
{
  "rows": 5,
  "cols": 8,
  "seats": [
    {
      "room_name": "1실습실",
      "row": 0,
      "col": 0,
      "pc_id": 5
    },
    {
      "room_name": "1실습실",
      "row": 0,
      "col": 1,
      "pc_id": 6
    }
  ]
}
```

#### 4.4.2. 좌석 배치 저장

```http
POST /api/layout/map/{room_name}
Content-Type: application/json
```

#### Request Body

```json
{
  "rows": 5,
  "cols": 8,
  "seats": [
    {
      "row": 0,
      "col": 0,
      "pc_id": 5
    },
    {
      "row": 0,
      "col": 1,
      "pc_id": 6
    }
  ]
}
```

#### 응답 (200 OK)

```json
{
  "status": "success"
}
```

---

## 5. 클라이언트 API

클라이언트 PC가 서버와 통신할 때 사용하는 API입니다.

### 5.1. 클라이언트 등록

클라이언트가 최초 실행 시 서버에 자신을 등록합니다.

#### 요청

```http
POST /api/client/register
Content-Type: application/json
```

#### Request Body

```json
{
  "machine_id": "A1B2C3D4E5F6",
  "hostname": "LAB1-PC05",
  "mac_address": "A1:B2:C3:D4:E5:F6",
  "cpu_model": "Intel Core i7-9700",
  "cpu_cores": 8,
  "cpu_threads": 8,
  "ram_total": 16384,
  "disk_info": "{\"C:\": {\"total\": 256000000000}}",
  "os_edition": "Windows 10 Pro",
  "os_version": "10.0.19045"
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `machine_id` | string | ✓ | MAC 주소 기반 고유 ID |
| `hostname` | string | ✓ | 컴퓨터 이름 |
| `mac_address` | string | ✓ | MAC 주소 |
| `cpu_model` | string | ✓ | CPU 모델명 |
| `cpu_cores` | integer | ✓ | 물리적 코어 수 |
| `cpu_threads` | integer | ✓ | 논리적 스레드 수 |
| `ram_total` | integer | ✓ | 총 RAM 크기 (MB) |
| `disk_info` | string | ✓ | 디스크 정보 (JSON 문자열) |
| `os_edition` | string | ✓ | OS 에디션 |
| `os_version` | string | ✓ | OS 버전 |

#### 응답 (200 OK)

```json
{
  "status": "success",
  "message": "등록 완료"
}
```

#### 응답 (500 Internal Server Error)

이미 등록된 PC인 경우:

```json
{
  "status": "error",
  "message": "이미 등록된 PC입니다."
}
```

#### 응답 (400 Bad Request)

필수 필드 누락 시:

```json
{
  "status": "error",
  "message": "machine_id is required"
}
```

---

### 5.2. 하트비트 (Heartbeat)

클라이언트가 주기적으로 동적 정보를 서버에 전송합니다.

#### 요청

```http
POST /api/client/heartbeat
Content-Type: application/json
```

#### Request Body

```json
{
  "machine_id": "A1B2C3D4E5F6",
  "system_info": {
    "cpu_usage": 45.2,
    "ram_used": 8192,
    "ram_usage_percent": 50.0,
    "disk_usage": "{\"C:\": {\"used\": 128000000000, \"free\": 128000000000}}",
    "ip_address": "192.168.1.105",
    "current_user": "student01",
    "uptime": 3600,
    "processes": "[\"chrome.exe\", \"Code.exe\", \"notepad.exe\"]"
  }
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `machine_id` | string | ✓ | PC 고유 ID |
| `system_info` | object | ✓ | 동적 시스템 정보 |

**system_info 객체**

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `cpu_usage` | float | ✓ | CPU 사용률 (%) |
| `ram_used` | integer | ✓ | 사용 중인 RAM (MB) |
| `ram_usage_percent` | float | ✓ | RAM 사용률 (%) |
| `disk_usage` | string | ✓ | 디스크 사용량 (JSON 문자열) |
| `ip_address` | string | ✓ | IP 주소 |
| `current_user` | string | ✓ | 현재 로그인 사용자 |
| `uptime` | integer | ✓ | 부팅 이후 경과 시간 (초) |
| `processes` | string | ✓ | 실행 중인 프로세스 목록 (JSON 배열 문자열) |

#### 응답 (200 OK)

```json
{
  "status": "success",
  "message": "Heartbeat received"
}
```

#### 응답 (404 Not Found)

등록되지 않은 PC인 경우:

```json
{
  "status": "error",
  "message": "PC not registered"
}
```

> [!NOTE]
> **권장 주기**: 10분 (600초)마다 전송

---

### 5.3. 명령 폴링 (Long-Polling)

클라이언트가 주기적으로 서버에 새로운 명령이 있는지 확인합니다.

#### 요청

```http
GET /api/client/command?machine_id={machine_id}&timeout={timeout}
```

#### Query Parameters

| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
|---------|------|------|--------|------|
| `machine_id` | string | ✓ | - | 클라이언트의 고유 ID |
| `timeout` | integer | ✗ | 10 | 대기 시간 (초) |

#### 응답 (200 OK)

**명령이 있는 경우**:

```json
{
  "command_type": "create_user",
  "command_data": "{\"username\": \"student01\", \"password\": \"SecureP@ss123\"}"
}
```

**명령이 없는 경우**:

```json
{
  "command_type": null,
  "command_data": null
}
```

> [!TIP]
> **Long-polling 최적화**: `timeout`을 30초로 설정하면 불필요한 네트워크 트래픽을 줄일 수 있습니다.

#### 예제 코드

**Python**
```python
import requests
import json

SERVER_URL = "http://localhost:5050/api"
MACHINE_ID = "A1B2C3D4E5F6"

while True:
    try:
        response = requests.get(
            f"{SERVER_URL}/client/command",
            params={"machine_id": MACHINE_ID, "timeout": 30},
            timeout=35
        )
        
        data = response.json()
        
        if data.get('command_type'):
            cmd_type = data['command_type']
            cmd_params = json.loads(data.get('command_data', '{}'))
            print(f"명령 수신: {cmd_type}")
            # 명령 실행 로직
            
    except requests.Timeout:
        continue
    except Exception as e:
        print(f"오류: {e}")
        time.sleep(5)
```

---

### 5.4. 명령 실행 결과 보고

> [!WARNING]
> **현재 미구현**: 이 엔드포인트는 API 명세서에만 존재하며, 실제 구현되지 않았습니다. 향후 구현 예정입니다.

클라이언트가 명령을 실행한 후 결과를 서버에 보고합니다.

#### 요청

```http
POST /api/client/command/result
Content-Type: application/json
```

#### Request Body

```json
{
  "machine_id": "A1B2C3D4E5F6",
  "command_id": 123,
  "status": "completed",
  "result": "User 'student01' created successfully."
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `machine_id` | string | ✓ | PC 고유 ID |
| `command_id` | integer | ✓ | 명령 ID |
| `status` | string | ✓ | 실행 상태 (`completed` 또는 `error`) |
| `result` | string | ✓ | 실행 결과 메시지 |

#### 응답 (200 OK)

```json
{
  "status": "success",
  "message": "Result received"
}
```

#### 응답 (404 Not Found)

```json
{
  "status": "error",
  "message": "Command or PC not found"
}
```

---

## 6. 에러 코드

### 6.1. 공통 에러 코드

| HTTP 코드 | 설명 | 대응 방법 |
|-----------|------|----------|
| 400 | Bad Request - 잘못된 요청 형식 | 요청 데이터 형식 확인 |
| 401 | Unauthorized - 인증 실패 | 로그인 후 재시도 |
| 404 | Not Found - 리소스를 찾을 수 없음 | PC ID 또는 URL 확인 |
| 500 | Internal Server Error - 서버 오류 | 관리자에게 문의 |

### 6.2. 클라이언트 특정 에러

**404 - PC not registered**
- **원인**: 서버에 등록되지 않은 PC
- **대응**: `/api/client/register`로 재등록

**500 - 이미 등록된 PC입니다**
- **원인**: 중복 등록 시도
- **대응**: 정상 상황이므로 하트비트 시작

---

## 7. Quick Start

### 7.1. 클라이언트 시작하기

#### 1단계: 클라이언트 등록

```python
import requests

SERVER_URL = "http://localhost:5050/api"
MACHINE_ID = "A1B2C3D4E5F6"

reg_data = {
    "machine_id": MACHINE_ID,
    "hostname": "LAB1-PC05",
    "mac_address": "A1:B2:C3:D4:E5:F6",
    "cpu_model": "Intel Core i7",
    "cpu_cores": 8,
    "cpu_threads": 8,
    "ram_total": 16384,
    "disk_info": "{}",
    "os_edition": "Windows 10",
    "os_version": "10.0"
}

response = requests.post(f"{SERVER_URL}/client/register", json=reg_data)
print(response.json())
```

#### 2단계: 하트비트 전송

```python
heartbeat_data = {
    "machine_id": MACHINE_ID,
    "system_info": {
        "cpu_usage": 45.0,
        "ram_used": 8192,
        "ram_usage_percent": 50.0,
        "disk_usage": "{}",
        "ip_address": "192.168.1.105",
        "current_user": "student",
        "uptime": 3600,
        "processes": "[]"
    }
}

response = requests.post(f"{SERVER_URL}/client/heartbeat", json=heartbeat_data)
print(response.json())
```

#### 3단계: 명령 폴링

```python
response = requests.get(
    f"{SERVER_URL}/client/command",
    params={"machine_id": MACHINE_ID, "timeout": 30},
    timeout=35
)
print(response.json())
```

### 7.2. 관리자 명령 전송하기

#### 1단계: 로그인

```python
import requests

session = requests.Session()
session.post('http://localhost:5050/login', data={
    'username': 'admin',
    'password': 'your_password'
})
```

#### 2단계: PC 종료 명령

```python
response = session.post(
    'http://localhost:5050/api/pc/5/command',
    json={'type': 'shutdown', 'data': {}}
)
print(response.json())
```

#### 3단계: 계정 생성 명령

```python
response = session.post(
    'http://localhost:5050/api/pc/5/command',
    json={
        'type': 'create_user',
        'data': {
            'username': 'student01',
            'password': 'SecureP@ss123',
            'full_name': '홍길동'
        }
    }
)
print(response.json())
```

---

## 부록: 변경 이력

### v1.0.0 (2025-11-17)
- 초기 API 명세서 작성
- 관리자 API 및 클라이언트 API 정의
- Windows 계정 관리 명령 추가 (`create_user`, `delete_user`, `change_password`)
- Long-polling 방식 명령 시스템 설계
- 좌석 배치 관리 API 추가