# WCMS 시스템 아키텍처

> **최종 업데이트**: 2026-02-26
> **프로젝트**: Woosuk Computer Management System

---

## 목차

1. [시스템 개요](#시스템-개요)
2. [아키텍처 다이어그램](#아키텍처-다이어그램)
3. [컴포넌트 구조](#컴포넌트-구조)
4. [통신 흐름](#통신-흐름)
5. [자동 업데이트](#자동-업데이트)
6. [데이터베이스 설계](#데이터베이스-설계)
7. [보안 아키텍처](#보안-아키텍처)

---

## 시스템 개요

WCMS는 Client-Server 아키텍처 기반의 실습실 PC 원격 관리 시스템입니다.

| 계층 | 기술 |
|------|------|
| 프론트엔드 | HTML5, CSS3, Vanilla JavaScript |
| 백엔드 | Flask 2.x, Python 3.11+ |
| 데이터베이스 | SQLite 3 (WAL 모드) |
| 클라이언트 | Python 3.11+, psutil, WMI, pywin32, Chocolatey |
| 통신 | RESTful API, JSON, Short-polling (2s) |
| 패키징 | PyInstaller (클라이언트 EXE) |

---

## 아키텍처 다이어그램

```
                     관리자 (웹 브라우저)
                            |
                        HTTPS/HTTP
                            |
              +-------------+-------------+
              |         Flask 서버         |
              |  Web Routes | Admin API   |
              |             | Client API  |
              |         모델 레이어        |
              |    SQLite (WAL 모드)       |
              |  백그라운드 워커 (30s)     |
              +-------------+-------------+
                            |
                     REST API (2s 폴링)
                            |
              +------+------+------+
              |      |             |
         Client 1  Client 2  ... Client N
         (Windows Service)
```

---

## 컴포넌트 구조

### 서버

```
server/
├── app.py              # Flask 앱 (Talisman, Limiter, 라우트 등록)
├── config.py           # 환경 설정 (Dev/Prod/Test)
├── api/
│   ├── client.py       # 클라이언트 API (등록, 하트비트, 명령 폴링)
│   ├── admin.py        # 관리자 API (PC, 명령, 토큰, 계정 관리)
│   └── install.py      # 설치 스크립트 제공
├── models/
│   ├── pc.py           # PC 정보 (정적/동적)
│   ├── command.py      # 명령 큐
│   ├── registration.py # 등록 토큰 (PIN)
│   └── admin.py        # 관리자 계정
├── services/
│   └── pc_service.py   # 백그라운드 오프라인 체커
├── utils/
│   ├── database.py     # DB 연결 관리
│   ├── auth.py         # 인증 데코레이터
│   └── validators.py   # 입력 검증
└── static/
    ├── css/
    │   ├── base.css        # 공통 레이아웃
    │   ├── index.css       # 메인 페이지
    │   └── components.css  # 공통 컴포넌트 클래스
    └── js/
        ├── modal.js        # PC 상세 모달
        ├── pc-grid.js      # PC 그리드, 선택 모드
        └── commands.js     # 일괄 명령, 결과 폴링
```

### 클라이언트

```
client/
├── main.py             # 메인 루프 (등록, 하트비트, 폴링, 업데이트)
├── service.py          # Windows 서비스 래퍼 (PreShutdown 처리)
├── collector.py        # 시스템 정보 수집 (WMI, psutil)
├── executor.py         # 명령 실행 (Chocolatey, PowerShell, RunOnce)
├── updater.py          # 자동 업데이트 (다운로드 + 배치 교체)
├── config.py           # 설정 (SERVER_URL, 버전)
└── utils.py            # 네트워크 재시도 유틸리티
```

---

## 통신 흐름

### 1. 클라이언트 등록 (최초 1회)

```
Client                    Server
  |                         |
  |---register (POST)------>|
  |  {machine_id, pin...}   |
  |                         |---> DB: PIN 검증
  |                         |---> DB: INSERT pcs
  |<--{token: "..."}--------|
```

### 2. 전체 하트비트 (5분 주기)

```
Client                    Server
  |                         |
  |---heartbeat (POST)----->|
  |  {full_update: true}    |
  |                         |---> DB: UPDATE last_seen, pc_dynamic_info
  |<--{status: success}-----|
```

### 3. 명령 폴링 + 경량 하트비트 (2초 주기)

```
Client                    Server
  |                         |
  |---commands (POST)------>|
  |  {heartbeat: {cpu...}}  |
  |                         |---> DB: UPDATE pc_dynamic_info (partial)
  |                         |---> DB: SELECT commands WHERE status='pending'
  |<--{command: {...}}------|
  |                         |
  |---result (POST)-------->|
  |  {command_id, result}   |
  |                         |---> DB: UPDATE commands.status
  |<--{status: success}-----|
```

### 4. 종료 감지

PreShutdown 서비스 이벤트 수신 시 서버에 오프라인 상태 즉시 알림.

---

## 자동 업데이트

### 흐름

```
클라이언트 시작
    |
check_for_updates() (main.py)
    |
GET /api/client/version
    |
버전 비교
    +-- 최신: 로그 후 종료
    +-- 구버전: perform_update() (updater.py)
              |
              1. 새 EXE 다운로드 (임시 폴더)
              2. 배치 스크립트 생성
              3. 스크립트 실행 + 현재 프로세스 종료
              |
              [배치 스크립트]
              1. net stop WCMS-Client
              2. copy /Y <new_exe> <target>
              3. net start WCMS-Client
              4. 임시 파일 정리
```

### 버전 등록 (관리자)

웹 UI → 클라이언트 버전 메뉴에서 버전/URL/변경사항 입력 후 등록.
또는 GitHub Actions 빌드 완료 후 `POST /api/client/version`으로 자동 등록.

### 트러블슈팅

**업데이트 무한 루프**
- 원인: 버전 비교 오류 또는 다운로드 파일 손상
- 해결: 서버 버전 정보 확인 → 클라이언트 로그 확인 (`C:\ProgramData\WCMS\logs\client.log`) → 수동으로 서비스 중지 후 EXE 교체

**서비스 시작 실패**
- 원인: 권한 문제 또는 파일 경로 오류
- 해결: `sc query WCMS-Client` → 이벤트 뷰어 로그 → `install.cmd` 관리자 권한 재실행

---

## 데이터베이스 설계

### 테이블

| 테이블 | 설명 |
|--------|------|
| `pcs` | PC 정적 정보 (hostname, IP, MAC, CPU, OS) |
| `pc_dynamic_info` | PC 동적 정보 (CPU%, RAM%, 최신 1건 유지) |
| `commands` | 명령 큐 (pending → executing → completed/error) |
| `registration_tokens` | 6자리 PIN (1회용/재사용, 만료시간) |
| `rooms` | 실습실 정보 |
| `layouts` | 좌석 배치 (JSON) |
| `client_versions` | 클라이언트 버전 이력 (download_url, changelog) |
| `admin` | 관리자 계정 |

### 설계 원칙

- 정적/동적 데이터 분리: `pcs`(불변)와 `pc_dynamic_info`(2초 갱신)로 분리
- `pc_dynamic_info`는 `INSERT OR REPLACE`로 최신 상태 1건만 유지
- JSON 필드: `disk_info`, `processes`, `command_data` 등 가변 구조 저장

---

## 보안 아키텍처

### 인증

| 대상 | 방법 |
|------|------|
| 관리자 웹 | Flask 세션 (`session['username']`), bcrypt 해시 |
| 클라이언트 API | `hostname` + `token` (PIN 등록 시 발급) |
| 버전 업데이트 API | `Authorization: Bearer <UPDATE_TOKEN>` |

### 보안 레이어

- `Flask-Talisman`: HTTPS 강제, HSTS, CSP, X-Frame-Options (프로덕션)
- `Flask-Limiter`: 로그인 5회/분, 전역 50회/시간 / 클라이언트 API 제외
- 세션 쿠키: Secure, HttpOnly, SameSite=Lax, 만료 1시간
- Windows 서비스: LocalSystem 계정 (winget 미지원 → Chocolatey 사용)
- 자동 복구: 서비스 실패 시 자동 재시작 (`sc failure`)