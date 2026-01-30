# GitHub Copilot Instructions

> WCMS 프로젝트 AI 어시스턴트 규칙

---

## 🚫 절대 금지사항

### 1. 체크박스 이모티콘 사용 금지
```markdown
❌ 금지: ✅ ❌ ⏳ 🔥 🚀 ☑ ☒ 🔴 🟢
✅ 사용: - [x] 완료, - [ ] 미완료
```

### 2. 과도한 이모티콘 금지
- 본문에 장식용 이모티콘 남발 금지
- 섹션 헤더(`## 📚 문서`)에만 최소한으로 사용

### 3. 기타 금지
- 존재하지 않는 문서 참조 금지
- 하드코딩된 설정값 사용 금지 (환경변수 사용)
- 타입 힌팅 없는 새 함수 작성 금지

---

## ✅ 코딩 규칙

### Python
```python
# 타입 힌팅 필수
def get_pc(pc_id: int) -> Optional[Dict[str, Any]]:
    """PC 정보를 조회합니다.
    
    Args:
        pc_id: PC ID
        
    Returns:
        PC 정보 딕셔너리 또는 None
    """
    pass

# 네이밍: snake_case (함수/변수), PascalCase (클래스)
# 에러 핸들링 및 로깅 추가
# 환경변수 사용 (하드코딩 금지)
```

### 파일 구조
- **레이어 분리**: Model → Service → API
- **절대 임포트**: `from server.models import PCModel`
- **모듈화**: 관련 기능을 모듈로 분리

---

## 📝 문서 작성

### 체크박스 형식
```markdown
# ✅ 올바른 예시
- [x] 서버 구현 완료
- [ ] 클라이언트 테스트 필요
- [x] 문서 업데이트

## 상태
> **구현**: [x] 완료  
> **테스트**: [ ] 필요

# ❌ 잘못된 예시
- ✅ 서버 구현 완료
- ❌ 클라이언트 테스트 필요
- ⏳ 문서 업데이트 진행 중
```

### 문서 업데이트 규칙
코드 변경 시 다음 문서 함께 업데이트:
1. `docs/CHANGELOG.md` - 모든 변경사항 기록
2. `docs/API.md` - API 변경 시
3. `AI_CONTEXT.md` - 중요 의사결정 (ADR 섹션)

### 커밋 메시지
- 형식: `type(scope): message`
- 예: `feat(api): add shutdown endpoint`
- 상세: `docs/GIT_COMMIT_GUIDE.md` 참고

---

## 🗂️ 프로젝트 구조

### 새 세션 시작 시
1. `AI_CONTEXT.md` 읽기 (필수)
2. 관련 문서 확인 (`docs/` 디렉토리)
3. 최근 변경사항 확인 (`docs/CHANGELOG.md`)

### 주요 파일
```
server/
├── app.py              # Flask 앱 초기화
├── config.py           # 환경 설정
├── models/             # 데이터 접근 (Repository)
├── api/                # REST API (Blueprint)
├── services/           # 비즈니스 로직
└── utils/              # 공통 유틸리티

client/
├── main.py             # 메인 로직
├── service.py          # Windows 서비스
├── config.py           # 클라이언트 설정
└── collector.py        # 시스템 정보 수집

docs/
├── AI_CONTEXT.md       # AI 빠른 온보딩
├── ARCHITECTURE.md     # 시스템 아키텍처
├── API.md              # REST API 명세
└── CHANGELOG.md        # 변경 이력
```

---

## 💡 작업 패턴

### API 엔드포인트 추가
1. `server/api/client.py` 또는 `admin.py`에 라우트 추가
2. `server/services/`에 비즈니스 로직 추가
3. `server/models/`에 DB 접근 로직 추가 (필요 시)
4. `docs/API.md`에 문서 추가
5. `docs/CHANGELOG.md`에 기록

### 클라이언트 명령 추가
1. `client/executor.py`의 `execute()` 메서드에 case 추가
2. 핸들러 메서드 구현
3. 테스트 및 로깅 추가

---

## ⚙️ 제약사항

### 기술적 제약
- SQLite 사용 (동시 쓰기 제한, WAL 모드)
- Windows 전용 클라이언트 (pywin32, WMI)
- Long-polling (10초 주기, 실시간성 제한)
- 내부 네트워크 전용 (클라이언트 API 인증 없음)

### 설계 원칙
- 모듈화 및 레이어 분리
- 클라이언트는 실패해도 계속 동작
- 모든 주요 동작 로깅
- 명령 타임아웃 기본 300초

---

**이 규칙을 엄격히 준수하세요.**
4. ✓ 기존 코딩 스타일 따르기
5. ✓ 에러 핸들링 및 로깅 추가

---

**모든 AI 에이전트는 이 규칙을 엄격히 준수해야 합니다.**
