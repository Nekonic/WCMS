# 프로젝트 파일 구조 정리 계획

## 현재 상태 분석

### 디렉토리 구조
```
WCMS/
├── archive/              # 정상 작동 확인된 원본 코드
├── server/               # 리팩터링된 서버 코드
├── client/               # 클라이언트 코드
├── tests/                # 테스트 코드
├── docs/                 # 문서
├── flask_session/        # Flask 세션 임시 파일
├── .venv/                # 가상환경 (루트)
└── server/.venv/         # 가상환경 (server)
```

## 문제점 및 중복 사항

### 1. 중복 파일

#### DB 파일
- [ ] `archive/code/db.sqlite3` (4.16 MB) - 실제 운영 DB
- [ ] `server/db.sqlite3` (존재 여부 확인 필요) - 개발용 DB

#### 테스트 파일
- [ ] `archive/code/test_server.py` - archive 전용 기존 테스트
- [ ] `archive/code/test_archive_complete.py` - 새로 작성한 완전한 테스트
- [ ] `client/test_api.py` - 클라이언트 API 테스트
- [ ] `client/test_client.py` - 클라이언트 테스트
- [ ] `tests/client/test_client.py` - 중복?
- [ ] `tests/client/test_utils.py`
- [ ] `tests/server/test_integration.py` - 통합 테스트
- [ ] `tests/server/test_refactored_complete.py` - 새로 작성한 완전한 테스트
- [ ] `test_all.py` (루트) - 전체 테스트 실행기?

#### 문서 파일
- [ ] `README.md` (루트) - 메인 README
- [ ] `REFACTORING_BUG_FIX_REPORT.md` (루트) - 버그 수정 리포트
- [ ] `docs/REFACTORING.md` - 리팩터링 가이드
- [ ] `docs/REFACTORING_STATUS.md` - 리팩터링 상태
- [ ] `docs/PROJECT_STATUS.md` - 프로젝트 상태
- [ ] `docs/CHANGELOG.md` - 변경 이력
- [ ] `archive/docs/GUIDE_v2.0_legacy.md` - 레거시 가이드

#### 유틸리티 파일
- [ ] `server/clean_duplicates.py` - DB 중복 정리 스크립트
- [ ] `server/clean_duplicates.sql` - DB 중복 정리 SQL
- [ ] `code_quality.py` (루트) - 코드 품질 검사

#### 임시/불필요 파일
- [ ] `archive/code/tst.py` - 테스트용 임시 파일
- [ ] `flask_session/` - Flask 세션 임시 디렉토리
- [ ] `.DS_Store` - macOS 메타데이터
- [ ] `__pycache__/` - Python 캐시
- [ ] `.pytest_cache/` - pytest 캐시
- [ ] `wcms.egg-info/` - 패키지 메타데이터

### 2. 가상환경 중복
- [ ] `.venv/` (루트) - 사용되지 않는 듯
- [ ] `server/.venv/` - 실제 사용 중

### 3. 설정 파일 분산
- [ ] `pyproject.toml` (루트)
- [ ] `server/pyproject.toml` (존재 여부 확인)
- [ ] `client/pyproject.toml` (존재 여부 확인)

## 통폐합 계획

### Phase 1: 중복 제거

#### 1.1 임시 파일 삭제
```bash
# 삭제 대상
rm -f archive/code/tst.py
rm -rf flask_session/
rm -rf __pycache__/
rm -rf .pytest_cache/
rm -f .DS_Store
rm -rf wcms.egg-info/
```

#### 1.2 테스트 파일 정리
```
tests/
├── archive/                          # 신규
│   └── test_archive_complete.py      # 이동: archive/code/test_archive_complete.py
├── client/
│   ├── test_client.py                # 통합 (중복 확인 후)
│   └── test_utils.py
└── server/
    ├── test_api.py
    ├── test_integration.py
    ├── test_models.py
    └── test_complete.py              # 이름 변경: test_refactored_complete.py
```

