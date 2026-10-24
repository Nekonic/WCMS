# 클라이언트-서버 프로토콜 v1

클라이언트는 학내망에서 서버 내부 주소로 직접 접속한다. 이 문서의 경로는 그 주소 기준이다.

## 1. 등록

`POST /client/register` (Content-Type: application/json)

```json
{"pin": "123456", "hostname": "LAB-01", "machine_guid": "<HKLM\\SOFTWARE\\Microsoft\\Cryptography\\MachineGuid>", "specs": {}, "version": "2026.1"}
```

| 필드 | 제한 |
|---|---|
| pin | 6자리 문자열 |
| hostname | 1~64자 |
| machine_guid | 1~64자. 같은 값으로 다시 등록하면 같은 PC로 취급하고 자리를 유지한다 |
| specs | 객체, JSON으로 16KB 이하. 키는 자유 (cpu, ram_gb, os, ip, mac 등) |
| version | 20자 이하 |

응답:

| 상태 | 본문 |
|---|---|
| 201 | `{"pc_id": 1, "token": "..."}`. 토큰은 다시 볼 수 없으므로 클라이언트가 저장한다 |
| 400 | `{"error": "bad_json" \| "bad_fields" \| "specs_too_large"}` |
| 403 | `{"error": "invalid_pin"}` |
| 429 | `{"error": "too_many_attempts"}`. 같은 IP에서 PIN 실패 10회면 10분 차단 |

## 2. WebSocket 연결

`GET /client/ws`, 헤더 `Authorization: Bearer <token>`

- 토큰이 없거나 틀리면 핸드셰이크가 403으로 거절된다. 다시 등록해야 한다.
- 같은 PC로 새 연결이 들어오면 이전 연결은 서버가 close code `4409`로 닫는다.
- 모든 메시지는 JSON 텍스트 프레임이다. 형식: `{"type": "...", ...}`
- 연결이 끊기면 재접속한다. 대기 시간은 1초에서 시작해 두 배씩 늘리고 최대 60초, 매번 0~1초 무작위 지연을 더한다.

## 3. 클라이언트 → 서버

### hello

연결 직후 한 번.

```json
{"type": "hello", "version": "2026.1"}
```

### status

10초마다. 서버는 30초 동안 status가 없으면 오프라인으로 본다.

```json
{
  "type": "status",
  "cpu": 12.5,
  "mem_used": 8123456789, "mem_total": 17179869184,
  "disk_used": 246000000000, "disk_total": 512000000000,
  "user": "Student",
  "session": "active",
  "foreground": {"process": "chrome.exe", "title": "YouTube - Chrome"}
}
```

| 필드 | 규칙 |
|---|---|
| cpu | 0 이상 숫자 (%) |
| mem_*, disk_* | 0 이상 숫자 (바이트) |
| user | 로그인한 사용자 이름, 최대 64자 |
| session | `active`(로그인, 잠금 아님) / `locked` / `none`(로그인 없음). 그 밖의 값은 `none` |
| foreground | 앞에 떠 있는 창. process 최대 128자, title 최대 256자 |

목록에 없는 필드는 버린다.

### ping

```json
{"type": "ping"}
```

서버 응답: `{"type": "pong"}`

## 4. 서버 → 클라이언트

| 메시지 | 의미 |
|---|---|
| `{"type": "pong"}` | ping 응답 |
| `{"type": "error", "error": "unknown_type"}` | 모르는 type을 받음 |
| `{"type": "error", "error": "bad_json"}` | JSON이 아니거나 바이너리 프레임 (연결은 유지) |

명령 메시지는 계획 2에서 추가한다.
