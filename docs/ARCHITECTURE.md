# WCMS 시스템 아키텍처

> **최종 업데이트**: 2026-02-18  
> **버전**: 2.2  
> **프로젝트**: Woosuk Computer Management System

---

## 📚 목차

1. [시스템 개요](#시스템-개요)
2. [아키텍처 다이어그램](#아키텍처-다이어그램)
3. [컴포넌트 구조](#컴포넌트-구조)
4. [데이터 흐름](#데이터-흐름)
5. [데이터베이스 설계](#데이터베이스-설계)
6. [보안 아키텍처](#보안-아키텍처)
7. [확장성 고려사항](#확장성-고려사항)

---

## 시스템 개요

WCMS는 **Client-Server 아키텍처**를 기반으로 한 실습실 PC 원격 관리 시스템입니다.

### 핵심 특징
- **중앙 집중식 관리**: 단일 Flask 서버가 모든 클라이언트 관리
- **짧은 폴링(Short-polling) 통신**: 클라이언트가 2초마다 명령 확인 (v0.8.0+)
- **SQLite 데이터베이스**: 경량 데이터베이스로 빠른 배포 (WAL 모드)
- **Windows 서비스**: 백그라운드 상주 프로그램 (자동 시작 및 복구)
- **Chocolatey 통합**: 안정적인 프로그램 설치/삭제 지원 (v0.8.6+)
- **자동 업데이트**: 클라이언트 자동 버전 체크 및 업데이트 (v0.8.7+)

### 기술 스택

| 계층 | 기술 |
|------|------|
| **프론트엔드** | HTML5, CSS3, Vanilla JavaScript, Chart.js |
| **백엔드** | Flask 2.x, Python 3.8+ |
| **데이터베이스** | SQLite 3 (WAL 모드) |
| **클라이언트** | Python 3.8+, psutil, WMI, pywin32, Chocolatey |
| **통신** | RESTful API, JSON, Short-polling (2s) |
| **배포** | PyInstaller (클라이언트), systemd (서버) |

---

## 아키텍처 다이어그램

### 전체 시스템 구조

```
┌─────────────────────────────────────────────────────────────┐
│                         관리자                               │
│                     (웹 브라우저)                            │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTPS/HTTP
                       │ (세션 기반 인증)
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                     Flask 서버                               │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Web Routes │  │  Admin API   │  │  Client API  │      │
│  │  (HTML)     │  │  (관리 명령) │  │  (등록/하트비트)│   │
│  └──────┬──────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                │                  │               │
│         └────────────────┼──────────────────┘               │
│                          ↓                                  │
│  ┌───────────────────────────────────────────────┐         │
│  │           서비스 레이어                        │         │
│  │  - PC 관리   - 명령 처리   - 인증/권한       │         │
│  └─────────────────────┬─────────────────────────┘         │
│                        ↓                                    │
│  ┌───────────────────────────────────────────────┐         │
│  │           모델 레이어                          │         │
│  │  - PC Model  - Command Model  - Admin Model  │         │
│  └─────────────────────┬─────────────────────────┘         │
│                        ↓                                    │
│  ┌───────────────────────────────────────────────┐         │
│  │         SQLite Database (WAL 모드)            │         │
│  │  - pc_info  - pc_dynamic_info  - pc_command   │         │
│  └───────────────────────────────────────────────┘         │
│                                                              │
│  ┌───────────────────────────────────────────────┐         │
│  │       백그라운드 워커 (스레드)                 │         │
│  │  - 오프라인 체크 (30초)                       │         │
│  └───────────────────────────────────────────────┘         │
└─────────────────────┬───────────────────────────────────────┘
                      │ REST API
                      │ (Short-polling 2s)
                      ↓
     ┌────────────────┴────────────────┬─────────────────┐
     ↓                                 ↓                 ↓
┌──────────┐                     ┌──────────┐      ┌──────────┐
│ Client 1 │                     │ Client 2 │ ...  │ Client N │
│ (Windows)│                     │ (Windows)│      │ (Windows)│
│          │                     │          │      │          │
│ ┌──────┐ │                     │ ┌──────┐ │      │ ┌──────┐ │
│ │Collect││                     │ │Collect││      │ │Collect││
│ │or    ││                     │ │or    ││      │ │or    ││
│ └──┬───┘ │                     │ └──┬───┘ │      │ └──┬───┘ │
│    │     │                     │    │     │      │    │     │
│ ┌──▼───┐ │                     │ ┌──▼───┐ │      │ ┌──▼───┐ │
│ │Execut││                     │ │Execut││      │ │Execut││
│ │or    ││                     │ │or    ││      │ │or    ││
│ └──────┘ │                     │ └──────┘ │      │ └──────┘ │
│    │     │                     │    │     │      │    │     │
│ ┌──▼───┐ │                     │ ┌──▼───┐ │      │ ┌──▼───┐ │
│ │Update│ │                     │ │Update│ │      │ │Update│ │
│ │r     │ │                     │ │r     │ │      │ │r     │ │
│ └──────┘ │                     │ └──────┘ │      │ └──────┘ │
│          │                     │          │      │          │
│ Windows  │                     │ Windows  │      │ Windows  │
│ Service  │                     │ Service  │      │ Service  │
└──────────┘                     └──────────┘      └──────────┘
```

### 통신 흐름

#### 1. 클라이언트 등록 (초기 1회)
```
Client                    Server
  │                         │
  │───register (POST)──────>│
  │  {machine_id, pin...}   │
  │                         │──> DB: Verify PIN
  │                         │──> DB: INSERT pc_info
  │                         │──> DB: INSERT pc_specs
  │<──{status: success}─────│
  │                         │
```

#### 2. 하트비트 (5분 주기)
```
Client                    Server
  │                         │
  │───heartbeat (POST)─────>│
  │  {full_update: true}    │
  │                         │──> DB: UPDATE pc_info.last_seen
  │                         │──> DB: UPDATE pc_dynamic_info
  │<──{status: success}─────│
  │                         │
```

#### 3. 명령 폴링 + 경량 하트비트 (2초 주기)
```
Client                    Server
  │                         │
  │───commands (POST)──────>│
  │  {heartbeat: {cpu...}}  │
  │                         │──> DB: UPDATE pc_dynamic_info (partial)
  │                         │──> DB: SELECT pc_command
  │                         │     WHERE status='pending'
  │                         │
  │<──{command: {...}}──────│  (명령 있으면 즉시 응답)
  │                         │
  │───execute───┐           │
  │             │           │
  │<────result──┘           │
  │                         │
  │───result (POST)────────>│
  │  {command_id, result}   │
  │                         │──> DB: UPDATE pc_command
  │<──{status: success}─────│
  │                         │
```

#### 4. 자동 업데이트 (시작 시)
```
Client                    Server
  │                         │
  │───version (GET)────────>│
  │                         │──> DB: SELECT client_versions
  │<──{version, url}────────│
  │                         │
  │ (버전 다르면)             │
  │───Download EXE─────────>│ (GitHub Releases)
  │                         │
  │───Update Script────────>│ (서비스 재시작)
```

---

## 컴포넌트 구조

### 서버 컴포넌트

```
server/
├── app.py                      # Flask 앱 초기화
├── config.py                   # 설정 관리
├── models/                     # 데이터 모델
│   ├── pc.py                   # PC 정보 및 상태
│   ├── command.py              # 명령 관리
│   ├── registration.py         # 등록 토큰 (PIN)
│   └── admin.py                # 관리자 계정
├── api/                        # API 엔드포인트
│   ├── client.py               # 클라이언트용 API
│   ├── admin.py                # 관리자용 API
│   └── install.py              # 설치 스크립트 생성
├── services/                   # 비즈니스 로직
│   ├── pc_service.py           # PC 상태 관리
│   └── command_service.py      # 명령 처리
└── utils/                      # 유틸리티
    ├── database.py             # DB 연결 관리
    └── auth.py                 # 인증
```

### 클라이언트 컴포넌트

```
client/
├── main.py                     # 메인 엔트리포인트 (폴링 루프)
├── config.py                   # 설정 관리 (버전, URL)
├── collector.py                # 시스템 정보 수집 (WMI, psutil)
├── executor.py                 # 명령 실행 (Chocolatey, CMD, RunOnce)
├── updater.py                  # 자동 업데이트 모듈 (v0.8.7+)
├── service.py                  # Windows 서비스 래퍼
└── utils.py                    # 유틸리티 (네트워크 재시도)
```

---

## 데이터베이스 설계

### ERD (Entity Relationship Diagram)

```
┌─────────────────┐
│     admins      │
├─────────────────┤
│ id (PK)         │
│ username        │
│ password_hash   │
└─────────────────┘

┌─────────────────┐         ┌─────────────────┐
│    pc_info      │←────────│   pc_specs      │
├─────────────────┤ 1     1 ├─────────────────┤
│ id (PK)         │         │ id (PK)         │
│ machine_id (UK) │         │ pc_id (FK)      │
│ hostname        │         │ cpu_model       │
│ is_verified     │         │ ram_total       │
│ registered_with │         │ disk_info (JSON)│
└────────┬────────┘         └─────────────────┘
         │
         │ 1
         │
         │ 1
         ↓
┌─────────────────┐         ┌─────────────────┐
│ pc_dynamic_info │         │  pc_command     │
├─────────────────┤         ├─────────────────┤
│ id (PK)         │         │ id (PK)         │
│ pc_id (FK)      │         │ pc_id (FK)      │
│ cpu_usage       │         │ command_type    │
│ ram_used        │         │ command_data    │
│ disk_usage(JSON)│         │ status          │
│ processes(JSON) │         │ result          │
└─────────────────┘         └─────────────────┘
```

### 테이블 설계 원칙

#### 1. 정적/동적 데이터 분리
- **pc_info**: 기본 식별 정보
- **pc_specs**: 하드웨어 스펙 (거의 불변)
- **pc_dynamic_info**: 동적 상태 (2초/5분마다 갱신)

**효과:**
- 디스크 사용량 70% 감소
- `pc_dynamic_info`는 `INSERT OR REPLACE`로 최신 상태만 유지

#### 2. JSON 필드 활용
- **disk_info/usage**: 드라이브별 정보 저장
- **processes**: 프로세스 목록 저장
- **command_data**: 명령 파라미터 저장

---

## 보안 아키텍처

### 1. 인증 및 권한

#### 관리자 인증
- 세션 기반 인증 (`flask-session`)
- `bcrypt` 해시 사용

#### 클라이언트 인증 (v0.8.0+)
- **PIN 기반 등록**: 관리자가 생성한 6자리 PIN으로 최초 등록 시 인증
- **Machine ID**: 등록 후에는 고유 하드웨어 ID로 식별
- **등록 플래그**: 클라이언트는 `registered.flag` 파일을 생성하여 중복 등록 방지

### 2. 서비스 보안

#### Windows 서비스
- **LocalSystem 계정**: 시스템 최고 권한으로 실행
- **Chocolatey**: 시스템 레벨 패키지 관리자 사용으로 권한 문제 해결
- **지연된 자동 시작**: 부팅 시 시스템 안정화 후 시작 (`delayed-auto`)
- **자동 복구**: 서비스 실패 시 자동 재시작 설정 (`sc failure`)
- **언어 설정**: `RunOnce` 레지스트리를 사용하여 사용자 최초 로그인 시 적용 (v0.8.8+)

---

## 확장성 고려사항

### 1. 수평 확장 (Scale Out)

#### 현재 제약
- SQLite는 단일 서버 전용
- 세션은 파일 시스템 저장

#### 확장 방안
- SQLite → PostgreSQL 전환
- 세션 저장소 → Redis 전환

### 2. 성능 최적화 (v0.8.0)

#### 네트워크 최적화
- **경량 하트비트**: 2초마다 CPU, RAM, IP만 전송 (수백 바이트)
- **전체 하트비트**: 5분마다 디스크, 프로세스 등 전체 정보 전송
- **명령 통합**: 명령 조회 요청에 경량 하트비트를 실어 보내 HTTP 요청 수 50% 절감

---

**문서 버전**: 2.2  
**최종 업데이트**: 2026-02-18
**작성자**: WCMS Team
