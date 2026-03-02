# WCMS API 레퍼런스

> **버전**: v0.9.2
> **Base URL**: `http://<server>:5050`

---

## 인증

| 대상 | 방식 |
|------|------|
| 클라이언트 API | `machine_id` (등록된 PC 식별) |
| 관리자 API | 세션 쿠키 (`/login` POST 후) |
| 공개 엔드포인트 | 없음 |

관리자 전용 엔드포인트는 미로그인 시 `401` 반환.

---

## 엔드포인트 목록

### 클라이언트 API (`/api/client`)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/client/register` | PC 등록 (PIN 필수) |
| POST | `/api/client/heartbeat` | 상태 업데이트 |
| GET | `/api/client/commands` | 명령 대기 (Long-poll) |
| POST | `/api/client/commands/<id>/result` | 명령 결과 제출 |
| POST | `/api/client/offline` | 네트워크 오프라인 신호 |
| POST | `/api/client/shutdown` | 종료 신호 |
| GET | `/api/client/version` | 최신 클라이언트 버전 조회 |

### 관리자 API - PC

| 메서드 | 경로 | 인증 | 설명 |
|--------|------|------|------|
| GET | `/api/pcs` | 없음 | PC 목록 (`?room=<name>` 필터) |
| GET | `/api/pc/<id>` | 없음 | PC 상세 정보 |
| GET | `/api/pc/<id>/history` | 관리자 | 프로세스 기록 |
| DELETE | `/api/pc/<id>` | 관리자 | PC 삭제 |
| GET | `/api/pcs/duplicates` | 관리자 | 중복 호스트명 PC 목록 |
| GET | `/api/admin/pcs/unverified` | 관리자 | 미검증 PC 목록 |

### 관리자 API - PC 명령

모든 명령 엔드포인트는 관리자 인증 필요.

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/pc/<id>/command` | 범용 명령 전송 |
| POST | `/api/pc/<id>/shutdown` | 종료 |
| POST | `/api/pc/<id>/restart` | 재시작 |
| POST | `/api/pc/<id>/message` | 메시지 전송 |
| POST | `/api/pc/<id>/kill-process` | 프로세스 강제 종료 |
| POST | `/api/pc/<id>/install` | 프로그램 설치 (Chocolatey) |
| POST | `/api/pc/<id>/uninstall` | 프로그램 삭제 (Chocolatey) |
| POST | `/api/pc/<id>/account/create` | Windows 계정 생성 |
| POST | `/api/pc/<id>/account/delete` | Windows 계정 삭제 |
| POST | `/api/pc/<id>/account/password` | 비밀번호 변경 |
| DELETE | `/api/pc/<id>/commands/clear` | 대기 명령 전체 삭제 |

### 관리자 API - 일괄 명령

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/pcs/bulk-command` | 여러 PC에 동시 명령 |
| DELETE | `/api/pcs/commands/clear` | 여러 PC 대기 명령 삭제 |
| GET | `/api/commands/pending` | 전체 대기 명령 목록 |
| POST | `/api/commands/results` | 명령 결과 조회 (폴링) |

### 관리자 API - 실습실 / 좌석 배치

| 메서드 | 경로 | 인증 | 설명 |
|--------|------|------|------|
| GET | `/api/rooms` | 관리자 | 실습실 목록 |
| POST | `/api/rooms` | 관리자 | 실습실 생성 |
| PUT | `/api/rooms/<id>` | 관리자 | 실습실 수정 |
| DELETE | `/api/rooms/<id>` | 관리자 | 실습실 삭제 |
| GET | `/api/layout/map/<room_name>` | 없음 | 좌석 배치 조회 |
| POST | `/api/layout/map/<room_name>` | 관리자 | 좌석 배치 저장 |

### 관리자 API - 클라이언트 버전

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/client/versions` | 버전 목록 |
| POST | `/api/client/version` | 버전 등록 |
| DELETE | `/api/client/version/<id>` | 버전 삭제 |

### 관리자 API - 등록 토큰

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/admin/registration-token` | 토큰 생성 |
| GET | `/api/admin/registration-tokens` | 토큰 목록 |
| DELETE | `/api/admin/registration-token/<id>` | 토큰 삭제 |

### 설치 API (`/install`)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/install/install.cmd` | Windows Batch 설치 스크립트 |
| GET | `/install/install.ps1` | PowerShell 설치 스크립트 |
| GET | `/install/version` | 버전 조회 (→ `/api/client/version` 리다이렉트) |

`?server=<url>` 쿼리로 스크립트 내 서버 URL 지정 가능. 미지정 시 현재 호스트 사용.

---

## 상세

### POST /api/client/register

