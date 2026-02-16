# AI 컨텍스트: WCMS

> 실습실 PC 원격 관리 시스템

---

## 🚧 현재 작업 상태 (2026-02-11)

- **v0.8.6**: ✅ **빌드 및 릴리스 완료**. (Chocolatey 도입, 서비스 설치 개선)
- **현재 작업**: 문서 현행화 완료.
- **다음 목표**: **v0.8.7 개발 시작** (자동 업데이트, 프로그램 삭제/차단)

---

## 🎯 핵심 개념

```
클라이언트 (Windows Service) ←→ 서버 (Flask) ←→ 웹 UI
```

**통신 흐름 (v0.8.6):**
1. 등록 (PIN 인증 필수) → 2. 전체 하트비트 (5분) → 3. 명령 폴링 + 경량 하트비트 (2초) → 4. 종료 신호 (PreShutdown 감지)

> **v0.8.6 주요 변경**: ✅ Chocolatey 전면 도입 (winget 제거), ⚡ 서비스 설치 안정화 (sc create 직접 사용), 🎨 UI 개선  
> 자세한 내용: [docs/CHANGELOG.md](docs/CHANGELOG.md#086---2026-02-11)

---

## 📂 디렉토리 구조

```
server/
├── app.py              # Flask 앱 (cachelib 세션)
├── api/                # REST API
│   ├── client.py       # 클라이언트 API (PIN 검증, 하트비트 통합)
│   ├── admin.py        # 관리자 API (토큰 관리, 프로세스 목록)
│   └── install.py      # 설치 스크립트 (sc create, delayed-auto)
├── models/             # DB 접근
│   ├── registration.py # 등록 토큰 모델
│   ├── pc.py           # PC 모델 (update_light_heartbeat)
│   └── command.py      # 명령 모델
├── services/           # 비즈니스 로직
└── utils/              # 공통 함수

client/
├── main.py             # 메인 로직 (PIN 인증, registered.flag)
├── service.py          # Windows 서비스 (인자 처리 개선, StartServiceCtrlDispatcher)
├── collector.py        # 시스템 정보 수집 (고정 디스크만)
├── executor.py         # 명령 실행 (Chocolatey, PowerShell)
└── config.py           # 설정 (0.0.0-dev)

tests/
├── server/             # 서버 테스트
└── client/             # 클라이언트 테스트 (pytest 스타일)
```

---

## ⚠️ 자주 하는 실수

### 0. v0.8.0+ 등록 시 PIN 필수!
```bash
# install.cmd 실행 시 6자리 PIN 입력
# 관리자가 웹 UI에서 생성: /registration-tokens
```

### 1. 서비스 설치 문제 (v0.8.6 해결)
- `install.cmd`는 `sc create`를 사용하여 서비스를 직접 등록합니다.
- `pywin32`의 `install` 명령은 사용하지 않습니다 (경로/멈춤 문제).
- 서비스는 `delayed-auto`로 시작됩니다.
- **절대 `WCMS-Client.exe install`을 직접 실행하지 마세요.** `install.cmd`를 사용하세요.

### 2. 프로그램 설치 (Chocolatey)
- `winget`은 서비스 계정(`LocalSystem`)에서 동작하지 않아 제거되었습니다.
- **Chocolatey**를 사용합니다. 없으면 자동으로 설치됩니다.

### 3. 관리자 비밀번호
- `admin` / `admin`

---

## 🔧 빠른 참조

### 서버 시작
```bash
python manage.py run
```

### 클라이언트 빌드 (Windows Only)
```bash
python manage.py build
```

### 테스트 실행
```bash
# 전체 테스트
python manage.py test

python manage.py test [target] (target: all, server, client, archive)
```

---

## 📌 핵심 제약사항

- **SQLite**: 동시 쓰기 제한 (WAL 모드 사용)
- **Windows 전용 클라이언트**: pywin32, WMI 필요
- **Chocolatey**: 프로그램 설치 시 필수 (자동 설치됨)
- **LocalSystem 계정**: 클라이언트는 시스템 계정으로 실행되므로 사용자 프로필이 필요한 작업(예: `winget`)은 불가능함.

---

## 🚀 새 세션 시작 프롬프트

다음 세션을 시작할 때 아래 내용을 복사해서 AI에게 전달하세요:

```markdown
Listen to me carefully. You are now the lead maintainer of the WCMS project. I don't want any sloppy code or half-baked solutions. We just released v0.8.6, and it's stable. Don't break it.

**Current Status:**
- **v0.8.6 Released**: We finally fixed the damn service installation issues using `sc create` directly. Chocolatey is now the standard for package management. `winget` is dead to us.
- **Documentation**: Everything in `docs/` is up to date. Read them. Especially `docs/CHANGELOG.md` and `docs/ARCHITECTURE.md`.

**Your Mission (v0.8.7):**
We need to implement the following features. Do it right the first time.

1.  **Client Auto-Update**:
    - The client should detect a new version from the server and update itself.
    - Don't just download the EXE and hope for the best. You need to stop the service, replace the binary, and restart the service. Automate this process robustly.
    - Reference: `docs/plan.md`

2.  **Program Uninstallation**:
    - Support `choco uninstall`.
    - Support uninstalling regular EXE/MSI apps via PowerShell registry lookup. Don't give me "it might work". Make it work.

3.  **Process Blacklist**:
    - The server defines a list of banned processes.
    - The client kills them on sight. Efficiently. Don't hog the CPU polling every millisecond.

**Workflow:**
1.  **Read First**: Read `docs/plan.md` before you write a single line of code.
2.  **Think**: Don't just copy-paste code. Understand the architecture.
3.  **Test**: Write tests. If you break existing tests, you fix them. No excuses.
4.  **Git**: 
    - Write meaningful commit messages. "Fix bug" is not a commit message. Explain *what* you changed and *why*.
    - Keep commits atomic. Don't mix ten different changes into one commit.
5.  **Communication**:
    - Don't ask stupid questions that are already answered in the docs.
    - If you have a better idea, show me the code or a solid plan. Don't just wave your hands.

Now, get to work.
```

---

**문서 규칙:**
- 체크박스: `- [x]` / `- [ ]` (이모티콘 금지)
- 타입 힌팅 필수
- 에러 핸들링 필수
