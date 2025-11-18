# 개발 가이드 (DEVELOP.md)

## 빠른 시작

### 프로젝트 개요
- **이름**: WCMS (Woosuk Computer Management System)
- **목표**: 대학 실습실 PC 40대 원격 모니터링 및 제어
- **주요 기능**: 시스템 정보 수집, 프로세스 로깅, 원격 종료/재시작, 실습실 관리
- **개발 기간**: 2025.10.18 ~ 2025.11.15
- **상태**: [🔨 개발 중]

---

## 아키텍처 요약

```
[Flask 서버] ← HTTP API → [Windows 클라이언트]
├─ 웹 대시보드 (Jinja2)
├─ PC 정보 수집/저장 (SQLite)
└─ 명령 전달 시스템 (Long-polling)

[관리자] → 서버 대시보드 → 원격 제어 및 기록 조회
```

---

## 기술 스택

| 계층 | 기술 |
|------|------|
| 서버 | Flask, SQLite, Jinja2 |
| 클라이언트 | Python, psutil, wmi, requests |
| 빌드 | PyInstaller, GitHub Actions |
| 배포 | Windows 서비스 (예정) |

---

## 파일별 역할

### 서버
| 파일 | 역할 |
|------|------|
| `app.py` | Flask 라우트 (PC 조회, 로그인, 원격 제어, 기록 조회 API) |
| `migrations/schema.sql` | DB 테이블 정의 |
| `templates/base.html` | 기본 레이아웃, 사이드바, PC 상세 정보 모달 |
| `templates/index.html` | PC 카드 목록 (실습실별) |
| `templates/process_history.html` | 특정 PC의 프로세스 실행 기록 페이지 |
| `templates/layout_editor.html` | 드래그&드롭 좌석 배치 편집기 |
| `templates/login.html` | 관리자 로그인 페이지 |

### 클라이언트
| 파일 | 역할 |
|------|------|
| `main.py` | 메인 루프 (최초 등록, 주기적 heartbeat, 명령 수신) |
| `collector.py` | 시스템 정보 수집 (`collect_static_info`, `collect_dynamic_info`, `collect_running_processes`) |
| `executor.py` | 종료/재시작/CMD 실행 |

---

## 주요 API 엔드포인트

### 클라이언트 → 서버
| Method | Endpoint | 용도 | 요청 데이터 |
|--------|----------|------|-------------|
| POST | `/api/client/register` | 최초 등록 | 정적 정보 (CPU 모델, 총 RAM, OS, MAC 주소 등) |
| POST | `/api/client/heartbeat` | 상태 전송 | 동적 정보 (CPU/RAM 사용량, IP, 실행 프로세스 등) |
| GET | `/api/client/command?machine_id=...` | 명령 확인 | `machine_id` |
| POST | `/api/client/command/result` | 결과 전송 | `machine_id`, `command_id`, 결과 |

### 웹 → 서버
| Method | Endpoint | 용도 |
|--------|----------|------|
| GET | `/?room=실습실명` | PC 목록 조회 |
| GET | `/api/pc/<id>` | PC 상세 정보 (JSON, 모달용) |
| POST | `/api/pc/<id>/command` | 원격 명령 전송 |
| GET | `/pc/<id>/history` | 프로세스 기록 페이지 |
| GET | `/api/pc/<id>/history` | 프로세스 기록 데이터(JSON) |
| GET | `/layout_editor?room=실습실명` | 좌석 배치 편집기 |
| POST | `/api/layout/map/<room_name>` | 좌석 배치 저장 |

---

## 데이터베이스 구조

### pc_info (PC 고유 정보)
```
id, machine_id, hostname, mac_address, room_name, seat_number, ip_address, is_online, last_seen
```
### pc_status (PC 상태 로그)
```
id, pc_id, cpu_model, cpu_cores, ..., ram_total, ..., os_edition, ..., processes, created_at
```
- **정적 정보**: `cpu_model`, `ram_total` 등은 최초 1회만 기록되고 이후 heartbeat에서는 이전 값을 상속.
- **동적 정보**: `cpu_usage`, `ram_used`, `processes` 등은 heartbeat마다 기록.

### admins (관리자)
```
id, username, password_hash
```
---

## 로컬 테스트 환경 설정

### 1. 데이터베이스 초기화
```bash
cd server
./init_db.sh
```

### 2. 서버 시작
```bash
# server 디렉토리에서
python app.py
```

### 3. 클라이언트 실행
```bash
cd client
python main.py
```
---

## 주의사항

1. **서버 URL**: `client/main.py`의 `SERVER_URL`을 실제 서버 주소에 맞게 수정해야 합니다.
2. **DB 스키마 변경**: `migrations/schema.sql` 수정 후에는 반드시 `init_db.sh`를 실행하여 DB를 재생성해야 합니다.
3. **WMI 관련 경고**: 클라이언트 실행 시 나타나는 `Win32 exception` 경고는 `wmi` 라이브러리의 COM 객체 해제 과정에서 발생하는 것으로, 기능에 영향을 주지 않으므로 무시해도 됩니다.
