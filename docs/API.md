# WCMS API 명세

> **버전**: v0.10.0
> **Base URL**: `http://<server>:3000`

인증: HMAC-SHA256 서명 httpOnly 쿠키 (`wcms_session`). `POST /api/admin/login` 으로 발급.

---

## 클라이언트 API `/api/client`

Windows 서비스 클라이언트 전용. 인증 없음.

### POST /api/client/register

PC 등록 (PIN 인증).

**Request**
```json
{
  "machine_id":  "string (required)",
  "pin":         "string(6) (required)",
  "hostname":    "string",
  "mac_address": "string",
  "ip_address":  "string",
  "cpu_model":   "string",
  "cpu_cores":   "number",
  "cpu_threads": "number",
  "ram_total":   "number",
  "disk_info":   "string (JSON)",
  "os_edition":  "string",
  "os_version":  "string"
}
```

**Response** `200`
```json
{ "status": "success", "pc_id": 1 }
```

**Errors** `403` Invalid PIN / PIN expired / PIN already used

---

### POST /api/client/heartbeat

상태 업데이트. 30초마다 호출.

**Request**
```json
{
  "machine_id":        "string",
  "cpu_usage":         0.0,
  "ram_used":          4.0,
  "ram_usage_percent": 50.0,
  "disk_usage":        "string (JSON)",
  "current_user":      "string",
  "uptime":            3600,
  "processes":         "string (JSON)",
  "ip_address":        "string"
}
```

**Response** `200` `{ "status": "ok" }`

---

### GET /api/client/commands

명령 대기 (Long-poll). 최대 30초 대기.

**Query** `machine_id=string`, `timeout=number (max 60)`

**Response** `200`
```json
{ "status": "no_command" }
// 또는
{
  "status": "command",
  "command": {
    "id": 1,
    "command_type": "shutdown",
    "command_data": {},
    "timeout": 300
  }
}
```

---

### POST /api/client/commands/:id/result

명령 결과 제출.

**Request**
```json
{
  "machine_id": "string",
  "status":     "completed | error",
  "result":     "string",
  "error":      "string"
}
```

**Response** `200` `{ "status": "ok" }`

---

### POST /api/client/offline

오프라인 신호.

**Request** `{ "machine_id": "string", "reason": "shutdown | network_error | unknown" }`

**Response** `200` `{ "status": "ok" }`

---

### POST /api/client/shutdown

종료 신호 (PC가 꺼지기 전 호출).

**Request** `{ "machine_id": "string" }`

**Response** `200` `{ "status": "ok" }`

---

### GET /api/client/version

최신 클라이언트 버전 조회.

**Response** `200`
```json
{ "version": "1.0.0", "download_url": "https://...", "changelog": "..." }
```

---

### POST /api/client/version

버전 등록. `Authorization: Bearer <WCMS_UPDATE_TOKEN>` 필요.

**Request** `{ "version": "string", "download_url": "string", "changelog": "string" }`

**Response** `200` `{ "status": "ok" }`

---

## 관리자 API — 인증 `/api/admin`

### POST /api/admin/login

**Request** `{ "username": "string", "password": "string" }`

**Response** `200` `{ "status": "ok", "username": "admin" }` + Set-Cookie

**Error** `401`

---

### POST /api/admin/logout

**Response** `200` `{ "status": "ok" }`

---

### GET /api/admin/me

**Auth** required

**Response** `200` `{ "username": "admin" }`

---

## 관리자 API — 등록 토큰 `/api/admin/tokens`

### GET /api/admin/tokens

**Auth** required

**Response** `200` 토큰 목록 배열

---

### POST /api/admin/tokens

**Auth** required

**Request** `{ "usage_type": "single | multi", "expires_in": 600 }`

**Response** `201` `{ "status": "ok", "pin": "123456", "expires_at": "..." }`

---

### DELETE /api/admin/tokens/:id

**Auth** required

**Response** `200` `{ "status": "ok" }`

---

## 관리자 API — 클라이언트 버전 `/api/admin/versions`

### GET /api/admin/versions

**Auth** required

**Response** `200` 버전 목록 배열

---

### DELETE /api/admin/versions/:id

**Auth** required

**Response** `200` `{ "status": "ok" }` / `404`

---

## 관리자 API — 프로세스 `/api/admin/processes`

### GET /api/admin/processes

최근 1시간 내 업데이트된 PC의 프로세스 목록.

**Auth** required

**Response** `200`
```json
[{ "pc_id": 1, "hostname": "PC-01", "processes": [...], "updated_at": "..." }]
```

