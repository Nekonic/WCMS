# 클라이언트 자동 업데이트 기능

## 개요

클라이언트는 시작 시 서버에서 최신 버전을 확인하고, 새 버전이 있을 경우 사용자에게 알립니다.

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
사용자 수동 다운로드 및 설치
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
클라이언트: 다음 체크 시 새 버전 감지
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
                logger.info(f"다운로드: {data.get('download_url', 'GitHub Release 확인')}")
                if data.get('changelog'):
                    logger.info(f"변경사항: {data.get('changelog')}")
            else:
                logger.info(f"최신 버전 사용 중: {__version__}")
    except Exception as e:
        logger.debug(f"버전 체크 실패 (무시): {e}")
```

**특징:**
- 서버 응답 실패 시에도 클라이언트는 계속 작동
- 로그에만 기록되고 사용자에게 강제하지 않음
- 네트워크 재시도 로직 포함 (max_retries=2)

### 2. 서버 (server/api/client.py)

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
  "version": "0.7.0",
  "download_url": "https://github.com/Nekonic/WCMS/releases/download/client-v0.7.0/WCMS-Client.exe",
  "changelog": "자동 빌드 - v0.7.0 릴리스",
  "released_at": "2025-12-30T12:00:00"
}
```

#### POST /api/client/version (GitHub Actions 업데이트용)

```python
@client_bp.route('/version', methods=['POST'])
def update_version():
    """버전 정보 업데이트 (GitHub Actions에서 호출)"""
    # client_versions 테이블에 새 버전 삽입
    # 자동으로 released_at에 현재 시간 기록
```

**요청 형식:**
```json
{
  "version": "0.7.0",
  "download_url": "https://github.com/Nekonic/WCMS/releases/download/client-v0.7.0/WCMS-Client.exe",
  "changelog": "자동 빌드 - v0.7.0 릴리스"
}
```

### 3. GitHub Actions (.github/workflows/build_client.yml)

#### 버전 추출
```yaml
- name: Extract version from tag
  run: |
    $version = "0.7.0"  # client-v0.7.0 태그에서 추출
```

#### 버전 업데이트
```yaml
- name: Update version in main.py
  run: |
    __version__ = "0.7.0"  # main.py의 버전 문자열 자동 업데이트
```

#### 서버 알림
```yaml
- name: Notify server about new version
  run: |
    POST /api/client/version
    {
      "version": "0.7.0",
      "download_url": "https://github.com/Nekonic/WCMS/releases/download/client-v0.7.0/WCMS-Client.exe",
      "changelog": "자동 빌드 - v0.7.0 릴리스"
    }
```

---

## 사용 방법

### 새 버전 릴리스

```bash
# 1. 클라이언트 코드 수정 (필요시)
# 2. Git 태그 생성
git tag client-v0.7.0
git push origin client-v0.7.0

# 3. GitHub Actions 자동 실행
# - EXE 빌드
# - Release 생성
# - 서버에 버전 정보 저장
```

### 사용자 업데이트

```
1. 클라이언트 실행
2. 로그에서 "새 버전이 있습니다" 메시지 확인
3. 다운로드 링크에서 EXE 다운로드
4. 우클릭 → "관리자 권한으로 실행"
5. 자동으로 서비스 업데이트 및 재시작
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

**주의:** 각 버전은 한 번씩만 저장됨 (UNIQUE 제약)

---

## 설정

### GitHub Secrets (필수)

`.github/workflows/build_client.yml`에서 사용:

```
SERVER_URL         서버 API 주소 (예: http://localhost:5050)
UPDATE_TOKEN       인증 토큰 (선택사항)
```

**설정 방법:**
1. GitHub 레포지토리 → Settings
2. Secrets and variables → Actions
3. New repository secret 추가

### 환경 변수 (클라이언트)

`client/config.py`:
```python
SERVER_URL = os.getenv('WCMS_SERVER_URL', 'http://localhost:5050')
```

---

## 테스트

### 로컬 테스트

```bash
# 1. 서버 시작
cd server
uv run python app.py

# 2. 버전 정보 수동 추가 (SQLite)
sqlite3 db.sqlite3
INSERT INTO client_versions (version, download_url, changelog)
VALUES ('0.7.0', 'https://example.com/WCMS-Client.exe', 'Test version');

# 3. 클라이언트 실행
cd client
__version__ = "0.6.0"
uv run python main.py

# 4. 로그에서 "새 버전이 있습니다" 메시지 확인
```

### API 테스트

```bash
# 버전 조회
curl http://localhost:5050/api/client/version

# 버전 업데이트
curl -X POST http://localhost:5050/api/client/version \
  -H "Content-Type: application/json" \
  -d '{
    "version": "0.8.0",
    "download_url": "https://github.com/Nekonic/WCMS/releases/download/client-v0.8.0/WCMS-Client.exe",
    "changelog": "Test update"
  }'
```

---

## 문제 해결

### 로그에서 버전 체크 실패

**원인:** 서버가 응답하지 않음
**해결:**
1. 서버가 실행 중인지 확인
2. SERVER_URL 확인 (config.py)
3. 네트워크 연결 확인

### 새 버전이 감지되지 않음

**원인:** 데이터베이스에 버전 정보 없음
**해결:**
1. POST /api/client/version 요청 확인
2. client_versions 테이블 확인
3. GitHub Actions 로그 확인

### GitHub Actions 빌드 실패

**원인:** 의존성 설치 실패
**해결:**
1. 워크플로우 로그 확인
2. `uv sync --all-extras` 성공 확인
3. Python 3.9 설치 확인

---

## 향후 계획

- [ ] 자동 다운로드 및 설치 기능
- [ ] 업데이트 스케줄링
- [ ] 롤백 기능
- [ ] 베타 채널 지원
- [ ] 업데이트 알림 UI 추가

---

**마지막 업데이트**: 2025-12-30  
**상태**: 정상 작동 ✅

