# 브라우저 실시간 WebSocket (`/ws/live`)

웹 화면이 PC 상태를 실시간으로 받는 연결이다. 구현은 `server/live/consumers.py`, 알림은 `server/live/publish.py`. REST(`/api/...`)는 CRUD와 기록 조회에만 쓰고 실시간 상태는 이 연결로만 받는다.

## 1. 연결

`wss://<공개 주소>/ws/live`

- 모든 프레임은 UTF-8 JSON 텍스트다. 바이너리 프레임은 `bad_json` 오류로 답한다.
- 인증은 로그인 세션 쿠키(`sessionid`)다. 별도 토큰은 없다. 비로그인도 연결할 수 있다 (공개 토픽만 구독 가능).
- Origin 검사: `Origin` 헤더가 없거나 그 호스트가 서버 `ALLOWED_HOSTS`에 없으면 핸드셰이크가 거절된다 (HTTP 403).
- 관리자는 활성 상태이고 `is_staff`인 로그인 사용자다. 관리자 토픽은 구독할 때마다 DB에서 권한을 다시 확인한다.
- 연결은 브라우저 탭마다 하나. 여러 토픽을 한 연결에서 구독한다.

## 2. 토픽

| 토픽 | 구독 가능 | 스냅샷 키 | 이후 메시지 |
|---|---|---|---|
| `room:<id>` | 관리자 | `pcs` (좌석이 정해진 PC 목록, 행·열 순) | `pc`, `room_changed` |
| `room:<id>:public` | 누구나 | `seats` (좌석 목록, 행·열 순) | `seat`, `room_changed` |
| `pc:<id>` | 관리자 | `pc` (PC 하나) | `pc` |

- `<id>`는 ASCII 숫자, 10자리 이하, 앞자리 0 없음 (`0`, `7`, `305`). `room:05`, 전각·다른 문자 체계 숫자, 앞뒤 공백·줄바꿈은 `bad_topic`. `pc:<id>:public`은 없다 (`bad_topic`).
- `room:<id>`의 `pc` 메시지는 그 실습실에 좌석이 정해진 PC만 보낸다. 좌석 없는 PC는 `pc:<id>`로만 받는다.
- `seat` 메시지는 켜짐/꺼짐이 바뀔 때만 온다. 상태 보고(사용자, 창 제목 등)만 바뀌면 공개 토픽에는 아무것도 오지 않는다.
- `room_changed`는 실습실 설정 변경·삭제, 좌석 배치 변경, 그 실습실 PC 삭제 때 온다. 받으면 같은 토픽을 다시 `subscribe`해 새 스냅샷을 받는다 (실습실이 삭제됐으면 `not_found`).
- `pc:<id>` 구독자는 그 PC가 삭제되어도 아무 메시지를 받지 않는다. 실습실에 속한 PC였다면 그 실습실 토픽에 `room_changed`가 온다. 그 밖에는 다시 `subscribe`해 `not_found`로 확인한다.

## 3. 브라우저 → 서버

| type | 예시 | 규칙 |
|---|---|---|
| subscribe | `{"type": "subscribe", "topic": "room:3"}` | 성공하면 `snapshot`. 이미 구독한 토픽이면 스냅샷만 다시 보낸다 (알림은 한 번씩만 온다) |
| unsubscribe | `{"type": "unsubscribe", "topic": "room:3"}` | 응답 없음. 구독하지 않은 토픽이면 무시 |
| ping | `{"type": "ping"}` | `pong`으로 답한다. 약 25초마다 보낸다 (아래 참고) |

ping이 필요한 이유: 서버의 그룹 구독은 채널 레이어에서 24시간 뒤 만료되고 Redis가 재시작되면 사라진다. 서버는 ping을 받을 때마다 이 연결의 구독(토픽 그룹, 관리자는 로그아웃 알림용 사용자 그룹)을 다시 등록한다. ping을 보내지 않는 연결은 오래 열려 있으면 알림이 조용히 끊길 수 있다. Cloudflare의 유휴 연결 종료도 막는다.

