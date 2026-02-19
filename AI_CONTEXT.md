# AI 컨텍스트: WCMS

> 실습실 PC 원격 관리 시스템

---

## 🚧 현재 작업 상태 (2026-02-18)

- **v0.8.8**: ✅ **빌드 및 릴리스 완료**. (계정 생성 언어 설정, 토큰 삭제 버그 수정)
- **현재 작업**: 문서 현행화 완료.
- **다음 목표**: **v0.9.0 개발 시작** (보안 강화, 모니터링 개선)

---

## 🎯 핵심 개념

```
클라이언트 (Windows Service) ←→ 서버 (Flask) ←→ 웹 UI
```

**통신 흐름 (v0.8.8):**
1. 등록 (PIN 인증 필수) → 2. 전체 하트비트 (5분) → 3. 명령 폴링 + 경량 하트비트 (2초) → 4. 종료 신호 (PreShutdown 감지)

> **v0.8.8 주요 변경**: ✅ 계정 생성 시 언어 설정(RunOnce), ⚡ 토큰 삭제 버그 수정, 🎨 UI 개선 (키보드 설정 제거)  
> 자세한 내용: [docs/CHANGELOG.md](docs/CHANGELOG.md#088---2026-02-18)

---

## 📂 디렉토리 구조

```
server/
├── app.py              # Flask 앱 (cachelib 세션)
├── api/                # REST API
│   ├── client.py       # 클라이언트 API (PIN 검증, 하트비트 통합)
│   ├── admin.py        # 관리자 API (토큰 관리, 프로세스 목록, 계정 생성)
│   └── install.py      # 설치 스크립트 (sc create, delayed-auto)
├── models/             # DB 접근
│   ├── registration.py # 등록 토큰 모델
│   ├── pc.py           # PC 모델 (update_light_heartbeat)
│   └── command.py      # 명령 모델
├── services/           # 비즈니스 로직
└── utils/              # 공통 함수

client/
├── main.py             # 메인 로직 (PIN 인증, registered.flag, 자동 업데이트)
├── service.py          # Windows 서비스 (인자 처리 개선, StartServiceCtrlDispatcher)
├── collector.py        # 시스템 정보 수집 (고정 디스크만)
├── executor.py         # 명령 실행 (Chocolatey, PowerShell, RunOnce 언어 설정)
├── updater.py          # 자동 업데이트 모듈
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
- **언어 설정**: `RunOnce` 레지스트리를 사용하여 사용자 최초 로그인 시 적용됨.

---

## 🚀 새 세션 시작 프롬프트

다음 세션을 시작할 때 아래 내용을 복사해서 AI에게 전달하세요:

```markdown

```

---

**문서 규칙:**
- 체크박스: `- [x]` / `- [ ]` (이모티콘 금지)
- 타입 힌팅 필수
- 에러 핸들링 필수