**작업**:
- [ ] `archive/code/test_archive_complete.py` → `tests/archive/test_complete.py` 이동
- [ ] `archive/code/test_server.py` 삭제 (test_archive_complete.py가 대체)
- [ ] `client/test_*.py` 파일들을 `tests/client/`로 통합
- [ ] `test_all.py` 분석 후 필요시 `tests/run_all.py`로 이동 또는 삭제

#### 1.3 문서 정리
```
docs/
├── INDEX.md                          # 유지 (문서 인덱스)
├── GETTING_STARTED.md                # 유지
├── ARCHITECTURE.md                   # 유지
├── API.md                            # 유지
├── QUICK_REFERENCE.md                # 유지
├── GIT_COMMIT_GUIDE.md               # 유지
├── CLIENT_AUTO_UPDATE.md             # 유지
├── CHANGELOG.md                      # 유지
├── PROJECT_STATUS.md                 # 통합 대상
├── REFACTORING.md                    # 통합 대상
├── REFACTORING_STATUS.md             # 통합 대상
└── archive/                          # 신규
    └── LEGACY_GUIDE.md               # 이동: archive/docs/GUIDE_v2.0_legacy.md
```

**작업**:
- [ ] `docs/PROJECT_STATUS.md`, `docs/REFACTORING_STATUS.md` → `docs/CHANGELOG.md`에 통합
- [ ] `docs/REFACTORING.md` → `docs/ARCHITECTURE.md`에 통합
- [ ] `REFACTORING_BUG_FIX_REPORT.md` → `docs/CHANGELOG.md`에 요약 추가 후 삭제
- [ ] `archive/docs/GUIDE_v2.0_legacy.md` → `docs/archive/LEGACY_GUIDE.md` 이동

#### 1.4 DB 파일 정리
```
db/                                    # 신규 디렉토리
├── production.sqlite3                 # 이동: archive/code/db.sqlite3
└── .gitignore                         # *.sqlite3 추가
```

**작업**:
- [ ] 루트에 `db/` 디렉토리 생성
- [ ] `archive/code/db.sqlite3` → `db/production.sqlite3` 이동 (백업)
- [ ] `server/db.sqlite3` 삭제 (개발용, 언제든지 재생성 가능)
- [ ] `db/.gitignore` 생성하여 `*.sqlite3` 추가

#### 1.5 유틸리티 스크립트 정리
```
scripts/                               # 신규 디렉토리
├── clean_db_duplicates.py             # 이동: server/clean_duplicates.py
├── clean_db_duplicates.sql            # 이동: server/clean_duplicates.sql
└── check_code_quality.py              # 이동: code_quality.py
```

**작업**:
- [ ] 루트에 `scripts/` 디렉토리 생성
- [ ] 유틸리티 파일들을 `scripts/`로 이동

### Phase 2: 디렉토리 구조 최적화

#### 2.1 archive 디렉토리 최소화
```
archive/
├── README.md                          # 신규: archive 디렉토리 설명
└── v1.0/                              # 이름 변경: code → v1.0
    ├── app.py                         # 유지
    └── db_schema.sql                  # 신규: 스키마만 추출
```

**작업**:
- [ ] `archive/code/` → `archive/v1.0/` 이름 변경
- [ ] `archive/v1.0/db.sqlite3` 삭제 (db/production.sqlite3로 이동됨)
- [ ] `archive/README.md` 작성

#### 2.2 가상환경 정리
```
# 루트 가상환경 삭제
rm -rf .venv/

# server/.venv/ 유지 (실제 사용 중)
# client/.venv/ 확인 후 결정
```

**작업**:
- [ ] 루트 `.venv/` 삭제
- [ ] `client/.venv/` 존재 여부 확인 후 처리

### Phase 3: 최종 구조

