# 클라이언트 자동 업데이트 기능

## 개요

클라이언트는 시작 시 서버에서 최신 버전을 확인하고, 새 버전이 있을 경우 자동으로 다운로드하여 업데이트를 수행합니다.

---

## 아키텍처

### 클라이언트 흐름

```
클라이언트 시작
    ↓
check_for_updates() 호출 (main.py)
    ↓
GET /api/client/version 요청 (server)
    ↓
버전 비교
    ├─ 현재 = 최신: "최신 버전 사용 중" 로그
    └─ 현재 < 최신: "새 버전 있음" + download_url 로그
        ↓
        perform_update() 호출 (updater.py)
        ↓
        1. 새 EXE 다운로드 (임시 폴더)
        2. 업데이트 스크립트(.cmd) 생성
        3. 스크립트 실행 및 현재 프로세스 종료
        ↓
        [업데이트 스크립트]
        1. 서비스 중지 (net stop WCMS-Client)
        2. 파일 교체 (copy /Y)
        3. 서비스 시작 (net start WCMS-Client)
        4. 임시 파일 정리
```

### 서버 흐름

```
GitHub Actions 빌드 완료
    ↓
Release 생성
    ├─ 태그: client-vX.X.X
    ├─ 파일: WCMS-Client.exe
    └─ URL: https://github.com/Nekonic/WCMS/releases/download/client-vX.X.X/WCMS-Client.exe
    ↓
POST /api/client/version 호출 (GitHub Actions)
    ↓
client_versions 테이블에 저장
    ↓
클라이언트: 다음 체크 시 새 버전 감지 및 자동 업데이트
```

---

## 구현 상세

### 1. 클라이언트 (client/main.py)

```python
def check_for_updates():
    """서버에서 최신 버전 확인"""
    try:
        response = safe_request(f"{SERVER_URL}api/client/version", timeout=REQUEST_TIMEOUT, max_retries=2)
        if response and response.status_code == 200:
            data = response.json()
            latest_version = data.get('version', '1.0.0')

            if latest_version != __version__:
                logger.warning(f"새 버전이 있습니다! 현재: {__version__}, 최신: {latest_version}")
                download_url = data.get('download_url')
                if download_url:
                    logger.info(f"업데이트 시작: {download_url}")
                    perform_update(download_url, latest_version)
                else:
                    logger.info("다운로드 URL이 없어 업데이트를 건너뜁니다.")
            else:
                logger.info(f"최신 버전 사용 중: {__version__}")
    except Exception as e:
        logger.debug(f"버전 체크 실패 (무시): {e}")
```

### 2. 업데이터 모듈 (client/updater.py)

```python
def perform_update(download_url: str, version: str):
    """
    업데이트 프로세스 실행
    1. 새 버전 다운로드
    2. 배치 스크립트 생성
    3. 스크립트 실행 및 종료
    """
    # ... (생략) ...
    
    # 배치 스크립트 내용
    script_content = f"""@echo off
echo Waiting for service to stop...
timeout /t 5 /nobreak >nul

echo Stopping service {service_name}...
net stop {service_name}

echo Waiting for process to release lock...
timeout /t 3 /nobreak >nul

echo Replacing executable...
copy /Y "{new_exe_path}" "{target_exe_path}"
if %errorlevel% neq 0 (
    echo Failed to copy file. Retrying in 5 seconds...
    timeout /t 5 /nobreak >nul
    copy /Y "{new_exe_path}" "{target_exe_path}"
)

echo Starting service {service_name}...
net start {service_name}

echo Cleaning up...
del "{new_exe_path}"
del "%~f0"
"""
```

**특징:**
- 서비스 중지/시작 자동화
- 파일 잠금 해제 대기 (timeout)
- 실패 시 재시도 로직 포함
- 임시 파일 자동 정리

### 3. 서버 (server/api/client.py)

#### GET /api/client/version (클라이언트 조회용)

```python
@client_bp.route('/version', methods=['GET'])
def get_version():
    """클라이언트 최신 버전 확인"""
    # client_versions 테이블에서 최신 버전 조회
    # Released_at 기준 내림차순 정렬
```

**응답 형식:**
```json
{
  "status": "success",
  "version": "0.8.7",
  "download_url": "https://github.com/Nekonic/WCMS/releases/download/client-v0.8.7/WCMS-Client.exe",
  "changelog": "자동 업데이트 기능 추가",
  "released_at": "2026-02-18T12:00:00"
}
```

#### POST /api/client/version (관리자 전용)

```python
@admin_bp.route('/client/version', methods=['POST'])
@require_admin  # 관리자 세션 필수
def create_client_version():
    """클라이언트 버전 등록 (관리자 전용)"""
    # ...
```

---

## 사용 방법

### 관리자 페이지에서 버전 등록 (권장)

```
1. 웹 UI 접속 (http://localhost:5050)
2. 관리자 로그인
3. 좌측 메뉴 → "📦 클라이언트 버전" 클릭
4. 버전 정보 입력
   - 버전: 0.8.7
   - 다운로드 URL: https://github.com/Nekonic/WCMS/releases/download/client-v0.8.7/WCMS-Client.exe
   - 변경사항: (선택) 업데이트 내용
5. "등록" 버튼 클릭
```

### 사용자 업데이트

```
1. 클라이언트 서비스가 실행 중일 때
2. 서버에 새 버전이 등록되면
3. 클라이언트가 재시작되거나 주기적으로 체크할 때 (현재는 시작 시 체크)
4. 자동으로 다운로드 및 업데이트 수행
5. 서비스가 잠시 중지되었다가 새 버전으로 다시 시작됨
```

---

## 데이터베이스

### client_versions 테이블

```sql
CREATE TABLE client_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version VARCHAR(50) NOT NULL UNIQUE,
    download_url TEXT NOT NULL,
    changelog TEXT,
    released_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 문제 해결

### 업데이트 무한 루프

**원인:** 버전 비교 로직 오류 또는 다운로드 파일 손상
**해결:**
1. 서버의 최신 버전 정보 확인
2. 클라이언트 로그 확인 (`C:\ProgramData\WCMS\logs\client.log`)
3. 수동으로 서비스 중지 후 최신 버전 덮어쓰기

### 서비스 시작 실패

**원인:** 권한 문제 또는 파일 경로 오류
**해결:**
1. `sc query WCMS-Client`로 상태 확인
2. 이벤트 뷰어 로그 확인
3. `install.cmd`를 관리자 권한으로 다시 실행하여 서비스 재등록

---

**마지막 업데이트**: 2026-02-18  
**상태**: 정상 작동 ✅
