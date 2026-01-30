# WCMS API 문서

> **버전**: 0.6.0 (개발 중)  
> **기본 URL**: `http://your-server:5050`  
> **업데이트**: 2025-12-30

---

## 목차

1. [인증](#인증)
2. [클라이언트 API](#클라이언트-api)
3. [관리자 API](#관리자-api)
4. [오류 코드](#오류-코드)

---

## 인증

### 관리자 API
관리자 API는 세션 기반 인증을 사용합니다.

**로그인:**
```http
POST /login
Content-Type: application/x-www-form-urlencoded

username=admin&password=yourpassword
```

**응답:**
- 성공: 302 Redirect to /
- 실패: 302 Redirect to /login

**세션:**
- 쿠키: `session` (Flask session cookie)
- 만료: 브라우저 종료 시

### 클라이언트 API
클라이언트 API는 `machine_id` 기반 식별을 사용합니다.
- 인증 불필요 (내부 네트워크 전용)

---

## 클라이언트 API

### 1. 클라이언트 등록

새로운 클라이언트를 서버에 등록하거나 기존 정보를 업데이트합니다.

**엔드포인트:**
```http
POST /api/client/register
```

**요청 본문:**
```json
{
  "machine_id": "A1B2C3D4E5F6",
  "hostname": "LAB-PC-01",
  "mac_address": "A1:B2:C3:D4:E5:F6",
  "ip_address": "192.168.1.100",
  "cpu_model": "Intel Core i5-9400",
  "cpu_cores": 6,
  "cpu_threads": 6,
  "ram_total": 16.0,
  "disk_info": {
    "C:\\": {
      "total_gb": 237.0,
      "fstype": "NTFS",
      "mountpoint": "C:\\"
    }
  },
  "os_edition": "Windows 10 Pro",
  "os_version": "10.0.19045"
}
```

**응답:**
```json
{
  "status": "success",
  "message": "Registration successful",
  "pc_id": 123
}
```

---

### 2. 하트비트

클라이언트의 현재 상태를 서버에 전송합니다.

**엔드포인트:**
```http
POST /api/client/heartbeat
```

**요청 본문:**
```json
{
  "pc_id": 123,
  "cpu_usage": 45.2,
  "ram_used": 8.5,
  "ram_usage_percent": 53.1,
  "disk_usage": {
    "C:\\": {
      "used_gb": 107.2,
      "free_gb": 129.8,
      "percent": 45.2
    }
  },
  "current_user": "student",
  "uptime": 86400,
  "processes": ["chrome.exe", "Code.exe"]
}
```

**응답:**
```json
{
  "status": "success",
  "message": "Heartbeat recorded"
}
```

---

### 3. 명령 조회

대기 중인 명령을 조회합니다 (Long-polling).

**엔드포인트:**
```http
GET /api/client/command?pc_id=123
```

**응답:**
```json
{
  "status": "success",
  "commands": [
    {
      "id": 456,
      "type": "shutdown",
      "data": {},
      "priority": 5,
      "timeout": 300
    },
    {
      "id": 457,
      "type": "execute",
      "data": {
        "command": "ipconfig /all"
      },
      "priority": 5,
      "timeout": 300
    }
  ]
}
```

**명령 타입:**
- `shutdown`: PC 종료
- `reboot`: PC 재시작
- `execute`: CMD 명령 실행
- `install`: 프로그램 설치 (winget)
- `download`: 파일 다운로드
- `create_user`: 사용자 생성
- `delete_user`: 사용자 삭제
- `change_password`: 비밀번호 변경

---

### 5. 명령 결과 보고

명령 실행 결과를 서버에 보고합니다.

**엔드포인트:**
```http
POST /api/client/command/result
```

**요청 본문:**
```json
{
  "command_id": 456,
  "status": "completed",
  "result": "종료 명령 실행됨"
}
```

**status 값:**
- `completed`: 정상 완료
- `error`: 오류 발생

**응답:**
```json
{
  "status": "success",
  "message": "Result recorded"
}
```

---

### 5. 버전 확인

클라이언트의 최신 버전을 확인합니다.

**엔드포인트:**
```http
GET /api/client/version
```

**응답:**
```json
{
  "status": "success",
  "version": "1.0.0",
  "download_url": "https://github.com/.../releases/latest",
  "changelog": "- 버그 수정\n- 성능 개선",
  "released_at": "2025-12-30 00:00:00"
}
```

---

## 관리자 API

### 1. PC 목록 조회

모든 PC 또는 특정 실습실의 PC 목록을 조회합니다.

**엔드포인트:**
```http
GET /api/pcs
GET /api/pcs?room=1실습실
```

**인증:** 필요 (세션)

**응답:**
```json
{
  "status": "success",
  "count": 2,
  "pcs": [
    {
      "id": 1,
      "machine_id": "A1B2C3D4E5F6",
      "hostname": "LAB-PC-01",
      "ip_address": "192.168.1.100",
      "mac_address": "A1:B2:C3:D4:E5:F6",
      "room_name": "1실습실",
      "seat_number": "1, 1",
      "is_online": 1,
      "last_seen": "2025-12-30 00:00:00",
      "cpu_usage": 45.2,
      "ram_used": 8.5,
      "cpu_model": "Intel Core i5-9400",
      "ram_total": 16.0
    }
  ]
}
```

---

### 2. PC 상세 정보

특정 PC의 상세 정보를 조회합니다.

**엔드포인트:**
```http
GET /api/pc/{pc_id}
```

**인증:** 필요 (세션)

**응답:**
```json
{
  "status": "success",
  "pc": {
    "id": 1,
    "machine_id": "A1B2C3D4E5F6",
    "hostname": "LAB-PC-01",
    "ip_address": "192.168.1.100",
    "is_online": 1,
    "cpu_usage": 45.2,
    "ram_used": 8.5,
    "ram_total": 16.0,
    "disk_info": "{...}",
    "processes": "[...]"
  }
}
```

---

### 3. PC 상태 기록

PC의 과거 상태 기록을 조회합니다.

**엔드포인트:**
```http
GET /api/pc/{pc_id}/history?limit=100
```

**인증:** 필요 (세션)

**파라미터:**
- `limit`: 조회할 기록 수 (기본: 100)

**응답:**
```json
{
  "status": "success",
  "count": 100,
  "history": [
    {
      "id": 1000,
      "pc_id": 1,
      "cpu_usage": 45.2,
      "ram_used": 8.5,
      "created_at": "2025-12-30 00:00:00"
    }
  ]
}
```

---

### 4. 명령 전송

PC에 명령을 전송합니다.

**엔드포인트:**
```http
POST /api/pc/{pc_id}/command
```

**인증:** 필요 (세션)

**요청 본문:**
```json
{
  "type": "execute",
  "data": {
    "command": "ipconfig /all"
  },
  "priority": 5,
  "max_retries": 3,
  "timeout_seconds": 300
}
```

**응답:**
```json
{
  "status": "success",
  "message": "Command sent",
  "command_id": 456
}
```

---

### 5. PC 종료

PC를 종료합니다.

**엔드포인트:**
```http
POST /api/pc/{pc_id}/shutdown
```

**인증:** 필요 (세션)

**응답:**
```json
{
  "status": "success",
  "message": "Shutdown command sent",
  "command_id": 456
}
```

---

### 6. PC 재시작

PC를 재시작합니다.

**엔드포인트:**
```http
POST /api/pc/{pc_id}/reboot
```

**인증:** 필요 (세션)

**응답:**
```json
{
  "status": "success",
  "message": "Reboot command sent",
  "command_id": 457
}
```

---

### 7. 계정 생성

Windows 계정을 생성합니다.

**엔드포인트:**
```http
POST /api/pc/{pc_id}/account/create
```

**인증:** 필요 (세션)

**요청 본문:**
```json
{
  "username": "student01",
  "password": "password123",
  "full_name": "Student 01",
  "comment": "실습용 계정"
}
```

**응답:**
```json
{
  "status": "success",
  "message": "Account creation command sent",
  "command_id": 458
}
```

---

### 8. 계정 삭제

Windows 계정을 삭제합니다.

**엔드포인트:**
```http
POST /api/pc/{pc_id}/account/delete
```

**인증:** 필요 (세션)

**요청 본문:**
```json
{
  "username": "student01"
}
```

**응답:**
```json
{
  "status": "success",
  "message": "Account deletion command sent",
  "command_id": 459
}
```

---

### 9. 비밀번호 변경

Windows 계정의 비밀번호를 변경합니다.

**엔드포인트:**
```http
POST /api/pc/{pc_id}/account/password
```

**인증:** 필요 (세션)

**요청 본문:**
```json
{
  "username": "student01",
  "new_password": "newpassword123"
}
```

**응답:**
```json
{
  "status": "success",
  "message": "Password change command sent",
  "command_id": 460
}
```

---

## 오류 코드

### HTTP 상태 코드

| 코드 | 의미 | 설명 |
|------|------|------|
| 200 | OK | 요청 성공 |
| 400 | Bad Request | 잘못된 요청 (필수 파라미터 누락 등) |
| 401 | Unauthorized | 인증 필요 (로그인 안 됨) |
| 404 | Not Found | 리소스를 찾을 수 없음 (PC 없음 등) |
| 500 | Internal Server Error | 서버 내부 오류 |

### 오류 응답 형식

```json
{
  "status": "error",
  "message": "PC not found"
}
```

### 일반적인 오류 메시지

| 메시지 | 원인 | 해결 방법 |
|--------|------|----------|
| `machine_id is required` | machine_id 누락 | machine_id 파라미터 추가 |
| `pc_id is required` | pc_id 누락 | pc_id 파라미터 추가 |
| `PC not found` | 존재하지 않는 PC | pc_id 확인 |
| `Unauthorized` | 로그인 안 됨 | 로그인 후 재시도 |
| `username and password are required` | 필수 필드 누락 | 모든 필수 필드 전송 |

---

## 예제

### Python 예제 (클라이언트)

```python
import requests

SERVER_URL = "http://your-server:5050"

# 등록
data = {
    "machine_id": "A1B2C3D4E5F6",
    "hostname": "LAB-PC-01",
    # ... 기타 정보
}
response = requests.post(f"{SERVER_URL}/api/client/register", json=data)
print(response.json())

# 하트비트
data = {
    "pc_id": 123,
    "cpu_usage": 45.2,
    # ... 기타 정보
}
response = requests.post(f"{SERVER_URL}/api/client/heartbeat", json=data)
print(response.json())

# 명령 조회
response = requests.get(f"{SERVER_URL}/api/client/command", params={"pc_id": 123})
commands = response.json().get("commands", [])
for cmd in commands:
    print(f"명령: {cmd['type']}")
```

### JavaScript 예제 (관리자)

```javascript
// PC 목록 조회
fetch('/api/pcs?room=1실습실')
  .then(response => response.json())
  .then(data => {
    console.log(`PC 개수: ${data.count}`);
    data.pcs.forEach(pc => {
      console.log(`${pc.hostname}: ${pc.is_online ? '온라인' : '오프라인'}`);
    });
  });

// 종료 명령 전송
fetch('/api/pc/123/shutdown', {
  method: 'POST'
})
  .then(response => response.json())
  .then(data => {
    console.log(data.message);
  });
```

---

## 변경 이력

### v0.6.0 (2025-12-30)
- API Blueprint로 재구성
- 타입 힌팅 추가
- 오류 처리 개선

### v0.5.6 (2025-11-19)
- 초기 API 문서 작성
- 클라이언트/관리자 API 분리

---

**문의**: 이슈 생성 또는 프로젝트 관리자에게 연락

