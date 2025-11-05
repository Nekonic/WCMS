# API 명세서 (API.md)

## 📍 기본 정보

- **Base URL**: `http://localhost:5050` (로컬), `http://<server-IP>:5050` (배포)
- **요청 형식**: JSON
- **응답 형식**: JSON
- **인증**: Session (웹), machine_id (클라이언트)

---

## 🔑 인증 방식

### 웹 관리자
- 로그인 후 `session['admin']`에 username 저장
- Cookie로 자동 관리

### 클라이언트
- `machine_id` (기기 고유 ID): MAC 주소 기반
- 서버에서 `pc_info.machine_id` 검증

---

## 📡 API 엔드포인트

### 1️⃣ 인증 (웹)

#### 로그인

POST /login

**요청 Body**:
```json
{
"username": "admin",
"password": "admin"
}
```
**응답 (200)**:
```json
리다이렉트: /
Set-Cookie: session=...
```

**응답 (400)**:
```json
{
"error": "아이디 또는 비밀번호가 올바르지 않습니다."
}
```

---

#### 로그아웃

POST /logout

**응답 (200)**:

리다이렉트: /

---

### 2️⃣ PC 정보 조회 (웹)

#### PC 목록 조회

GET /?room=1실습실
**파라미터**:
```
- `room` (선택): 실습실명 (기본값: "1실습실")
```

**응답 (200)**:
```
 <!-- index.html 렌더링 --> <!-- 해당 실습실의 모든 PC 카드 표시 --> 
```

---

#### PC 상세 정보 (API)
GET /api/pc/<pc_id>
**응답 (200)**:
```json
{
"id": 1,
"machine_id": "MACHINE-101",
"room_name": "1실습실",
"seat_number": 1,
"hostname": "PC-101",
"is_online": true,
"cpu_model": "Intel i5-10400",
"cpu_cores": 6,
"cpu_threads": 12,
"ram_total": 8192,
"ram_used": 4096,
"disk_info": "{"C:": {"total": 500, "used": 250, "type": "SSD"}}",
"os_edition": "Windows 10 Pro",
"os_version": "22H2",
"ip_address": "192.168.1.101",
"mac_address": "AA:BB:CC:DD:EE:01"
}
```
**응답 (404)**:
```json
{
"error": "PC not found"
}
```

---

### 3️⃣ PC 원격 제어 (웹 - 인증 필수)

#### 원격 종료
POST /api/pc/<pc_id>/shutdown

Content-Type: application/json

**요구사항**: 로그인 필수 (`session['admin']` 필요)

**응답 (200)**:
```json
{
"message": "PC 1 종료 명령 전송됨"
}
```
**응답 (401)**:
```json
{
"error": "Unauthorized"
}
```
---

#### 원격 재시작
POST /api/pc/<pc_id>/reboot

Content-Type: application/json

**요구사항**: 로그인 필수

**응답 (200)**:
```json
{
"message": "PC 1 재시작 명령 전송됨"
}
```

---

### 4️⃣ 클라이언트 API

#### 클라이언트 등록 (최초 1회)
POST /api/client/register
Content-Type: application/json
**요청 Body**:
```json
{
"machine_id": "MACHINE-101",
"hostname": "PC-101",
"room_name": "1실습실",
"seat_number": 1
}
```
**응답 (200)**:
```json
{
"status": "success",
"message": "등록 완료"
}
```
**응답 (500)**:
```json
{
"status": "error",
"message": "이미 등록된 PC입니다."
}
```

---

#### Heartbeat (상태 업데이트)

POST /api/client/heartbeat

Content-Type: application/json

**요청 Body** (10분마다 전송):
```json
{
"machine_id": "MACHINE-101",
"system_info": {
    "cpu_model": "Intel i5-10400",
    "cpu_cores": 6,
    "cpu_threads": 12,
    "cpu_usage": 45.2,
    "ram_total": 8192,
    "ram_used": 4096,
    "ram_usage_percent": 50.0,
    "ram_type": "DDR4",
    "disk_info": "{"C:": {"total": 500, "used": 250, "type": "SSD"}}",
    "os_edition": "Windows 10 Pro",
    "os_version": "22H2",
    "os_build": "19045",
    "os_activated": true,
    "ip_address": "192.168.1.101",
    "mac_address": "AA:BB:CC:DD:EE:01",
    "gpu_model": "NVIDIA GTX 1650",
    "gpu_vram": 4096,
    "current_user": "student01",
    "uptime": 3600
    }
}
```
**응답 (200)**:
```json
{
"status": "success",
"message": "Heartbeat received"
}
```
**응답 (404)**:
```json
{
"status": "error",
"message": "PC not registered"
}
```

