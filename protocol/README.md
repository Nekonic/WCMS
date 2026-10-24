# 클라이언트-서버 프로토콜 v1

실습실 PC의 클라이언트가 서버와 주고받는 형식이다. 메시지 예시는 `examples/`에 있고, 서버 테스트와 클라이언트 테스트가 같은 파일로 검증한다.

클라이언트는 학내망에서 서버 내부 주소로 직접 접속한다 (`https://<내부 주소>`). 아래 경로는 그 주소 기준이다.

## 1. 등록

`POST /client/register`, `Content-Type: application/json` — 예시 `examples/register_request.json`

| 필드 | 규칙 |
|---|---|
| pin | JSON 문자열, ASCII 숫자 6자리 (예: `"012345"`) |
| hostname | 1~64자 |
| machine_guid | 1~64자 (`HKLM\SOFTWARE\Microsoft\Cryptography\MachineGuid`). 같은 값으로 다시 등록하면 같은 PC로 보고 자리를 유지한다 |
| specs | 객체, JSON으로 16KB 이하 |
| version | 20자 이하, 생략 가능 |

| 응답 | 본문 |
|---|---|
| 201 | `{"pc_id", "token"}` (`examples/register_response.json`). 토큰은 다시 받을 수 없으므로 저장한다 |
| 400 | `{"error": "invalid" \| "parse_error", "detail", "fields"?}` |
| 403 | `{"error": "invalid_pin", "detail"}` |
| 429 | `{"error": "too_many_attempts", "detail"}` — 같은 IP에서 PIN 실패 10회면 10분 차단 |

토큰은 URL-safe 문자(A-Z a-z 0-9 - _) 43자다.

다시 등록하면 토큰이 바뀐다. 이전 토큰은 즉시 무효가 되고, 이전 토큰으로 열려 있던 연결은 close code `4410`으로 닫힌다.

## 2. WebSocket 연결

`GET /client/ws`, 헤더 `Authorization: Bearer <token>`

- 모든 텍스트 프레임과 HTTP 본문은 UTF-8 JSON이다.
- 토큰이 없거나 틀리면 핸드셰이크가 HTTP 403으로 거절된다 → 다시 등록해야 한다.
- 핸드셰이크가 HTTP 403이면 토큰이 무효다 → 다시 등록. 그 밖의 실패(시간 초과, 5xx, DNS)는 백오프 후 재시도.
- 첫 메시지는 반드시 `hello`다 (`examples/hello.json`). `proto`는 이 문서의 버전 `1`.
- 연결 상태가 곧 온라인/오프라인이다.
- 재접속: 대기 시간은 1초에서 시작해 두 배씩, 최대 60초. 매번 0~1초 무작위 지연을 더한다. 연결이 30초 이상 유지되면 1초로 되돌린다 (4409로 닫힌 경우는 되돌리지 않는다).
- ping은 20~30초 간격으로 보낸다. 10초 안에 pong이 없으면 연결이 끊긴 것으로 보고 재접속한다. 서버도 WebSocket ping으로 응답 없는 연결을 끊는다 (약 40초). 상태 보고와 별개다.

| close code | 의미 | 클라이언트 동작 |
|---|---|---|
| 4400 | hello 전에 hello가 아닌 메시지를 보냄 | 버그. 재접속 후 hello부터 |
| 4406 | 지원하지 않는 `proto` | 재접속하지 않는다. 자동 업데이트를 기다린다 (업데이트 경로는 프로토콜 버전과 무관하게 동작) |
| 4409 | 같은 PC의 새 연결로 교체됨 | 인증 실패가 아니다. 백오프 후 재접속 |
| 4410 | 토큰 무효 (재등록되었거나 PC가 삭제됨) | 재접속하지 않는다. 다시 등록이 필요 |

hello 전에 JSON이 아닌 텍스트는 bad_json 오류, 바이너리 프레임은 binary_not_supported 오류로 답하고 연결은 유지한다. proto가 없거나 1이 아니면 4406. 두 번째 hello는 unknown_type 오류.

## 3. 클라이언트 → 서버 (텍스트 프레임, JSON)

| type | 예시 | 규칙 |
|---|---|---|
| hello | `hello.json` | 연결 직후 한 번. `proto`(정수), `version`(문자열, 20자) |
| status | `status.json` | 10초마다. 5초보다 자주 오면 서버가 버린다 |
| ping | `ping.json` | 서버가 `pong`으로 답한다. 온라인 판정에는 쓰지 않는다 |

status 필드:

| 필드 | 규칙 |
|---|---|
| cpu | 0~100 숫자 (%) |
| mem_used, mem_total, disk_used, disk_total | 0 이상 숫자 (바이트), 2^53 이하 |
| user | 로그인한 사용자 이름, 문자열, 최대 64자 |
| session | `active`(로그인, 잠금 아님) / `locked` / `none`(로그인 없음). 그 밖의 값은 `none` |
| foreground | 앞에 떠 있는 창 `{"process", "title"}`. 문자열, 각각 최대 128자 / 256자 |

길이 제한은 유니코드 코드 포인트 기준이다. 클라이언트가 보내기 전에 자르고, 넘치면 서버도 잘라서 저장한다. 타입이나 범위가 맞지 않는 값과 목록에 없는 필드는 서버가 그 필드만 버린다. 숫자는 유한한 값만 받는다 (`NaN`, `Infinity` 불가). 연결 후 첫 status는 hello 직후 바로 보낸다.

## 4. 서버 → 클라이언트 (텍스트 프레임, JSON)

| 메시지 | 의미 |
|---|---|
| `{"type": "pong"}` | ping 응답 |
| `{"type": "error", "error": "bad_json"}` | JSON이 아니거나 객체가 아님 |
| `{"type": "error", "error": "unknown_type"}` | 모르는 type |
| `{"type": "error", "error": "binary_not_supported"}` | 아직 바이너리 프레임을 받지 않음 (계획 06 전) |

오류 메시지를 보낸 뒤에도 서버는 연결을 유지한다. 클라이언트는 기록만 남긴다. 클라이언트는 모르는 type과 모르는 필드를 무시한다 (이후 버전에서 명령 메시지가 추가된다).

명령 메시지는 계획 04에서 추가한다.

## 5. 바이너리 프레임 (계획 06에서 활성화)

화면 데이터는 바이너리 프레임으로 보낸다. 모든 정수는 리틀 엔디언.

| 바이트 | 내용 |
|---|---|
| 0 | 종류: 1 = 썸네일(WebP), 2 = 크게 보기(H.264 Annex B), 3 = 스크린샷(PNG) |
| 1 | 플래그: bit0 = 키프레임 (H.264일 때) |
| 2-5 | 스트림 id (uint32) |
| 6-9 | seq (uint32) |
| 10-17 | 캡처 시각 (uint64, Unix 밀리초) |
| 18~ | 본문 |
