# WCMS 실시간 종료 감지 구현 (완료)

> **상태**: [x] 구현 완료  
> **완료 날짜**: 2025년 12월 (v0.7.0)  
> **검증 상태**: [ ] 테스트 필요

> **구현된 옵션**:
> 1. **감지 시점**: PreShutdown 이벤트 (안정적 시간 확보)
> 2. **전송 방식**: HTTP REST API (전송 확인 및 기존 로직 활용)
> 3. **감지 주기**: 보수적 모드 (기존 5분 유지, 서버 부하 최소화)

## 1. 개요 (Overview)
본 문서는 클라이언트 PC가 윈도우 종료 절차(정상 종료)에 진입했을 때, 이를 **PreShutdown** 이벤트로 감지하고 즉시 서버에 HTTP 요청을 보내 **Offline** 상태로 전환하는 기능의 구현을 설명합니다. 비정상 종료(랜선 단절 등)에 대한 감지는 서버 부하를 고려하여 기존의 긴 주기(보수적 모드)를 유지합니다.

---

## 2. 상세 구현 계획

### 2.1. Server Side (Flask)

#### A. API 엔드포인트 추가 (`server/api/client.py`)
클라이언트가 종료 직전에 호출할 전용 엔드포인트를 신설합니다.
- **URI**: `POST /api/client/shutdown`
- **Body**: `{"machine_id": "..."}`
- **동작**:
  1. `machine_id`로 PC 식별.
  2. 해당 PC의 `is_online` 상태를 즉시 `0` (False)으로 업데이트.
  3. `last_seen` 타임스탬프 갱신 (종료 시점 기록).

#### B. 서비스 로직 추가 (`server/services/pc_service.py`)
- **Method**: `set_offline_immediately(machine_id)`
- **쿼리**: `UPDATE pc_info SET is_online=0 WHERE machine_id=?`
- **특이사항**: 복잡한 비즈니스 로직 없이 DB 업데이트만 빠르게 수행하여 응답 속도 최적화.

---

### 2.2. Client Side (Windows Service & Python)

#### A. 종료 신호 전송 함수 구현 (`client/main.py`)
윈도우 종료 이벤트 핸들러에서 호출할 단발성 전송 함수를 작성합니다.
- **함수명**: `send_shutdown_signal()`
- **로직**:
  - `/api/client/shutdown`으로 POST 요청 전송.
  - **중요**: `timeout=2.0`초로 설정 (네트워크 지연 시 윈도우 종료를 방해하지 않기 위함).
  - 재시도(Retry) 로직 제외 (실패 시 어차피 종료되므로 무의미).

#### B. Windows Service 이벤트 핸들링 수정 (`client/service.py`)
`win32service` 모듈을 사용하여 **PreShutdown** 이벤트를 수신하도록 서비스를 구성합니다.

1. **서비스 수락 코드 추가**:
```python
self._svc_reg_class_ = win32service.SERVICE_WIN32_OWN_PROCESS
# PRESHUTDOWN 이벤트를 받겠다고 선언
self._svc_deps_ = [] # 기존 의존성 유지
# acceptedCodes에 SERVICE_ACCEPT_PRESHUTDOWN (0x100) 추가 필요
# 파이썬 win32serviceutil에서는 GetAcceptedControls() 오버라이드 권장
```

2. **핸들러 구현**:
* `SvcOtherEx` 메서드를 구현하여 `SERVICE_CONTROL_PRESHUTDOWN` 이벤트를 감지.
* 이벤트 수신 시:
1. 로깅: "PreShutdown received..."
2. `main.send_shutdown_signal()` 호출 (동기 실행).
3. `self.stop_event.set()`으로 메인 루프 종료 유도.





---

## 3. 구현 상태

### 완료된 작업

#### Step 1: Server 구현
1. [x] `server/services/pc_service.py`: `set_offline_immediately` 메서드 추가
2. [x] `server/api/client.py`: `/shutdown` 라우트 추가 및 서비스 메서드 연결
3. [ ] 서버 재시작 및 `curl`로 테스트

#### Step 2: Client 핵심 로직 구현
1. [x] `client/main.py`: `send_shutdown_signal` 함수 추가
2. [x] `client/config.py`: 타임아웃 상수(`SHUTDOWN_TIMEOUT = 2`) 정의

