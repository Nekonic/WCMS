# AI_CONTEXT: WCMS

> 실습실 PC 원격 관리 시스템 (Woosuk Computer Management System)
> 작업 전 반드시 이 파일을 읽을 것.

---

## Non-goals

- 크로스플랫폼 클라이언트 — pywin32, WMI 의존으로 Windows 전용 고정
- 외부 DB — SQLite 전용 (WAL 모드)
- 실시간 WebSocket — 2초 폴링으로 충분
- 과도한 추상화 — 현재 필요한 것만 구현

---

## Landmines (코드에서 추측 불가능한 제약)

**패키지 관리**: `pip` 직접 실행 금지. `uv add` / `uv sync` / `uv run python ...` 사용.

**클라이언트 프로그램 설치**: `winget` 금지. LocalSystem 계정에서 동작하지 않음. Chocolatey 사용.

**서비스 설치**: `WCMS-Client.exe install` 직접 실행 금지. `install.cmd` 사용.

**Jinja2 → JS 변수 전달**: static JS 파일에서 Jinja2 사용 불가. `window.WCMS_*` 전역 변수 패턴으로만 전달.
```html
<!-- base.html 또는 template의 inline <script> 블록에서만 -->
<script>window.WCMS_IS_ADMIN = {{ 'true' if session.get('username') else 'false' }};</script>
```

---

## 프로젝트 규칙 (관례와 다른 부분)

**체크박스**: `[-]` 완료 / `[ ]` 미완료. `[x]` 또는 이모티콘 금지 (문서, 코드, 주석 모두).

**인라인 CSS**: 금지. `server/static/css/` 클래스 사용. `style="..."` 속성 추가 금지.

**인라인 JS**: 금지. `server/static/js/` 파일로 분리. 예외: Jinja2 전역 변수 초기화 `<script>` 블록.

**커밋**:
- 항상 `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>` 포함
- 버전 완료 전 docs 커밋 금지 — 해당 버전 항목 전부 완료 후 한꺼번에 커밋
- 버전 커밋 형식: `release: v0.9.1` / `hotfix: v0.9.1`
- 상세: `docs/GIT_COMMIT_GUIDE.md`

**plan.md 관리 규칙**:
- 진행 중인 버전의 plan만 포함
- 완료된 버전은 plan.md에서 제거하고 `docs/CHANGELOG.md`에 기록

**코드**: 타입 힌팅 필수 (신규 함수). 요청하지 않은 기능·추상화·주석 추가 금지.

---

## 빠른 참조

```bash
# 서버 실행
python manage.py run

# 테스트
python manage.py test server
python manage.py test client

# 클라이언트 빌드 (Windows)
python manage.py build
```

**관리자 계정**: `admin` / `admin`

**현재 작업**: `docs/plan.md` 참고

---

## 권장 사항

- 패키지 관리: `uv add` / `uv sync` (`pip` 직접 사용 금지)
- 클라이언트 프로그램 설치: Chocolatey (`winget` 금지 — LocalSystem 계정 미지원)
- 서비스 설치: `install.cmd` 사용 (`WCMS-Client.exe install` 직접 실행 금지)
- 체크박스: `[-]` 완료 / `[ ]` 미완료 (`[x]`, `✅` 금지)
- 이모티콘: 문서, 코드, 주석 모두 사용 금지
- CSS: `server/static/css/` 클래스 사용 (인라인 `style="..."` 금지)
- 파일 편집: Write/Edit 도구 사용 (`sed`/`awk` 금지)
- 커밋: 항상 `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>` 포함
- 커밋 시점: 해당 버전 항목 전부 완료 후 한꺼번에 커밋
- 보안 분석: 요청 없으면 수행 금지 (문서화 요청 시 문서만 작성)