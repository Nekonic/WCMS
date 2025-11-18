# WCMS 테스트 가이드

이 문서는 WCMS(Woosuk Computer Management System)의 기능을 테스트하는 방법을 설명합니다.

## 📋 목차

1. [테스트 환경 준비](#테스트-환경-준비)
2. [서버 테스트](#서버-테스트)
3. [클라이언트 테스트](#클라이언트-테스트)
4. [통합 테스트](#통합-테스트)
5. [일괄 명령 테스트](#일괄-명령-테스트)

---

## 테스트 환경 준비

### 1. 서버 실행

```bash
cd server
python app.py
```

서버가 `http://127.0.0.1:5050`에서 실행됩니다.

### 2. 관리자 계정 생성 (최초 1회)

```bash
cd server
python create_admin.py
```

기본 계정:
- **ID**: `admin`
- **PW**: `admin`

### 3. 클라이언트 실행 (Windows PC)

```bash
cd client
python main.py
```

또는 빌드된 실행 파일 사용:

```bash
client\build\main\main.exe
```

---

## 서버 테스트

### 웹 API 통합 테스트

서버의 주요 API 엔드포인트를 테스트합니다.

```bash
cd server
python test_web_access.py
```

**테스트 항목:**
- ✅ 대시보드 접근
- ✅ 관리자 로그인
- ✅ PC 목록 조회
- ✅ 좌석 배치 조회
- ✅ 클라이언트 등록
- ✅ 하트비트 전송
- ✅ 명령 폴링

**예상 출력:**

```
======================================================================
WCMS API 통합 테스트
======================================================================

--- 1. Dashboard Access (GET /) ---
✓ 대시보드 접근 성공 (Status: 200)

--- 2. Admin Login (POST /login) ---
✓ 로그인 성공

--- 3. PC List (GET /api/pcs) ---
✓ PC 목록 조회 성공 (총 1대)

...

전체: 5/5 테스트 성공
모든 테스트가 성공했습니다! 🎉
```

---

## 클라이언트 테스트

### 1. 정보 수집 테스트

클라이언트가 시스템 정보를 올바르게 수집하는지 확인합니다.

```python
from collector import collect_static_info, collect_dynamic_info

# 정적 정보 (CPU, RAM, Disk 등)
static_info = collect_static_info()
print(static_info)

# 동적 정보 (CPU 사용률, 프로세스 등)
dynamic_info = collect_dynamic_info()
print(dynamic_info)
```

### 2. 명령 실행 테스트

```python
from executor import CommandExecutor

# CMD 명령 실행
result = CommandExecutor.execute('hostname')
print(result)

# winget 버전 확인
result = CommandExecutor.execute('winget --version')
print(result)

# 파일 다운로드
result = CommandExecutor.download_file(
    'https://www.google.com/robots.txt',
    'C:\\temp\\test.txt'
)
print(result)
```

### 3. 계정 관리 테스트 (관리자 권한 필요)

```python
from executor import CommandExecutor

# 계정 생성
result = CommandExecutor.manage_account(
    'create', 'testuser', 'TestPass123!'
)
print(result)

# 비밀번호 변경
result = CommandExecutor.manage_account(
    'change_password', 'testuser', 'NewPass456!'
)
print(result)

# 계정 삭제
result = CommandExecutor.manage_account(
    'delete', 'testuser'
)
print(result)
```

---

## 통합 테스트

서버와 클라이언트 간의 전체 통신 흐름을 테스트합니다.

```bash
python test_integration.py
```

**테스트 시나리오:**
1. 클라이언트 등록
2. 하트비트 전송
3. 명령 전송 및 실행
4. 명령 결과 보고

**예상 출력:**

```
[Step 1] 클라이언트 등록 테스트
✓ 등록 API 응답 성공

[Step 2] 하트비트 테스트
✓ 하트비트 전송 성공

[Step 3] 명령 실행 테스트
✓ 명령 전송 성공
✓ 명령 실행 완료

전체: 3/3 테스트 통과
```

---

## 일괄 명령 테스트

여러 PC에 동시에 명령을 전송하는 기능을 테스트합니다.

```bash
python test_bulk_commands.py
```

**전제 조건:**
- 서버가 `http://127.0.0.1:5050`에서 실행 중
- 최소 1대 이상의 클라이언트가 온라인 상태

**테스트 항목:**
1. ✅ 일괄 CMD 명령 실행
2. ✅ 일괄 winget 검색
3. ✅ 일괄 파일 다운로드
4. ✅ 일괄 계정 관리 (테스트 모드)

**예상 출력:**

```
======================================================================
WCMS 일괄 명령 테스트
======================================================================

======================================================================
관리자 로그인
======================================================================
✓ 관리자 로그인 성공

======================================================================
온라인 PC 조회
======================================================================
ℹ 총 3대 PC 중 2대 온라인
  - PC#1: DESKTOP-ABC123 (1번 좌석)
  - PC#2: DESKTOP-XYZ789 (2번 좌석)

======================================================================
테스트 1: 일괄 CMD 명령 실행
======================================================================
ℹ 2대의 PC에 'hostname' 명령 전송
✓ 명령 전송 완료: 2대 성공, 0대 실패

...

======================================================================
테스트 결과 요약
======================================================================
✓ CMD 명령: PASS
✓ winget 검색: PASS
✓ 파일 다운로드: PASS
✓ 계정 관리: PASS

======================================================================
전체: 4/4 테스트 통과
======================================================================

✓ 모든 테스트가 성공했습니다! 🎉
```

---

## 웹 UI 테스트

### 1. 대시보드 접속

브라우저에서 `http://127.0.0.1:5050` 접속

### 2. 로그인

- ID: `admin`
- PW: `admin`

### 3. PC 상태 확인

- 실습실별 PC 목록 확인
- 좌석 배치도에서 PC 상태 확인
  - 🟢 녹색: 정상 (CPU < 75%)
  - 🟡 노란색: 경고 (CPU 75~90%)
  - 🔴 빨간색: 위험 (CPU > 90%)
  - ⚫ 회색: 오프라인

### 4. 일괄 명령 실행

1. **선택 모드** 버튼 클릭
2. PC를 **드래그** 또는 **클릭**하여 선택
3. 선택된 PC 패널에서 원하는 명령 버튼 클릭:
   - 💻 **CMD 실행**: 임의의 CMD 명령 실행
   - 📦 **프로그램 설치**: winget으로 프로그램 설치
   - 📥 **파일 다운로드**: URL에서 파일 다운로드
   - 👤 **계정 관리**: 계정 생성/삭제/비밀번호 변경
   - 🔌 **전원 관리**: 종료/재시작/로그아웃

### 5. 개별 PC 제어

1. PC 좌석을 **일반 클릭**
2. PC 상세 정보 모달에서 개별 명령 실행

### 6. 명령 테스트 페이지

`http://127.0.0.1:5050/command-test` 접속

- PC 선택
- 명령 유형 선택 (CMD / winget / 다운로드)
- 명령 실행 및 결과 확인

---

## 명령 실행 결과 확인

### 웹 UI에서 확인

(향후 구현 예정)

### 데이터베이스에서 확인

```bash
cd server
sqlite3 db.sqlite3

# 명령 실행 기록 조회
SELECT 
    id, 
    pc_id, 
    command_type, 
    status, 
    result,
    created_at, 
    completed_at
FROM pc_command
ORDER BY created_at DESC
LIMIT 10;
```

---

## 트러블슈팅

### 서버 연결 실패

**증상:**
```
Connection refused: [Errno 61]
```

**해결:**
1. 서버가 실행 중인지 확인
2. 포트 5050이 사용 가능한지 확인

### 클라이언트 등록 실패

**증상:**
```
등록 실패: 500 - 이미 등록된 PC입니다
```

**해결:**
- 정상 동작입니다. 클라이언트는 자동으로 하트비트를 시작합니다.

### 명령 실행 타임아웃

**증상:**
```
명령 실행 타임아웃 (30초 초과)
```

**해결:**
- `executor.py`의 `timeout` 값을 늘리세요
- 장시간 소요 명령(winget 설치 등)은 이미 300초로 설정됨

### winget 미설치 오류

**증상:**
```
오류: winget이 설치되어 있지 않습니다
```

**해결:**
- Windows 11 또는 최신 Windows 10 필요
- Microsoft Store에서 "앱 설치 관리자" 업데이트

---

## 성능 테스트

### 동시 접속 테스트

여러 클라이언트를 동시에 실행하여 서버 성능 테스트:

```bash
# Windows PC 1
python main.py

# Windows PC 2
python main.py

# Windows PC 3
python main.py
```

### 일괄 명령 부하 테스트

10대 이상의 PC에 동시에 명령을 전송하여 처리 성능 확인

---

## 보안 테스트

### 세션 확인

1. 로그아웃 후 API 직접 호출 시도
2. 401 Unauthorized 응답 확인

### SQL Injection 방지

- 모든 DB 쿼리에 파라미터 바인딩 사용 확인
- 사용자 입력값 검증 확인

---

## 자동화 테스트

### GitHub Actions (향후)

`.github/workflows/test.yml`:

```yaml
name: Test WCMS

on: [push, pull_request]

jobs:
  test:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.11
      - name: Install dependencies
        run: |
          pip install -r server/requirements.txt
          pip install -r client/requirements.txt
      - name: Run tests
        run: |
          python test_integration.py
```

---

## 테스트 체크리스트

### 서버
- [ ] 웹 대시보드 접근
- [ ] 관리자 로그인/로그아웃
- [ ] PC 목록 조회
- [ ] 좌석 배치 저장/조회
- [ ] 클라이언트 등록
- [ ] 하트비트 수신
- [ ] 명령 전송
- [ ] 명령 결과 수신

### 클라이언트
- [ ] 정적 정보 수집
- [ ] 동적 정보 수집
- [ ] 서버 등록
- [ ] 하트비트 전송
- [ ] 명령 폴링
- [ ] CMD 명령 실행
- [ ] winget 설치
- [ ] 파일 다운로드
- [ ] 계정 관리
- [ ] 명령 결과 보고

### 일괄 명령
- [ ] 여러 PC 선택 (드래그)
- [ ] 체크박스 표시
- [ ] 일괄 CMD 실행
- [ ] 일괄 프로그램 설치
- [ ] 일괄 파일 다운로드
- [ ] 일괄 계정 관리
- [ ] 일괄 전원 관리

---

## 참고 자료

- [API 명세서](API.md)
- [개발 가이드](DEVELOP.md)
- [프로젝트 상태](STATUS.md)

---

**Last Updated**: 2024.11.18

