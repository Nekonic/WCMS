# 빠른 참조 가이드 (Quick Reference)

> 새로 생성된 모듈 사용법 및 통합 관리 스크립트

---

## 통합 관리 스크립트 (manage.py)

프로젝트 루트에 있는 `manage.py`를 사용하여 서버 실행, 테스트, 의존성 관리를 통합적으로 수행할 수 있습니다.

```bash
# 서버 실행 (기본값)
python manage.py run

# 테스트 실행
python manage.py test

# 도움말
python manage.py help
```

이 스크립트는 자동으로 `uv` 설치 여부를 확인하고 의존성을 동기화합니다.

---

## 서버 모듈

### 설정 관리 (config.py)

```python
from config import get_config

# 환경에 맞는 설정 로드 (개발/프로덕션/테스트)
config = get_config()  # WCMS_ENV 환경변수 사용

# 또는 직접 지정
config = get_config('production')

# 설정 사용
app.secret_key = config.SECRET_KEY
db_path = config.DB_PATH
```

**환경변수 설정:**
```bash
# 개발 환경
export WCMS_ENV=development

# 프로덕션 환경
export WCMS_ENV=production
export WCMS_SECRET_KEY=your-production-secret
export WCMS_DB_PATH=/var/lib/wcms/db.sqlite3
```

---

### 데이터베이스 (utils/database.py)

```python
from utils import init_db_manager, get_db, execute_query

# 앱 초기화 시 (한 번만)
init_db_manager(config.DB_PATH, config.DB_TIMEOUT)

# 연결 가져오기
db = get_db()
cursor = db.execute('SELECT * FROM pc_info WHERE id=?', (pc_id,))

# 또는 헬퍼 함수 사용
pc = execute_query(
    'SELECT * FROM pc_info WHERE id=?',
    params=(pc_id,),
    fetch_one=True
)

pcs = execute_query(
    'SELECT * FROM pc_info WHERE room_name=?',
    params=(room,),
    fetch_all=True
)

# 커밋이 필요한 경우
lastrowid = execute_query(
    'INSERT INTO pc_info (machine_id, hostname) VALUES (?, ?)',
    params=(machine_id, hostname),
    commit=True
)
```

**Flask 앱에 통합:**
```python
from flask import Flask
from config import get_config
from utils import init_db_manager, close_db

app = Flask(__name__)
config = get_config()

# DB 매니저 초기화
init_db_manager(config.DB_PATH, config.DB_TIMEOUT)

# 요청 종료 시 DB 연결 닫기
@app.teardown_appcontext
def teardown_db(error):
    close_db(error)
```

---

### 인증 (utils/auth.py)

```python
from utils import hash_password, check_password, require_admin

# 비밀번호 해싱
hashed = hash_password('mypassword')

# 비밀번호 확인
if check_password('mypassword', hashed):
    print("인증 성공")

# 관리자 권한 필요한 라우트
@app.route('/api/admin/users')
@require_admin  # 세션에 'admin' 키 없으면 401
def admin_users():
    return jsonify({'users': [...]})
```

---

### 검증 (utils/validators.py)

```python
from utils import (
    validate_machine_id,
    validate_ip_address,
    sanitize_hostname,
    validate_command_type,
    sanitize_command_output
)

# Machine ID 검증 (12자리 16진수)
if not validate_machine_id(machine_id):
    return jsonify({'error': 'Invalid machine ID'}), 400

# IP 주소 검증
if not validate_ip_address(ip):
    return jsonify({'error': 'Invalid IP address'}), 400

# 호스트명 정제 (XSS 방지)
safe_hostname = sanitize_hostname(user_input)

# 명령 타입 검증
if not validate_command_type(cmd_type):
    return jsonify({'error': 'Invalid command type'}), 400

# 긴 출력 자르기
result = sanitize_command_output(long_output, max_length=5000)
```

---

## 클라이언트 모듈

### 설정 관리 (config.py)

```python
from config import (
    SERVER_URL,
    MACHINE_ID,
    HEARTBEAT_INTERVAL,
    COMMAND_POLL_INTERVAL,
    validate_config,
    print_config
)

# 설정 검증
try:
    validate_config()
except ValueError as e:
    logger.error(f"설정 오류: {e}")
    sys.exit(1)

# 디버깅용 설정 출력
if __name__ == '__main__':
    print_config()

# 설정 사용
response = requests.post(f"{SERVER_URL}api/client/register", ...)
time.sleep(HEARTBEAT_INTERVAL)
```

**환경변수 설정:**
```bash
# Windows
set WCMS_SERVER_URL=http://your-server.com:5050/
set WCMS_HEARTBEAT_INTERVAL=600

# Linux/Mac
export WCMS_SERVER_URL=http://your-server.com:5050/
export WCMS_HEARTBEAT_INTERVAL=600
```

