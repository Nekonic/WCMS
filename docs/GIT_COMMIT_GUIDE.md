# Git Commit 가이드

리팩토링 작업을 Git에 커밋하기 위한 가이드입니다.

---

## 커밋 전 확인

```bash
# 변경된 파일 확인
git status

# 변경 내역 확인
git diff README.md
```

---

## 커밋 방법

### 옵션 1: 한 번에 커밋 (권장)

```bash
# 모든 새 파일 추가
git add .

# 커밋 메시지 작성
git commit -m "refactor: 프로젝트 리팩토링 시작 - Phase 1-2 기반 모듈 생성

- 리팩토링 계획 및 아키텍처 문서 작성
- 서버 설정 및 유틸리티 모듈 생성 (config, utils)
- 클라이언트 설정 및 유틸리티 모듈 생성
- 변경 이력 관리 시스템 구축 (CHANGELOG.md)

생성된 파일:
- 문서: ARCHITECTURE.md, REFACTORING.md, CHANGELOG.md 등 6개
- 서버: config.py, utils/* (5개)
- 클라이언트: config.py, utils.py, data/system_processes.json (3개)

참고: REFACTORING.md 및 IMPLEMENTATION_REPORT.md 참조"
```

### 옵션 2: 단계별 커밋

#### 1단계: 문서 커밋
```bash
git add ARCHITECTURE.md REFACTORING.md CHANGELOG.md REFACTORING_PROGRESS.md IMPLEMENTATION_REPORT.md QUICK_REFERENCE.md
git commit -m "docs: 리팩토링 계획 및 아키텍처 문서 작성

- ARCHITECTURE.md: 시스템 아키텍처 전체 설명
- REFACTORING.md: 5개 Phase 리팩토링 계획
- CHANGELOG.md: Keep a Changelog 형식 도입
- REFACTORING_PROGRESS.md: 진행 상황 추적
- IMPLEMENTATION_REPORT.md: 구현 완료 보고서
- QUICK_REFERENCE.md: 빠른 참조 가이드"
```

#### 2단계: 서버 모듈 커밋
```bash
git add server/config.py server/utils/
git commit -m "refactor(server): 설정 및 유틸리티 모듈 생성

- config.py: 환경변수 기반 설정 관리
- utils/database.py: DatabaseManager 클래스 및 쿼리 헬퍼
- utils/auth.py: 인증 및 권한 관리
- utils/validators.py: 입력 검증 함수 (보안 강화)
- utils/__init__.py: 패키지 초기화

타입 힌팅 추가, 재사용 가능한 구조"
```

#### 3단계: 클라이언트 모듈 커밋
```bash
git add client/config.py client/utils.py client/data/
git commit -m "refactor(client): 설정 및 유틸리티 모듈 생성

- config.py: 클라이언트 설정 중앙화
- utils.py: 네트워크 재시도, 유틸리티 함수
- data/system_processes.json: 시스템 프로세스 외부화

에러 핸들링 개선, 환경변수 지원"
```

#### 4단계: README 업데이트 커밋
```bash
git add README.md
git commit -m "docs: README 문서 섹션 개편

- 사용자/개발자 문서 구분
- 새 문서 링크 추가 (ARCHITECTURE, REFACTORING, CHANGELOG)"
```

---

## 푸시

```bash
# main 브랜치에 푸시
git push origin main

# 또는 새 브랜치 생성
git checkout -b refactor/phase1-foundation
git push origin refactor/phase1-foundation
```

---

## 태그 생성 (선택사항)

```bash
# 마일스톤 태그
git tag -a v0.6.0-refactor-start -m "리팩토링 시작: Phase 1-2 기반 모듈 생성"
git push origin v0.6.0-refactor-start
```

---

## 커밋 메시지 컨벤션

### 형식
```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type
- `feat`: 새 기능
- `fix`: 버그 수정
- `refactor`: 리팩토링
- `docs`: 문서 변경
- `style`: 코드 스타일 변경
- `test`: 테스트 추가/수정
- `chore`: 빌드/설정 변경

### Scope (선택사항)
- `server`: 서버 관련
- `client`: 클라이언트 관련
- `docs`: 문서 관련

### 예시
```bash
git commit -m "refactor(server): 데이터베이스 레이어 분리

- DatabaseManager 클래스 생성
- 연결 관리 및 쿼리 헬퍼 함수
- 타입 힌팅 추가

참고: #123"
```

---

## .gitignore 확인

다음 항목이 제외되어야 합니다:

```gitignore
# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
venv/
env/

# Database
*.sqlite3
*.db

# Logs
*.log
logs/

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db

# Build
dist/
build/
*.spec
```

---

## 마무리 체크리스트

- [ ] `git status`로 변경 파일 확인
- [ ] 불필요한 파일 제외 (`.pyc`, `__pycache__` 등)
- [ ] 커밋 메시지 작성
- [ ] 커밋 실행
- [ ] 원격 저장소에 푸시
- [ ] (선택) 태그 생성

---

**준비 완료!** 위 명령어를 실행하여 리팩토링 작업을 커밋하세요.