#### Step 3: Client Service 연동
1. [x] `client/service.py`: `win32service.SERVICE_ACCEPT_PRESHUTDOWN` 적용
2. [x] `SvcOtherEx` 핸들러에서 신호 전송 로직 연결

---

## 4. 테스트 가이드

운영 환경에서 다음 시나리오를 테스트하여 기능을 검증하세요.

### 테스트 1: 정상 부팅
**절차**: 클라이언트 PC 부팅 또는 서비스 시작  
**기대 결과**: 웹 UI에서 PC 상태가 `Online`으로 표시됨  
**확인 방법**: 서버 대시보드에서 해당 PC의 상태 확인

### 테스트 2: 정상 종료 (핵심)
**절차**:
1. 윈도우 시작 메뉴 → "시스템 종료" 클릭
2. 종료 진행 관찰

**기대 결과**:
- `C:\ProgramData\WCMS\logs\client.log`에 "PreShutdown received" 로그 기록
- `C:\ProgramData\WCMS\logs\client.log`에 "Shutdown signal sent" 로그 기록
- 서버 웹 UI에서 해당 PC가 **즉시** `Offline`으로 변경됨

**확인 방법**:
```cmd
# 로그 확인
type C:\ProgramData\WCMS\logs\client.log | findstr "shutdown"
```

### 테스트 3: 네트워크 단절 (예외 케이스)
**절차**:
1. PC에서 랜선 제거
2. 윈도우 시작 메뉴 → "시스템 종료" 클릭

**기대 결과**:
- 클라이언트 로그에 "Shutdown signal failed" 또는 타임아웃 오류 기록
- 윈도우는 정상적으로 종료됨 (행이 걸리지 않음)
- 서버는 약 5분 후 백그라운드 체커를 통해 PC를 `Offline`으로 전환

**확인 방법**:
- 종료 시간이 평소와 유사한지 확인 (2초 이상 지연되지 않음)
- 로그에 네트워크 오류가 기록되었는지 확인



---

## 5. 트러블슈팅

### 문제: 종료 신호가 서버에 도달하지 않음
**원인**:
- PreShutdown 이벤트가 발생하지 않음
- 네트워크 연결 문제
- 서버 API 엔드포인트 오류

**해결**:
1. 로그 확인: `C:\ProgramData\WCMS\logs\client.log`
2. 서비스가 PreShutdown을 수신하는지 확인:
   ```cmd
   sc query WCMSClient
   ```
3. 서버 API 테스트:
   ```bash
   curl -X POST http://your-server:5050/api/client/shutdown \
     -H "Content-Type: application/json" \
     -d '{"machine_id":"TEST-MACHINE-ID"}'
   ```

### 문제: 종료 시 행(Hang)이 발생함
**원인**: `send_shutdown_signal()`의 타임아웃이 너무 김

**해결**:
1. `client/config.py`에서 `SHUTDOWN_TIMEOUT` 값 확인 (기본값: 2초)
2. 필요 시 더 짧게 조정 (권장 범위: 1~3초)

### 문제: 로그에 "PreShutdown received"가 없음
**원인**: 서비스가 PreShutdown 이벤트를 수락하지 않음

**해결**:
1. `client/service.py`의 `GetAcceptedControls()` 메서드 확인
2. 클라이언트 재빌드 및 재설치 필요 가능성

---

## 6. 참고: 구현된 코드 위치

### 서버 (Flask)
- **API 엔드포인트**: `server/api/client.py` (93-107줄)
  - `POST /api/client/shutdown`
- **서비스 로직**: `server/services/pc_service.py` (57-76줄)
  - `PCService.set_offline_immediately(machine_id)`

### 클라이언트 (Windows Service)
- **종료 신호 전송**: `client/main.py` (131-147줄)
  - `send_shutdown_signal()`
- **PreShutdown 핸들러**: `client/service.py` (56-71줄)
  - `GetAcceptedControls()`: PreShutdown 이벤트 수락 선언
  - `SvcOtherEx()`: PreShutdown 이벤트 핸들링
- **설정**: `client/config.py`
  - `SHUTDOWN_TIMEOUT = 2` (타임아웃 설정)

---

## 7. 관련 문서
- [ARCHITECTURE.md](docs/ARCHITECTURE.md): 시스템 아키텍처
- [API.md](docs/API.md): API 명세서
- [CHANGELOG.md](docs/CHANGELOG.md): 버전 히스토리