---

### 유틸리티 (utils.py)

```python
from utils import (
    retry_on_network_error,
    safe_request,
    load_json_file,
    format_bytes,
    format_uptime
)

# 네트워크 재시도 데코레이터
@retry_on_network_error(max_retries=3, delay=5)
def send_heartbeat():
    response = requests.post(f"{SERVER_URL}api/client/heartbeat", ...)
    response.raise_for_status()
    return response.json()

# 안전한 HTTP 요청
response = safe_request(
    f"{SERVER_URL}api/client/command",
    method='GET',
    timeout=30,
    max_retries=3,
    params={'pc_id': pc_id}
)
if response:
    commands = response.json()

# JSON 파일 로드
system_processes = load_json_file(
    'data/system_processes.json',
    default=[]
)

# 바이트 포맷팅
print(format_bytes(1024 * 1024 * 1024))  # "1.00 GB"

# 업타임 포맷팅
print(format_uptime(86400 + 3600 + 900))  # "1일 1시간 15분"
```

---

### 시스템 프로세스 필터링

**Before:**
```python
# collector.py
WINDOWS_SYSTEM_PROCESSES = {
    'System', 'Registry', 'explorer.exe', ...  # 100+ 항목
}
```

**After:**
```python
# collector.py
from utils import load_json_file
import os

# JSON 파일에서 로드
SYSTEM_PROCESSES_FILE = os.path.join(
    os.path.dirname(__file__),
    'data',
    'system_processes.json'
)
WINDOWS_SYSTEM_PROCESSES = set(load_json_file(
    SYSTEM_PROCESSES_FILE,
    default=[]
))
```

---

## 마이그레이션 예시

### app.py 리팩토링 (일부)

**Before:**
```python
import os
import bcrypt
from flask import Flask, g

app = Flask(__name__)
app.secret_key = 'woosuk25'
DB_PATH = os.path.join(os.path.dirname(__file__), 'db.sqlite3')

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH, ...)
    return g.db

def require_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin'):
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function
```

**After:**
```python
from flask import Flask
from config import get_config
from utils import init_db_manager, close_db, require_admin

config = get_config()
app = Flask(__name__)
app.secret_key = config.SECRET_KEY

# DB 초기화
init_db_manager(config.DB_PATH, config.DB_TIMEOUT)

@app.teardown_appcontext
def teardown_db(error):
    close_db(error)

# require_admin은 utils에서 임포트해서 바로 사용
```

---

## 테스트

### 서버 모듈 테스트

```python
# tests/test_config.py
from server.config import get_config, TestConfig

def test_config():
    config = get_config('test')
    assert isinstance(config, TestConfig)
    assert config.TESTING is True
    assert config.DB_PATH == ':memory:'
```

### 클라이언트 모듈 테스트

```python
# tests/test_utils.py
from client.utils import format_bytes, format_uptime

def test_format_bytes():
    assert format_bytes(1024) == "1.00 KB"
    assert format_bytes(1024 ** 3) == "1.00 GB"

def test_format_uptime():
    assert "1일" in format_uptime(86400)
    assert "1시간" in format_uptime(3600)
```

---

## 체크리스트

### 서버 마이그레이션
- [ ] config.py 임포트 및 설정 적용
- [ ] get_db() → utils.get_db() 변경
- [ ] require_admin 데코레이터 utils에서 임포트
- [ ] 입력 검증 함수 추가 (validators 사용)
- [ ] 하드코딩된 설정 제거

### 클라이언트 마이그레이션
- [ ] config.py 임포트 및 설정 사용
- [ ] 네트워크 요청에 safe_request() 사용
- [ ] system_processes.json 파일 사용
- [ ] 에러 핸들링 개선 (utils 활용)
- [ ] 하드코딩된 설정 제거

---

## 문제 해결

### Import 오류
```python
# 오류: ModuleNotFoundError: No module named 'utils'
# 해결: 현재 디렉토리가 PYTHONPATH에 있는지 확인

# 서버
cd /path/to/WCMS/server
python app.py

# 클라이언트
cd /path/to/WCMS/client
python main.py
```

### 설정 오류
```python
# 오류: ValueError: 프로덕션 환경에서는 WCMS_SECRET_KEY 필요
# 해결: 환경변수 설정

export WCMS_ENV=production
export WCMS_SECRET_KEY=your-secure-secret-key
```

---

## 추가 리소스

- **REFACTORING.md**: 전체 리팩토링 계획
- **ARCHITECTURE.md**: 시스템 아키텍처
- **IMPLEMENTATION_REPORT.md**: 구현 완료 보고서
- **REFACTORING_PROGRESS.md**: 진행 상황 추적

---

**마지막 업데이트**: 2025-12-30  
**버전**: 1.1