관리자 연결은 다시 등록하기 전에 계정이 아직 활성 관리자인지와 로그인 세션이 남아 있는지를 확인한다. 둘 중 하나라도 아니면 (사용자 그룹이 만료된 사이에 로그아웃 알림을 놓친 경우 포함) `pong` 대신 4401로 닫는다. 비로그인 연결은 확인하지 않는다.

## 4. 서버 → 브라우저

| type | 형식 |
|---|---|
| snapshot | `{"type": "snapshot", "topic", "pcs" \| "seats" \| "pc"}` — 키는 2절 표 |
| pc | `{"type": "pc", "topic", "pc"}` — PC 하나의 전체 상태 |
| seat | `{"type": "seat", "topic", "seat"}` — 좌석 하나의 전체 공개 상태 |
| room_changed | `{"type": "room_changed", "topic"}` |
| pong | `{"type": "pong"}` |
| error | `{"type": "error", "error", "topic"?}` — 연결은 유지된다 |

PC 객체(`pcs`의 원소, `pc`)는 OpenAPI의 `LivePC`와 같다: `id, hostname, label, room, row, col, version, online, session, user, foreground, cpu, mem_used, mem_total, disk_used, disk_total`. 꺼진 PC는 `session`이 `"none"`, `user`가 `""`, `foreground`와 수치가 `null`이다. `hostname`, `user`, `foreground`는 학생이 바꿀 수 있는 값이므로 화면에는 텍스트로만 넣는다.

좌석 객체(`seats`의 원소, `seat`)는 OpenAPI의 `PublicSeat`와 같다: `row, col, label, online`.

| error | 뜻 | topic 포함 |
|---|---|---|
| bad_json | JSON 객체가 아님 (깨진 JSON, 배열·문자열 등, 바이너리 프레임) | 아니오 |
| unknown_type | 모르는 `type` | 아니오 |
| bad_topic | 토픽 형식이 틀림 (문자열이 아니거나 2절 규칙 위반) | 아니오 |
| forbidden_topic | 비로그인이거나 관리자 권한이 없어진 사용자가 관리자 토픽을 구독 | 예 |
| not_found | 없는 실습실·PC. 구독은 남지 않는다 | 예 |

## 5. 순서

- 구독하면 서버는 먼저 알림 그룹에 들어간 뒤 스냅샷을 만든다. 스냅샷을 만드는 동안 생긴 변경은 스냅샷 **뒤에** 전달된다. 처음 구독할 때 스냅샷보다 먼저 그 토픽의 `pc`/`seat`가 오는 일은 없다.
- `pc`와 `seat`는 바뀐 필드만이 아니라 전체 상태를 담는다. 받은 것으로 해당 PC·좌석을 통째로 바꾸면 된다 (스냅샷과 같은 내용이 한 번 더 올 수 있다).
- PC는 `pc` 메시지의 `id`, 좌석은 `row`와 `col`로 찾는다.

## 6. 연결 종료

| close code | 의미 | 브라우저 동작 |
|---|---|---|
| 4401 | 로그인 세션 끝 (이 사용자가 로그아웃했거나 관리자 계정이 삭제됨, 또는 ping 때 관리자 권한이나 세션이 없어짐) | 다시 연결하지 않고 `/login`으로 |
| 1011 | 서버 처리 중 오류 | 백오프 후 재접속하고 구독을 다시 보낸다 |

그 밖의 끊김(네트워크, 서버 재시작)도 재접속 후 구독을 다시 보내면 스냅샷부터 다시 받는다. 서버는 연결 사이에 구독을 기억하지 않는다.

## 7. 비로그인에게 보이는 것

비로그인 연결은 `room:<id>:public`만 구독할 수 있고, 좌석의 `row, col, label, online`만 받는다. 호스트 이름, 사용자, 창 제목, 수치 같은 값은 공개 메시지에 들어가지 않는다. 공개 메시지는 서버가 따로 만들어 공개 그룹에만 보낸다 (관리자용 메시지를 연결마다 걸러내는 방식이 아니다).
