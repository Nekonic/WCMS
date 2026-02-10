# AI 컨텍스트: WCMS

> 실습실 PC 원격 관리 시스템

---

## 🎯 핵심 개념

```
클라이언트 (Windows Service) ←→ 서버 (Flask) ←→ 웹 UI
```

**통신 흐름 (v0.8.0):**
1. 등록 (PIN 인증 필수) → 2. 전체 하트비트 (5분) → 3. 명령 폴링 + 경량 하트비트 (2초) → 4. 종료 신호

> **v0.8.0 주요 변경 완료**: ✅ PIN 인증 시스템, ⚡ 네트워크 최적화 (60% 대역폭 절감)  
> 자세한 내용: [docs/CHANGELOG.md](docs/CHANGELOG.md#080---2026-02-10)

---

## 📂 디렉토리 구조

```
server/
├── app.py              # Flask 앱
├── api/                # REST API
│   ├── client.py       # 클라이언트 API (PIN 검증, 하트비트 통합)
│   ├── admin.py        # 관리자 API (토큰 관리)
│   └── install.py      # 설치 스크립트 (PIN 프롬프트)
├── models/             # DB 접근
│   ├── registration.py # 등록 토큰 모델 [NEW v0.8.0]
│   ├── pc.py           # PC 모델
│   └── command.py      # 명령 모델
├── services/           # 비즈니스 로직
└── utils/              # 공통 함수

client/
├── main.py             # 메인 로직 (PIN 인증, 경량 하트비트)
├── service.py          # Windows 서비스
├── collector.py        # 시스템 정보 수집
├── executor.py         # 명령 실행
└── config.py           # 설정 (PIN 로드)

tests/
├── server/             # 서버 테스트 (37개)
│   ├── test_models_registration.py
│   ├── test_api_registration.py
│   ├── test_api_client_auth.py
│   └── test_api_heartbeat.py
└── conftest.py         # pytest 픽스처
```

---

## ⚠️ 자주 하는 실수

### 0. v0.8.0 등록 시 PIN 필수!
```bash
# install.cmd 실행 시 6자리 PIN 입력
# 관리자가 웹 UI에서 생성: /registration-tokens
```

### 1. Docker 수정 후 재빌드 안 함
```bash
docker compose up -d --build  # 코드 변경 후 필수!
```

### 2. 환경변수 무시
- ❌ 하드코딩: `db_path = "db/wcms.sqlite3"`
- ✅ 환경변수: `db_path = os.getenv('WCMS_DB_PATH', 'db/wcms.sqlite3')`

### 3. 관리자 비밀번호
- `admin` / `admin` (구버전 `admin123` 아님)

### 4. client_versions 테이블 비어있음
```bash
# DB에 버전 정보 없으면 install.cmd 실패
docker exec wcms-server sqlite3 /app/db/wcms.sqlite3 \
  "INSERT INTO client_versions (version, download_url) VALUES \
  ('0.6.0', 'https://github.com/Nekonic/WCMS/releases/download/client-v0.6.0/WCMS-Client.exe');"
```

---

## 🔧 빠른 참조

### 서버 시작
```bash
python manage.py run
```

### API 작업 패턴
```python
# 1. server/api/에 라우트 추가
@client_bp.route('/endpoint', methods=['POST'])
def endpoint():
    # 검증 → 서비스 호출 → 응답
    return jsonify({'status': 'success'})

# 2. server/services/에 로직 추가
# 3. docs/API.md 업데이트
```

### 테스트 작성 패턴
```python
# tests/server/test_models.py에 클래스 추가
class TestNewFeature:
    """새 기능 테스트"""
    
    def test_basic_functionality(self):
        """기본 기능 테스트"""
        # Given: 테스트 데이터 준비
        pc_id = PCModel.register(
            machine_id='TEST-001',
            hostname='test-pc',
            mac_address='AA:BB:CC:DD:EE:FF'
        )
        
        # When: 기능 실행
        result = PCModel.get_by_id(pc_id)
        
        # Then: 결과 검증
        assert result is not None
        assert result['hostname'] == 'test-pc'
```

### Git 커밋
```bash
feat(api): add endpoint
fix(client): resolve bug
docs: update README
```

### 테스트 실행
```bash
# 서버 모델 테스트
pytest tests/server/test_models.py -v

# 서버 API 테스트
pytest tests/server/test_api.py -v

# 모든 서버 테스트
pytest tests/server/ -v

# 클라이언트 테스트
pytest tests/client/ -v

# 전체 테스트 (서버 + 클라이언트)
pytest tests/ -v

# 특정 테스트만 실행
pytest tests/server/test_models.py::TestPCModel::test_register -v
```

---

## 📌 핵심 제약사항

- **SQLite**: 동시 쓰기 제한
- **Windows 전용 클라이언트**: pywin32, WMI 필요
- **Long-polling**: 최대 10초 지연

---

## 🚀 새 세션 시작

1. `AI_CONTEXT.md` 읽기 (이 파일)
2. `python manage.py run`
3. http://localhost:5050 접속
4. 필요한 문서만 참고 (API.md, ARCHITECTURE.md)

---

**문서 규칙:**
- 체크박스: `- [x]` / `- [ ]` (이모티콘 금지)
- 타입 힌팅 필수
- 에러 핸들링 필수

