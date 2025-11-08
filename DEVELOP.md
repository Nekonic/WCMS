# 개발 가이드 (DEVELOP.md)

## 빠른 시작

### 프로젝트 개요
- **이름**: WCMS (Woosuk Computer Management System)
- **목표**: 대학 실습실 PC 40대 원격 모니터링 및 제어
- **주요 기능**: 시스템 정보 수집, 원격 종료/재시작, 실습실 관리
- **개발 기간**: 2025.10.18 ~ 2025.11.15
- **상태**: [🔨 개발 중] (현재 Phase: 클라이언트 시스템 정보 수집)

---

## 아키텍처 요약

```
[Flask 서버] ← HTTP API → [Windows 클라이언트]
├─ 웹 대시보드 (Jinja2 + Bootstrap)
├─ PC 정보 수집/저장 (SQLite)
└─ 명령 전달 시스템

[관리자] → 서버 대시보드 → 원격 제어
```


---

## 기술 스택

| 계층 | 기술 |
|------|------|
| 서버 | Flask, SQLite, Jinja2 |
| 클라이언트 | Python, psutil, wmi, requests |
| 빌드 | PyInstaller, GitHub Actions |
| 배포 | Windows 서비스 |

---

## 파일별 역할

### 서버
| 파일 | 역할 |
|------|------|
| `app.py` | Flask 라우트 (PC 조회, 로그인, 원격 제어) |
| `migrations/schema.sql` | DB 테이블 정의 |
| `templates/base.html` | UI 프레임워크 + 모달 |
| `templates/index.html` | 좌석 배치도 + PC 카드 |

### 클라이언트
| 파일 | 역할 |
|------|------|
| `main.py` | 메인 루프 (10분마다 heartbeat) |
| `collector.py` | CPU, RAM, 디스크, OS 정보 수집 |
| `api.py` | 서버 API 호출 |
| `executor.py` | 종료/재시작/CMD 실행 |

---

## 현재 개발 상태

### ✅ 완료된 기능
- [x] Flask 서버 기본 구조
- [x] SQLite 데이터베이스 스키마
- [x] 웹 대시보드 UI (사이드바, PC 카드, 모달)
- [x] 관리자 로그인 (bcrypt)
- [x] 좌석 배치도
- [x] PC 상세 정보 모달
- [x] 서버-클라이언트 API 테스트 완료
- [x] 좌석 배치 드래그&드롭 에디터
- [x] **클라이언트 기본 기능**
  - [x] 시스템 정보 수집 (실제 IP/MAC)
  - [x] 서버 등록 및 heartbeat
  - [x] Long-polling 명령 수신
  - [x] 종료/재시작/명령 실행
- [x] **GitHub Actions 자동 빌드**
  - [x] build.spec (PyInstaller 설정)
  - [x] build-client.yml (GitHub Actions 워크플로우)

### 🔨 진행 중
- [ ] Windows 서비스 등록 (nssm/pywin32 활용)
- [ ] 파일 전송 기능
- [ ] 프로그램 설치 고도화

### 📋 향후 계획
- [ ] Windows 서비스화
- [ ] 실제 40대 PC 배포
- [ ] 모니터링 대시보드 고도화
- [ ] 한국/중국/몽골 사용자 계정 생성
- [ ] 과목별 자동 프로그램 설치

---

## 로컬 테스트 환경 설정

### 1. 서버 시작
```bash
cd server
python app.py  # http://localhost:5050
```

### 2. 클라이언트 API 통신 테스트
```bash
cd client
python test_api.py
```

### 3. 대시보드 확인(개발용)
- 주소: http://localhost:5050
- 로그인: admin / admin

---

## 주요 API 엔드포인트

### 클라이언트 → 서버
| Method | Endpoint | 용도              |
|--------|----------|-----------------|
| POST | `/api/client/register` | 최초 등록           |
| POST | `/api/client/heartbeat` | 10분마다 상태 전송     |
| GET | `/api/client/command?machine_id=...` | 명령 확인 (5초마다 폴링) |
| POST | `/api/client/command/result` | 명령 실행 결과 전송     |

### 웹 → 서버
| Method | Endpoint | 용도 |
|--------|----------|------|
| GET | `/` | PC 목록 조회 |
| GET | `/api/pc/<id>` | PC 상세 정보 |
| POST | `/api/pc/<id>/shutdown` | 원격 종료 |
| POST | `/api/pc/<id>/reboot` | 원격 재시작 |

---

## 데이터베이스 구조

### pc_info (기본 정보)
```
id, machine_id, room_name, seat_number, hostname, 
is_online, ip_address, mac_address, last_seen
```
### pc_status (상태 로그)
```
id, pc_id, cpu_model, cpu_usage, ram_total, ram_used, 
disk_info, os_edition, os_version, ...
```
### admins (관리자)
```
id, username, password_hash
```
---

## 주의사항

1. **서버 URL**: client 코드의 SERVER_URL을 로컬/배포 환경에 맞게 수정 필요
2. **기기 ID**: 각 PC마다 고유한 machine_id 필요 (MAC 주소 기반)
3. **권한 관리**: 관리자 권한 필요한 작업 (서비스 등록, 종료 등)

---

## 빠른 참조 (Cheat Sheet)

### 현재 진행 중인 작업
- Phase: 클라이언트 개발
- 목표: 실제 시스템 정보 수집 및 자동 전송
- 예상 완료: 2025.11.15

### 다음 작업
1. collector.py 완성 (모든 시스템 정보 수집)
2. main.py 메인 루프 구현
3. 클라이언트 테스트