---

## 관리자 API — PC `/api/pcs`

### GET /api/pcs/public

인증 불필요. Svelte 메인 화면용.

**Response** `200` `[{ "id", "hostname", "roomName", "seatNumber", "isOnline", "lastSeen" }]`

---

### GET /api/pcs

**Auth** required. `?room=<roomName>` 필터 가능.

**Response** `200` PC + spec + dynamic 조인 배열

---

### GET /api/pcs/duplicates

중복 호스트명 PC 목록.

**Auth** required

---

### GET /api/pcs/unverified

미검증 PC 목록.

**Auth** required

---

### GET /api/pcs/:id

PC 상세 정보.

**Auth** required

**Response** `200` / `404`

---

### GET /api/pcs/:id/history

네트워크 이벤트 기록 (최근 100개).

**Auth** required

---

### DELETE /api/pcs/:id

PC 삭제.

**Auth** required

**Response** `200` `{ "status": "ok" }`

---

## 관리자 API — PC 명령

모두 **Auth** required.

### POST /api/pcs/:id/command

범용 명령 전송.

**Request**
```json
{
  "command_type": "string",
  "command_data": {},
  "priority":     5,
  "timeout":      300
}
```

**Response** `200` `{ "status": "ok", "command_id": 1 }` / `404`

---

### 단축 명령

| 엔드포인트 | command_type | 추가 필드 |
|-----------|-------------|---------|
| `POST /api/pcs/:id/shutdown` | shutdown | - |
| `POST /api/pcs/:id/restart` | restart | - |
| `POST /api/pcs/:id/message` | show_message | `message`, `duration` |
| `POST /api/pcs/:id/kill-process` | kill_process | `process_name` |
| `POST /api/pcs/:id/install` | install | `package_name` |
| `POST /api/pcs/:id/uninstall` | uninstall | `package_name` |
| `POST /api/pcs/:id/account/create` | create_user | `username`, `password`, `language` |
| `POST /api/pcs/:id/account/delete` | delete_user | `username` |
| `POST /api/pcs/:id/account/password` | change_password | `username`, `new_password` |

---

### DELETE /api/pcs/:id/commands

대기 중인 명령 큐 삭제.

---

## 관리자 API — 일괄 명령 `/api/commands`

### GET /api/commands/pending

**Auth** required

**Response** `200` 대기 명령 목록

---

### POST /api/commands/results

**Auth** required

**Request** `{ "command_ids": [1, 2, 3] }`

**Response** `200` `[{ "id", "status", "result", "error", "completed_at" }]`

---

### POST /api/commands/bulk

**Auth** required

**Request**
```json
{
  "pc_ids":       [1, 2, 3],
  "command_type": "shutdown",
  "command_data": {},
  "priority":     5,
  "timeout":      300
}
```

**Response** `200` `{ "status": "ok", "command_ids": [1, 2, 3] }`

---

### DELETE /api/commands/bulk

**Auth** required

**Request** `{ "pc_ids": [1, 2, 3] }`

**Response** `200` `{ "status": "ok" }`

---

## 관리자 API — 실습실 `/api/rooms`

### GET /api/rooms

인증 불필요.

**Response** `200` 실습실 목록

---

### POST /api/rooms

**Auth** required

**Request** `{ "room_name": "string", "rows": 6, "cols": 8, "description": "string" }`

**Response** `201` `{ "status": "ok" }`

---

### PUT /api/rooms/:id

**Auth** required

**Request** 위 필드 일부 (partial)

---

### DELETE /api/rooms/:id

**Auth** required (soft delete — isActive: false)

---

### GET /api/rooms/:room/layout

인증 불필요. Svelte 메인 화면용.

**Response** `200`
```json
{
  "room": { "roomName", "rows", "cols", "..." },
  "seats": [{ "row", "col", "pcId", "hostname", "isOnline" }]
}
```

---

### POST /api/rooms/:room/layout

**Auth** required

**Request** `[{ "row": 1, "col": 1, "pc_id": 1 }]`

**Response** `200` `{ "status": "ok" }`

---

## 설치 API `/install`

### GET /install/install.cmd

Windows Batch 설치 스크립트 다운로드.

### GET /install/install.ps1

PowerShell 설치 스크립트 다운로드.

### GET /install/version

`/api/client/version` 으로 리다이렉트 (302).

---

## 헬스 체크

### GET /health

**Response** `200` `{ "status": "ok", "ts": "2026-01-01T00:00:00.000Z" }`