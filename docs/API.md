# WCMS API 문서

> **버전**: 0.8.6  
> **기본 URL**: `http://your-server:5050`  
> **업데이트**: 2026-02-11  
> **주요 변경**: Chocolatey 지원, 서비스 설치 개선

---

## 목차

1. [개요](#개요)
2. [인증](#인증)
3. [클라이언트 API](#클라이언트-api)
4. [관리자 API](#관리자-api)
5. [오류 코드](#오류-코드)

---

## 개요

### 통신 프로토콜
- **프로토콜**: HTTP/1.1
- **데이터 형식**: JSON
- **문자 인코딩**: UTF-8
- **타임아웃**: 30초 (요청), 5초 (명령 폴링)

### v0.8.6 주요 변경사항
1. **Chocolatey 지원**: 프로그램 설치 명령이 `winget`에서 `chocolatey`로 변경되었습니다.
2. **서비스 설치 개선**: `install.cmd`의 서비스 등록 방식이 개선되어 안정성이 향상되었습니다.
3. **UI 개선**: 계정 관리 및 전원 관리 모달이 클릭 기반 UI로 변경되었습니다.

---

## 인증

### 관리자 API

관리자 API는 **세션 기반 인증**을 사용합니다.

#### 로그인

**엔드포인트:**
```http
POST /login
Content-Type: application/x-www-form-urlencoded
```

**요청 본문:**
```
username=admin&password=your_password
```

**응답:**
- 성공: 302 Redirect to /
- 실패: 302 Redirect to /login

**세션 관리:**
- 쿠키 이름: `session`
- 만료: 브라우저 종료 시

### 클라이언트 API

클라이언트 API는 **PIN 기반 등록 인증**을 사용합니다.

- **등록 시**: 관리자가 생성한 6자리 PIN 필수
- **등록 후**: `machine_id` 기반 식별

---

## 클라이언트 API

### 1. 버전 확인

최신 클라이언트 버전을 조회합니다.

**엔드포인트:**
```http
GET /api/client/version
```

**응답:**
```json
{
  "status": "success",
  "version": "0.8.6",
  "download_url": "https://github.com/Nekonic/WCMS/releases/download/client-v0.8.6/WCMS-Client.exe",
  "changelog": "Chocolatey 지원 및 서비스 설치 개선"
}
```

---

### 2. 클라이언트 등록 (PIN 필수)

**엔드포인트:**
```http
POST /api/client/register
Content-Type: application/json
```

**요청:**
```json
{
  "machine_id": "A1B2C3D4E5F6",
  "pin": "123456",
  "hostname": "LAB-PC-01",
  "mac_address": "A1:B2:C3:D4:E5:F6",
  "ip_address": "192.168.1.100",
  "cpu_model": "Intel Core i5-9400",
  "cpu_cores": 6,
  "cpu_threads": 6,
  "ram_total": 16.0,
  "disk_info": {
    "C:\\": {"total_gb": 237.0, "fstype": "NTFS"}
  },
  "os_edition": "Windows 10 Pro",
  "os_version": "10.0.19045"
}
```

**필수 필드:**
- `machine_id`: 하드웨어 ID
- `pin`: 6자리 숫자 PIN
- `hostname`: PC 이름
- `mac_address`: MAC 주소

**응답:**
```json
{
  "status": "success",
  "message": "Registration successful",
  "pc_id": 123
}
```

**오류:**
- `400`: PIN 누락
- `403`: PIN 검증 실패 (`"Invalid or expired PIN"`)
- `403`: 1회용 PIN 재사용 (`"PIN already used"`)

---

### 3. 하트비트 (네트워크 최적화)

클라이언트의 동적 상태를 전송합니다. **네트워크 부하 최소화를 위해 델타 전송 방식 지원**

**엔드포인트:**
```http
POST /api/client/heartbeat
Content-Type: application/json
```

**전체 하트비트 (초회 또는 5분마다):**
```json
{
  "machine_id": "A1B2C3D4E5F6",
  "full_update": true,
  "system_info": {
    "cpu_usage": 45.2,
    "ram_used": 8.5,
    "ram_usage_percent": 53.1,
    "disk_usage": {
      "C:\\": {"used_gb": 107.2, "free_gb": 129.8, "percent": 45.2}
    },
    "current_user": "student",
    "uptime": 86400,
    "ip_address": "192.168.1.100",
    "processes": ["chrome.exe", "Code.exe", "python.exe"]
  }
}
```

**경량 하트비트 (명령 조회 시 함께 전송):**
```json
{
  "machine_id": "A1B2C3D4E5F6",
  "full_update": false,
  "system_info": {
    "cpu_usage": 52.1,
    "ram_usage_percent": 58.3,
    "ip_address": "192.168.1.101"
  }
}
```

**필드 설명:**

| 필드 | 전체 | 경량 | 설명 |
|------|------|------|------|
| `full_update` | ✅ | ✅ | 전체 업데이트 여부 |
| `cpu_usage` | ✅ | ✅ | CPU 사용률 (0~100) |
| `ram_usage_percent` | ✅ | ✅ | RAM 사용률 (0~100) |
| `ip_address` | ✅ | ✅ | IP 주소 (변경 감지용) |
| `ram_used` | ✅ | ❌ | RAM 사용량 (GB) |
| `disk_usage` | ✅ | ❌ | 디스크 사용량 (5분마다만) |
| `current_user` | ✅ | ❌ | 현재 사용자 |
| `uptime` | ✅ | ❌ | 가동 시간 |
| `processes` | ✅ | ❌ | 프로세스 목록 (대역폭 큰 데이터) |

**네트워크 최적화 전략:**

1. **IP 주소 자동 업데이트**
   - 모든 하트비트에 IP 포함 (4바이트)
   - 서버가 자동으로 `pc_info.ip_address` 업데이트
   - DHCP, VPN, 네트워크 전환 대응

2. **델타 전송 (경량 하트비트)**
   - 명령 조회 시 함께 전송 (HTTP 오버헤드 제거)
   - 프로세스 목록 제외 → **대역폭 90% 절감**
   - 2초마다: CPU, RAM, IP만 전송 (~100바이트)

3. **전체 업데이트 (5분마다)**
   - 디스크, 사용자, 프로세스 목록 포함
   - 데이터 정합성 보장
   - 프로세스 히스토리 수집

**응답:**
```json
{
  "status": "success",
  "message": "Heartbeat received",
  "ip_changed": true
}
```

**대역폭 비교:**

| 항목 | 기존 방식 | 개선 방식 | 절감률 |
|------|----------|----------|--------|
| 하트비트 주기 | 5분 | 5분 (전체) + 2초 (경량) | - |
| 전체 데이터 크기 | ~5KB | ~5KB | 0% |
| 경량 데이터 크기 | - | ~100B | - |
| 시간당 전송량 (100대) | 60MB | 6MB (전체) + 18MB (경량) = 24MB | **60% 절감** |
| 명령 조회 통합 | ❌ | ✅ | HTTP 오버헤드 50% 절감 |

**클라이언트 구현 권장:**
```python
last_full_heartbeat = 0
FULL_HEARTBEAT_INTERVAL = 300  # 5분

while True:
    # 명령 조회 + 경량 하트비트 (2초마다)
    response = requests.post(
        f"{SERVER_URL}/api/client/command",  # GET → POST로 변경
        json={
            "machine_id": MACHINE_ID,
            "heartbeat": {
                "full_update": False,
                "system_info": {
                    "cpu_usage": psutil.cpu_percent(),
                    "ram_usage_percent": psutil.virtual_memory().percent,
                    "ip_address": get_ip_address()
                }
            }
        }
    )
    
    # 5분마다 전체 하트비트
    if time.time() - last_full_heartbeat > FULL_HEARTBEAT_INTERVAL:
        send_full_heartbeat()
        last_full_heartbeat = time.time()
    
    time.sleep(2)
```

---

### 4. 명령 조회 + 경량 하트비트 (통합 엔드포인트)

명령 조회와 경량 하트비트를 통합하여 **HTTP 요청 오버헤드 50% 절감**

**엔드포인트:**
```http
POST /api/client/commands
Content-Type: application/json
```

**요청 (하트비트 포함):**
```json
{
  "machine_id": "A1B2C3D4E5F6",
  "heartbeat": {
    "cpu_usage": 52.1,
    "ram_usage_percent": 58.3,
    "ip_address": "192.168.1.101"
  }
}
```

**요청 (하트비트 없음):**
```json
{
  "machine_id": "A1B2C3D4E5F6"
}
```

**응답 (명령 있음):**
```json
{
  "status": "success",
  "data": {
    "has_command": true,
    "command": {
      "id": 456,
      "type": "shutdown",
      "parameters": {
        "delay": 60,
        "message": "System maintenance"
      },
      "timeout": 300,
      "priority": 5
    },
    "heartbeat_processed": true,
    "ip_changed": true
  }
}
```

**응답 (명령 없음):**
```json
{
  "status": "success",
  "data": {
    "has_command": false,
    "command": null,
    "heartbeat_processed": true,
    "ip_changed": false
  }
}
```

**에러 응답:**
```json
{
  "status": "error",
  "error": {
    "code": "PC_NOT_FOUND",
    "message": "PC not registered: A1B2C3D4E5F6"
  }
}
```

**명령 타입:**
- `shutdown`: 종료
- `restart`: 재시작 (reboot → restart로 통일)
- `message`: 메시지 표시
- `kill_process`: 프로세스 종료
- `execute`: CMD 실행
- `install`: 프로그램 설치 (Chocolatey)
- `download`: 파일 다운로드
- `create_user`: 사용자 생성
- `delete_user`: 사용자 삭제
- `change_password`: 비밀번호 변경

**Rate Limiting:** 최소 2초 간격

**네트워크 최적화 효과:**
- 기존: 명령 조회 (2초마다) + 하트비트 (5분마다) = 1,800회/시간 + 12회/시간
- 개선: 통합 요청 (2초마다) = **1,800회/시간 (50% 절감)**
- HTTP 헤더 오버헤드: ~500바이트/요청 × 12회 절감 = 6KB/시간/PC
- 100대 기준: **600KB/시간 절감**

**클라이언트 구현 (권장):**
```python
import psutil
import requests
import time

def get_ip_address():
    """현재 IP 주소 조회"""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "Unknown"

last_full_heartbeat = 0
FULL_HEARTBEAT_INTERVAL = 300  # 5분

while True:
    # 명령 조회 + 경량 하트비트 통합
    response = requests.post(
        f"{SERVER_URL}/api/client/commands",
        json={
            "machine_id": MACHINE_ID,
            "heartbeat": {
                "cpu_usage": psutil.cpu_percent(interval=0.1),
                "ram_usage_percent": psutil.virtual_memory().percent,
                "ip_address": get_ip_address()
            }
        },
        timeout=5
    )
    
    if response.status_code == 200:
        data = response.json()
        
        # 새 API 응답 형식 처리
        if data.get('status') == 'success':
            response_data = data.get('data', {})
            
            # IP 변경 알림
            if response_data.get('ip_changed'):
                logger.info(f"IP 주소 변경됨: {get_ip_address()}")
            
            # 명령 처리
            if response_data.get('has_command'):
                cmd = response_data.get('command', {})
                execute_command(cmd['id'], cmd['type'], cmd['parameters'])
    
    # 5분마다 전체 하트비트 (프로세스 목록 포함)
    if time.time() - last_full_heartbeat > FULL_HEARTBEAT_INTERVAL:
        send_full_heartbeat()
        last_full_heartbeat = time.time()
    
---

### 5. 명령 결과 보고

**엔드포인트:**
```http
POST /api/client/commands/{command_id}/result
Content-Type: application/json
```

**요청:**
```json
{
  "status": "success",
  "output": "종료 명령 실행됨"
}
```

**상태 값:**
- `success`: 성공적으로 완료
- `error`: 실행 중 오류 발생
- `timeout`: 타임아웃 발생

**에러 시 요청:**
```json
{
  "status": "error",
  "output": "Permission denied",
  "error_message": "관리자 권한 필요",
  "exit_code": 1
}
```

**응답:**
```json
{
  "status": "success",
  "data": {
    "message": "Result recorded",
    "command_id": 456,
    "final_status": "success"
  }
}
```

---

### 6. 종료 신호

**엔드포인트:**
```http
POST /api/client/shutdown
Content-Type: application/json
```

**요청:**
```json
{
  "machine_id": "A1B2C3D4E5F6"
}
```

---

## 관리자 API

### 등록 토큰 관리

#### 1. 토큰 생성

**엔드포인트:**
```http
POST /api/admin/registration-token
Content-Type: application/json
Authorization: Session Required
```

**요청:**
```json
{
  "usage_type": "multi",
  "expires_in": 600
}
```

**필드:**
- `usage_type`: `single` (기본값, 1회용) 또는 `multi` (재사용)
- `expires_in`: 만료 시간 (초, 기본값 600)

**응답:**
```json
{
  "status": "success",
  "token": "123456",
  "usage_type": "multi",
  "expires_at": "2026-02-10T15:30:00Z",
  "created_by": "admin"
}
```

---

#### 2. 토큰 목록

**엔드포인트:**
```http
GET /api/admin/registration-tokens
Authorization: Session Required
```

**응답:**
```json
{
  "status": "success",
  "tokens": [
    {
      "token": "123456",
      "usage_type": "multi",
      "used_count": 5,
      "expires_at": "2026-02-10T15:30:00Z",
      "created_by": "admin"
    }
  ]
}
```

---

#### 3. 토큰 삭제

**엔드포인트:**
```http
DELETE /api/admin/registration-token/{token}
Authorization: Session Required
```

**응답:**
```json
{
  "status": "success",
  "message": "Token expired successfully"
}
```

---

### PC 관리

#### 1. 미검증 PC 목록

**엔드포인트:**
```http
GET /api/admin/pcs/unverified
Authorization: Session Required
```

**응답:**
```json
{
  "status": "success",
  "pcs": [
    {
      "id": 10,
      "hostname": "OLD-PC-01",
      "machine_id": "LEGACY001",
      "is_verified": false
    }
  ]
}
```

---

#### 2. PC 삭제

**엔드포인트:**
```http
DELETE /api/admin/pc/{pc_id}
Authorization: Session Required
```

**응답:**
```json
{
  "status": "success",
  "message": "PC deleted successfully"
}
```

**주의:** 연관 데이터 모두 삭제 (Cascade)

---

### 명령 전송

#### PC 종료

**엔드포인트:**
```http
POST /api/admin/pc/{pc_id}/shutdown
Authorization: Session Required
```

**응답:**
```json
{
  "status": "success",
  "command_id": 456
}
```

#### PC 재시작

**엔드포인트:**
```http
POST /api/admin/pc/{pc_id}/reboot
```

#### CMD 명령 실행

**엔드포인트:**
```http
POST /api/admin/pc/{pc_id}/execute
Content-Type: application/json
```

**요청:**
```json
{
  "command": "ipconfig /all"
}
```

---

## 오류 코드

| 코드 | 의미 | 설명 |
|------|------|------|
| 200 | OK | 성공 |
| 302 | Found | 리다이렉트 |
| 400 | Bad Request | 필수 필드 누락 |
| 401 | Unauthorized | 세션 없음 |
| 403 | Forbidden | PIN 검증 실패 |
| 404 | Not Found | 리소스 없음 |
| 500 | Internal Server Error | 서버 오류 |

**에러 응답 형식:**
```json
{
  "status": "error",
  "message": "Error description"
}
```

---

## 변경 이력

### v0.8.6 (2026-02-11)

**주요 변경:**

1. **Chocolatey 지원**
   - `winget` 대신 `chocolatey`를 사용하여 프로그램 설치
   - 서비스 환경(`LocalSystem`)에서도 안정적인 설치 지원
   - Chocolatey 미설치 시 자동 설치 기능 추가

2. **서비스 설치 개선**
   - `install.cmd`의 서비스 등록 로직을 `sc create`로 변경하여 안정성 확보
   - 서비스 시작 시 인자 없이 실행되도록 수정하여 `StartServiceCtrlDispatcher` 호출 보장
   - `delayed-auto` 시작 유형 적용으로 부팅 시 안정성 향상

3. **UI 개선**
   - 계정 관리 및 전원 관리 모달을 클릭 기반 UI로 변경
   - 프로세스 종료 시 목록에서 선택 가능하도록 개선
   - RAM 사용량 도넛 차트 추가

---

## 참고 자료

- [Architecture](./ARCHITECTURE.md)
- [Getting Started](./GETTING_STARTED.md)
- [Changelog](./CHANGELOG.md)
- [GitHub](https://github.com/Nekonic/WCMS)