```
WCMS/
├── .git/
├── .github/
├── .gitignore
├── LICENSE
├── README.md                          # 메인 README
├── manage.py                          # 통합 관리 스크립트
├── pyproject.toml                     # 루트 설정
├── uv.lock
│
├── archive/                           # 원본 코드 보관
│   ├── README.md
│   └── v1.0/
│       ├── app.py
│       └── db_schema.sql
│
├── client/                            # 클라이언트 코드
│   ├── .venv/                         # (선택)
│   ├── pyproject.toml
│   ├── main.py
│   ├── config.py
│   ├── collector.py
│   ├── executor.py
│   ├── service.py
│   └── utils.py
│
├── server/                            # 서버 코드
│   ├── .venv/
│   ├── pyproject.toml
│   ├── app.py
│   ├── config.py
│   ├── create_admin.py
│   ├── create_seats.py
│   ├── api/
│   ├── models/
│   ├── services/
│   ├── utils/
│   ├── templates/
│   └── migrations/
│       └── schema.sql
│
├── tests/                             # 모든 테스트 통합
│   ├── __init__.py
│   ├── conftest.py
│   ├── archive/
│   │   └── test_complete.py
│   ├── client/
│   │   ├── test_client.py
│   │   └── test_utils.py
│   └── server/
│       ├── test_api.py
│       ├── test_models.py
│       ├── test_integration.py
│       └── test_complete.py
│
├── docs/                              # 문서
│   ├── INDEX.md
│   ├── GETTING_STARTED.md
│   ├── ARCHITECTURE.md
│   ├── API.md
│   ├── QUICK_REFERENCE.md
│   ├── CHANGELOG.md
│   └── archive/
│       └── LEGACY_GUIDE.md
│
├── db/                                # DB 파일 (gitignore)
│   ├── .gitignore
│   └── production.sqlite3
│
└── scripts/                           # 유틸리티 스크립트
    ├── clean_db_duplicates.py
    ├── clean_db_duplicates.sql
    └── check_code_quality.py
```

## 삭제 대상 요약

### 즉시 삭제 가능
- [ ] `archive/code/tst.py` - 임시 테스트 파일
- [ ] `flask_session/` - Flask 세션 임시 디렉토리
- [ ] `__pycache__/` - Python 캐시
- [ ] `.pytest_cache/` - pytest 캐시
- [ ] `.DS_Store` - macOS 메타데이터
- [ ] `wcms.egg-info/` - 패키지 메타데이터
- [ ] `.venv/` (루트) - 사용하지 않는 가상환경
- [ ] `server/db.sqlite3` - 개발용 DB (재생성 가능)

### 통합 후 삭제
- [ ] `archive/code/test_server.py` → `tests/archive/test_complete.py`로 대체
- [ ] `REFACTORING_BUG_FIX_REPORT.md` → `docs/CHANGELOG.md`에 통합
- [ ] `docs/PROJECT_STATUS.md` → `docs/CHANGELOG.md`에 통합
- [ ] `docs/REFACTORING_STATUS.md` → `docs/CHANGELOG.md`에 통합
- [ ] `docs/REFACTORING.md` → `docs/ARCHITECTURE.md`에 통합
- [ ] `test_all.py` → 분석 후 결정

### 이동 대상
- [ ] `archive/code/` → `archive/v1.0/`
- [ ] `archive/code/test_archive_complete.py` → `tests/archive/test_complete.py`
- [ ] `archive/code/db.sqlite3` → `db/production.sqlite3`
- [ ] `archive/docs/GUIDE_v2.0_legacy.md` → `docs/archive/LEGACY_GUIDE.md`
- [ ] `client/test_*.py` → `tests/client/`
- [ ] `server/clean_duplicates.*` → `scripts/`
- [ ] `code_quality.py` → `scripts/check_code_quality.py`

## 실행 순서

1. **백업 생성**
   ```bash
   git add -A
   git commit -m "backup: 정리 전 백업"
   ```

2. **즉시 삭제 가능한 파일 제거**

3. **신규 디렉토리 생성**
   - `db/`
   - `scripts/`
   - `tests/archive/`
   - `docs/archive/`

4. **파일 이동**

5. **문서 통합**

6. **테스트 실행**
   ```bash
   python manage.py test all
   ```

7. **커밋**
   ```bash
   git add -A
   git commit -m "refactor: 프로젝트 구조 정리 및 통폐합"
   ```

## 예상 효과

- **디스크 공간 절약**: 약 10-20MB (중복 파일, 캐시 제거)
- **구조 명확화**: 명확한 디렉토리 분리
- **유지보수 향상**: 중복 제거로 관리 포인트 감소
- **문서 일관성**: 분산된 문서 통합
