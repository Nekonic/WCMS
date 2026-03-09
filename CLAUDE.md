# CLAUDE.md — WCMS

> 실습실 PC 원격 관리 시스템 (Woosuk Computer Management System)
> 작업 전 반드시 이 파일을 읽을 것.

---

## 절대 금지 사항

**커밋/푸시**: 사용자가 명시적으로 "커밋해", "push해" 라고 말하기 전까지 `git commit`, `git push` 등 일체의 git 쓰기 명령 실행 금지. 코드 수정 완료 후 반드시 사용자 확인을 기다릴 것.

**이모티콘**: 문서, 코드, 주석 어디에도 이모티콘/이모지 사용 금지.

**인라인 CSS**: `style="..."` 속성 추가 금지. `server/static/css/` 클래스 사용.

**인라인 JS**: `<script>` 인라인 금지. `server/static/js/` 파일로 분리. 예외: Jinja2 전역 변수 초기화 블록.

**pip 직접 실행**: `pip install` 금지. `uv add` / `uv sync` / `uv run python ...` 사용.

**winget**: 클라이언트 프로그램 설치에 사용 금지 (LocalSystem 계정 미지원). Chocolatey 사용.

---

## 프로젝트 구조

```
WCMS/
├── api/          # TypeScript + Hono API 서버 (v0.10.0~)
├── server/       # Flask 서버 (v0.9.x, 레거시)
├── client/       # Python 클라이언트 (Windows 서비스)
├── db/           # SQLite DB 파일
├── docs/         # plan.md, CHANGELOG.md
├── tests/        # pytest (server, client)
└── manage.py     # 통합 관리 스크립트
```

### 현재 스택 (v0.10.0)

| 역할 | 기술 |
|------|------|
| API 서버 | TypeScript + Hono (`api/`) |
| 요청 검증 | Zod |
| DB | SQLite + Drizzle ORM |
| 프론트엔드 | Svelte (Phase 2 예정) |
| 클라이언트 | Python + PyInstaller, Windows 전용 |

---

## 빠른 참조

```bash
# API 서버 실행
cd api && npm run dev

# 테스트 (루트에서)
python manage.py test api      # vitest (Hono API)
python manage.py test server   # pytest (Flask 레거시)
python manage.py test all      # 전체

# 클라이언트 빌드 (Windows 전용)
python manage.py build

# DB 초기화
python manage.py init-db
```

**관리자 계정 (개발)**: `admin` / `admin`

**현재 작업**: `docs/plan.md` 참고

---

## 코딩 규칙

**체크박스**: `[-]` 완료 / `[ ]` 미완료. `[x]` 사용 금지.

**타입 힌팅**: 신규 함수에 필수 (TypeScript, Python 모두).

**요청하지 않은 것 추가 금지**: 기능, 추상화, 주석, docstring, 리팩토링 등 명시적 요청 없으면 추가하지 말 것.

**커밋 메시지 형식**:
- 영어 conventional commit (`feat:`, `fix:`, `refactor:` 등)
- 마지막 줄: `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>`

---

## Landmines (코드에서 추측 불가능한 제약)

- **Jinja2 → JS 변수 전달**: static JS 파일에서 Jinja2 사용 불가. `window.WCMS_*` 전역 변수 패턴만 허용.
- **서비스 설치**: `WCMS-Client.exe install` 직접 실행 금지. `install.cmd` 경유.
- **SQLite WAL 모드**: `journal_mode = WAL` 고정. 변경 금지.
- **세션**: HMAC-SHA256 서명 httpOnly 쿠키. 서버 사이드 세션 없음.