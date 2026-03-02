# WCMS (Woosuk Computer Management System)

실습실 PC를 원격으로 관리하고 모니터링하기 위한 시스템입니다.

**버전**: v0.9.5 | **최근 업데이트**: 2026-03-03

---

## 주요 기능

- PIN 기반 클라이언트 등록 인증
- Long-poll 방식 실시간 명령 전달 (2초 주기)
- PC 그리드 UI — 좌석 배치, 상태 모니터링
- 일괄 명령 — 종료/재시작/메시지/계정 관리/프로그램 설치
- 계정 생성 시 표시 언어 설정 (Install-Language + NTUSER.DAT)
- 클라이언트 자동 업데이트
- 오프라인 자동 감지 (40초 threshold)

---

## 빠른 시작

### 서버

```bash
# 1. 의존성 설치
python manage.py install

# 2. 데이터베이스 초기화
python manage.py init-db

# 3. 서버 실행
python manage.py run
```

접속 주소: `http://localhost:5050` | 기본 계정: `admin` / `admin`

### 클라이언트 설치

1. 관리자 페이지 → **등록 토큰** → 6자리 PIN 생성
2. 실습실 PC에서 관리자 권한으로 실행:

**Windows CMD:**
```cmd
curl -fsSL http://서버주소:5050/install/install.cmd -o install.cmd && install.cmd && del install.cmd
```

**PowerShell:**
```powershell
iwr -Uri "http://서버주소:5050/install/install.ps1" -OutFile install.ps1; .\install.ps1; del install.ps1
```

설치 중 PIN 입력 → 자동 등록 → Windows 서비스(`WCMS-Client`)로 시작

---

## 문서

| 문서 | 설명 |
|------|------|
| [시작 가이드](docs/GETTING_STARTED.md) | 설치 및 실행 상세 |
| [아키텍처](docs/ARCHITECTURE.md) | 시스템 구조 |
| [API 명세](docs/API.md) | REST API |
| [보안](docs/SECURITY.md) | 보안 설정 및 정책 |
| [변경 이력](docs/CHANGELOG.md) | 버전별 변경사항 |

---

## 기술 스택

| 구분 | 기술 |
|------|------|
| 서버 | Python 3.9+, Flask, SQLite (WAL) |
| 클라이언트 | Python 3.9+, psutil, WMI, pywin32 |
| 패키징 | PyInstaller (EXE) |
| 패키지 관리 | uv |

---

## 트러블슈팅

**서비스 시작 실패**
`install.cmd`를 관리자 권한으로 재실행하세요. 이벤트 뷰어에서 원인을 확인할 수 있습니다.

**언어 설정이 적용 안 됨**
클라이언트 로그(`C:\ProgramData\WCMS\logs\client.log`)에서 언어 팩 설치 결과를 확인하세요. 일부 언어(mn-MN 등)는 Windows에서 지원하지 않을 수 있습니다.

**프로그램 설치 실패**
WCMS는 Chocolatey를 사용합니다. 네트워크 문제로 실패한 경우 수동으로 Chocolatey를 설치하세요.

---

## 라이선스

MIT License