---

#### 명령 확인 (폴링)
GET /api/client/command?machine_id=MACHINE-101

**쿼리 파라미터**:
- `machine_id` (필수): 기기 고유 ID

**응답 (200)** - 명령 있음:
```json
{
"command_id": 123,
"action": "shutdown",
"params": {
    "force": true
    }
}
```
**응답 (200)** - 명령 없음:
```json
{
"command": null
}
```

---

#### 명령 실행 결과 전송
POST /api/client/command/result

Content-Type: application/json

**요청 Body**:
```json
{
"machine_id": "MACHINE-101",
"command_id": 123,
"result": "success",
"message": "PC 정상 종료"
}
```

**응답 (200)**:
```json
{
"status": "success",
"message": "Result received"
}
```

---

### 5️⃣ 좌석 배치 관리 (관리자 전용)
#### 배치 맵 조회
GET /api/layout/map/<room_name>

**응답 (200)**:
```json
{
"rows": 4,
"cols": 10,
"seats": [
    {"room_name": "1실습실", "row": 0, "col": 0, "pc_id": 1},
    {"room_name": "1실습실", "row": 0, "col": 1, "pc_id": 2}
    ]
}
```

#### 배치 맵 저장 (드래그&드롭 후)
POST /api/layout/map/<room_name>

**요청 Body**:
```json
{
"rows": 4,
"cols": 10,
    "seats": [
    {"row": 0, "col": 0, "pc_id": 1},
    {"row": 0, "col": 1, "pc_id": 2}
    ]
}
```

**응답 (200)**:
```json
{
"status": "success",
"message": "배치 저장 완료"
}
```
undefined

---

## 📋 향후 추가 예정 API

### Phase 3: 명령 실행 확장
POST /api/pc/<pc_id>/execute
- CMD 명령어 실행
- 프로세스 강제 종료
- 파일 전송

---

### Phase 4: 관리 기능
POST /api/pc/<pc_id>/install
POST /api/pc/<pc_id>/send-file
POST /api/pc/<pc_id>/get-logs

---

## 🧪 테스트 방법

### cURL 예시

**heartbeat 전송**:
```bash
curl -X POST http://localhost:5050/api/client/heartbeat
-H "Content-Type: application/json"
-d '{
"machine_id": "TEST-001",
"system_info": {
    "cpu_model": "Intel i5",
    "cpu_usage": 45.2,
    "ram_total": 8192,
    "ram_used": 4096,
    "os_edition": "Windows 10 Pro"
    }
}'
```
**명령 확인**:
```bash
curl http://localhost:5050/api/client/command?machine_id=TEST-001
```

---

## 📊 상태 코드

| 코드 | 의미 | 설명 |
|------|------|------|
| 200 | OK | 요청 성공 |
| 400 | Bad Request | 요청 형식 오류 |
| 401 | Unauthorized | 인증 필요 |
| 404 | Not Found | 리소스 없음 |
| 500 | Server Error | 서버 오류 |

---

## 🔄 요청/응답 흐름도

### 클라이언트 → 서버

1. 최초 등록 (1회)
    - POST /api/client/register
2. 10분마다 (무한 반복)
    - POST /api/client/heartbeat
3. 5초마다 명령 확인 (무한 반복)
    - GET /api/client/command
4. 명령 실행 후
    - POST /api/client/command/result

### 웹 관리자 → 서버 → 클라이언트
1. 관리자: POST /api/pc/<id>/shutdown
2. 서버: 명령 큐에 저장
3. 클라이언트: GET /api/client/command (5초 폴링)
4. 클라이언트: 명령 실행 (예: shutdown /s /t 0)
5. 클라이언트: POST /api/client/command/result
6. 서버: 결과 저장
7. 웹: 결과 확인 가능


---

## 💡 주의사항

1. **heartbeat 주기**: 10분 (600초)
   - 너무 짧으면 네트워크 부하 증가
   - 너무 길면 PC 상태 업데이트 지연

2. **명령 폴링**: 5초
   - 명령 실행까지 최대 5초 지연
   - 네트워크 안정성 권장

3. **타임아웃**: 명령 실행 후 결과가 없으면 서버에서 자동 실패 처리 (향후 구현)

4. **재연결 로직**: 네트워크 끊김 시 클라이언트가 자동 재연결 (향후 구현)

---