```json
// Request
{
  "machine_id": "DESKTOP-ABCDEF",
  "pin": "123456",
  "hostname": "DESKTOP-ABCDEF",
  "mac_address": "AA:BB:CC:DD:EE:FF",
  "ip_address": "192.168.1.100",
  "cpu_model": "Intel Core i5-10400",
  "cpu_cores": 6,
  "cpu_threads": 12,
  "ram_total": 16384,
  "disk_info": "[{\"device\": \"C:\\\\\", \"total\": 512000, \"used\": 128000}]",
  "os_edition": "Windows 10 Pro",
  "os_version": "10.0.19045"
}

// Response 200
{ "status": "success", "pc_id": 1 }
// Response 400: machine_id 또는 pin 누락
// Response 403: PIN 검증 실패 또는 만료
```

---

### POST /api/client/heartbeat

`full_update=true` (기본): CPU, RAM, 디스크, 프로세스 전체 저장.
`full_update=false`: CPU, RAM만 경량 업데이트.

```json
// Request
{
  "machine_id": "DESKTOP-ABCDEF",
  "full_update": true,
  "system_info": {
    "cpu_usage": 45.2,
    "ram_used": 8192,
    "ram_usage_percent": 50.0,
    "disk_usage": "[{\"device\": \"C:\\\\\", \"percent\": 25.0}]",
    "current_user": "student",
    "uptime": 3600,
    "ip_address": "192.168.1.100",
    "processes": ["chrome.exe", "notepad.exe"]
  }
}

// Response 200
{ "status": "success", "full_update": true, "ip_changed": false }
```

---

### GET /api/client/commands

명령이 올 때까지 연결을 유지하는 Long-poll.
`timeout`초(최대 60) 동안 0.5초마다 명령을 확인하고 즉시 반환.
연결 자체가 생존 신호로 처리되어 `last_seen`을 갱신함.
오프라인이었던 PC가 재연결하면 `network_events`에 복구 이벤트가 기록됨.

```
GET /api/client/commands?machine_id=DESKTOP-ABCDEF&timeout=30
```

```json
// 명령 있음
{
  "status": "success",
  "data": {
    "has_command": true,
    "command": {
      "id": 42,
      "type": "shutdown",
      "parameters": { "delay": 60, "message": "점검을 위해 종료합니다." },
      "timeout": 300,
      "priority": 5,
      "created_at": "2026-02-27T10:00:00"
    }
  }
}

// 명령 없음 (timeout 만료)
{ "status": "success", "data": { "has_command": false, "command": null } }
```

---

### POST /api/client/commands/<id>/result

```json
// Request
{
  "status": "success",   // "success" | "error" | "timeout"
  "output": "명령 실행 완료",
  "error_message": null,
  "exit_code": 0
}

// Response 200
{ "status": "success", "data": { "command_id": 42, "final_status": "success" } }
```

---

### POST /api/client/offline / POST /api/client/shutdown

```json
// Request
{ "machine_id": "DESKTOP-ABCDEF" }

// Response 200
{ "status": "success" }
```

`offline`: 네트워크 오류로 연결이 끊길 때 호출 (`reason = "network_error"`).
`shutdown`: 시스템 종료 전 호출 (`reason = "shutdown"`).

---

### GET /api/client/version

```json
// Response 200
{
  "status": "success",
  "version": "0.9.2",
  "download_url": "https://github.com/Nekonic/WCMS/releases/download/client-v0.9.2/WCMS-Client.exe",
  "changelog": "v0.9.2 변경사항",
  "released_at": "2026-02-27T00:00:00"
}
```

---

### GET /api/pcs

응답: PC 객체 배열 직접 반환 (래퍼 없음).

```
GET /api/pcs
GET /api/pcs?room=1실습실
```

---

### GET /api/pc/<id>

응답: PC 객체 직접 반환. 없으면 `{ "error": "PC not found" }`, 404.

---

### GET /api/pc/<id>/history

```
GET /api/pc/1/history
GET /api/pc/1/history?limit=50   # 기본 100
```

응답: 프로세스 기록 배열 (`updated_at`, `current_user`, `processes` 포함).

---

### POST /api/pc/<id>/command

