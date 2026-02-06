# AI 컨텍스트: WCMS

> 실습실 PC 원격 관리 시스템

---

## 🎯 핵심 개념

```
클라이언트 (Windows Service) ←→ 서버 (Flask) ←→ 웹 UI
```

**통신 흐름:**
1. 등록 → 2. 하트비트 (5분) → 3. 명령 폴링 (10초) → 4. 종료 신호

---

## 📂 디렉토리 구조

```
server/
├── app.py              # Flask 앱
├── api/                # REST API
│   ├── client.py       # 클라이언트 API
│   ├── admin.py        # 관리자 API
│   └── install.py      # 설치 스크립트 [NEW]
├── models/             # DB 접근
├── services/           # 비즈니스 로직
└── utils/              # 공통 함수

client/
├── main.py             # 메인 로직
├── service.py          # Windows 서비스
├── collector.py        # 시스템 정보 수집
├── executor.py         # 명령 실행
└── config.py           # 설정 (환경변수)
```

---

## ⚠️ 자주 하는 실수

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

### Git 커밋
```bash
feat(api): add endpoint
fix(client): resolve bug
docs: update README
```

---

## 📌 핵심 제약사항

- **SQLite**: 동시 쓰기 제한
- **Windows 전용 클라이언트**: pywin32, WMI 필요
- **Long-polling**: 최대 10초 지연
- **내부망 전용**: 클라이언트 API 무인증

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