범용 명령. 명령 타입은 [명령 타입 참조](#명령-타입) 참고.

```json
{
  "type": "shutdown",
  "data": { "delay": 0, "message": "" },
  "priority": 5,
  "timeout_seconds": 300
}
// Response: { "status": "success", "command_id": 42 }
```

---

### POST /api/pc/<id>/shutdown / restart

```json
// Request (모두 선택 필드)
{ "delay": 60, "message": "종료합니다." }
```

---

### POST /api/pc/<id>/message

```json
{ "message": "수업이 시작됩니다.", "duration": 10 }
```

---

### POST /api/pc/<id>/kill-process

```json
{ "process_name": "chrome.exe" }
```

---

### POST /api/pc/<id>/install / uninstall

```json
{ "app_id": "googlechrome" }   // Chocolatey 패키지 ID
```

---

### POST /api/pc/<id>/account/create

```json
{
  "username": "student01",
  "password": "Pass1234!",
  "full_name": "학생01",     // 선택
  "comment": "실습 계정"     // 선택
}
```

### POST /api/pc/<id>/account/delete

```json
{ "username": "student01" }
```

### POST /api/pc/<id>/account/password

```json
{ "username": "student01", "new_password": "NewPass5678!" }
```

---

### POST /api/pcs/bulk-command

```json
// Request
{
  "pc_ids": [1, 2, 3],
  "command_type": "shutdown",
  "command_data": { "delay": 30 }
}

// Response
{ "total": 3, "success": 3, "failed": 0, "results": [...] }
```

---

### DELETE /api/pcs/commands/clear

```json
// Request
{ "pc_ids": [1, 2, 3] }

// Response
{ "total": 3, "success": 3, "failed": 0, "total_deleted": 5, "results": [...] }
```

---

### GET /api/rooms

```json
{
  "total": 2,
  "rooms": [
    {
      "id": 1,
      "room_name": "1실습실",
      "rows": 5,
      "cols": 8,
      "description": "",
      "is_active": 1,
      "pc_count": 20,
      "created_at": "2026-01-01T00:00:00"
    }
  ]
}
```

### POST /api/rooms

```json
// Request
{ "room_name": "2실습실", "rows": 6, "cols": 10, "description": "" }

// Response
{ "status": "success", "room_id": 2 }
```

### PUT /api/rooms/<id>

변경할 필드만 포함. `room_name` 변경 시 `pc_info`, `seat_map` 연동 자동 갱신.

### DELETE /api/rooms/<id>

PC가 배치된 실습실은 삭제 불가 (400 반환).

---

### GET /api/layout/map/<room_name>

```json
{
  "rows": 5,
  "cols": 8,
  "seats": [
    { "id": 1, "room_name": "1실습실", "row": 0, "col": 0, "pc_id": 1 }
  ]
}
```

### POST /api/layout/map/<room_name>

기존 배치를 완전히 교체.

```json
{
  "rows": 5,
  "cols": 8,
  "seats": [
    { "row": 0, "col": 0, "pc_id": 1 },
    { "row": 0, "col": 1, "pc_id": 2 }
  ]
}
```

---

### POST /api/admin/registration-token

```json
// Request
{
  "usage_type": "single",   // "single" (1회용) | "multi" (다회용)
  "expires_in": 600         // 60 ~ 86400 초
}

// Response 200
{
  "status": "success",
  "id": 1,
  "token": "123456",
  "usage_type": "single",
  "expires_at": "2026-02-27T10:10:00",
  "created_by": "admin"
}
```

### GET /api/admin/registration-tokens

```
GET /api/admin/registration-tokens            # 활성 토큰만
GET /api/admin/registration-tokens?all=true   # 전체 (만료/사용 포함)
```

---

### POST /api/client/version (관리자)

```json
{
  "version": "0.9.2",
  "download_url": "https://github.com/Nekonic/WCMS/releases/download/client-v0.9.2/WCMS-Client.exe",
  "changelog": "v0.9.2 변경사항"
}
```

---

## 공통 응답

```json
// 성공
{ "status": "success", ... }

// 실패
{ "status": "error", "message": "오류 설명" }
```

일부 엔드포인트는 하위 호환성을 위해 래퍼 없이 배열/객체를 직접 반환함 (`GET /api/pcs`, `GET /api/pc/<id>` 등).

| 코드 | 의미 |
|------|------|
| 200 | 성공 |
| 400 | 필수 필드 누락 또는 잘못된 값 |
| 401 | 관리자 세션 없음 |
| 403 | PIN 검증 실패 |
| 404 | 리소스 없음 |
| 500 | 서버 오류 |

---

## 명령 타입

`/api/pc/<id>/command`의 `type` 및 Long-poll 응답의 `command.type` 값.

| 타입 | 설명 | parameters |
|------|------|------------|
| `shutdown` | PC 종료 | `delay` (초), `message` |
| `restart` | PC 재시작 | `delay` (초), `message` |
| `reboot` | PC 재시작 (별칭) | — |
| `message` | 메시지 표시 (`msg *`) | `message`, `duration` |
| `kill_process` | 프로세스 강제 종료 | `process_name` |
| `install` | 프로그램 설치 (Chocolatey) | `app_id` |
| `uninstall` | 프로그램 삭제 (Chocolatey) | `app_id` |
| `create_user` | Windows 계정 생성 | `username`, `password`, `full_name` |
| `delete_user` | Windows 계정 삭제 | `username` |
| `change_password` | 비밀번호 변경 | `username`, `new_password` |
| `execute` | CMD 명령 실행 | `command` |

---

## 오프라인 판정

클라이언트는 30초 Long-poll로 연결을 유지한다. 서버는 40초 이상 `last_seen`이 갱신되지 않으면 `is_online=0`으로 처리한다 (백그라운드 체커, 기본 10초 주기).

단절 이유(`reason`)는 `network_error` (명시적 offline 신호) 또는 `shutdown` (종료 신호)으로 기록되며, 재연결 시 `network_events` 테이블에 `online_at`과 `duration_sec`이 기록된다.