# 변경 이력

프로젝트의 주요 변경사항을 기록합니다.

형식: [Keep a Changelog](https://keepachangelog.com/ko/1.0.0/)  
버전 관리: [Semantic Versioning](https://semver.org/lang/ko/)

---

## [Unreleased] - 0.8.0

### 계획
- [ ] Docker 환경에서 설치 스크립트 E2E 테스트
- [ ] 클라이언트 자동 업데이트 강화 (자동 다운로드 및 설치)
- [ ] 설치 스크립트 개선 (진행률 표시, 롤백 기능)

---

## [0.7.0] - 2026-02-07

### 추가
- **한 줄 설치 스크립트 구현 (Phase 2 완료)** [x]
  - **server/api/install.py**: 설치 API Blueprint 추가
    - `/install/install.cmd` - Windows Batch 스크립트 동적 생성 (영어 메시지)
    - `/install/install.ps1` - PowerShell 스크립트 동적 생성
    - `/install/version` - `/api/client/version`으로 리다이렉트
  - **GitHub Releases 기반 배포**: EXE는 GitHub에서 호스팅, 서버는 스크립트만 제공
  - **동적 스크립트 생성**: 서버 URL을 자동으로 삽입하여 스크립트 생성
  - **인코딩 문제 해결**: CMD 스크립트를 영어로 작성하여 Windows 코드페이지 문제 방지
  - **사용법**: 
    - CMD: `curl -fsSL http://server:5050/install/install.cmd -o install.cmd && install.cmd && del install.cmd`
    - PS1: `iwr -Uri "http://server:5050/install/install.ps1" -OutFile install.ps1; .\install.ps1; del install.ps1`
  - **기능**:
    - 관리자 권한 확인
    - 서버에서 최신 버전 조회 (`/api/client/version`)
    - GitHub Releases에서 EXE 다운로드
    - 자동 설치 및 서비스 등록
    - 설정 파일 자동 생성 (`config.json`)
    - 서비스 시작 및 상태 확인

- **클라이언트 서버 URL 설정 개선** [x]
  - **3단계 우선순위 시스템**:
    - 1순위: `config.json` 파일 (설치 스크립트가 자동 생성)
    - 2순위: 환경변수 `WCMS_SERVER_URL`
    - 3순위: 기본값 `http://localhost:5050` (테스트/개발용)
  - **프로덕션 주소 제거**: 하드코딩된 서버 주소 제거
  - **유연한 배포**: 설치 시 자동으로 올바른 서버 주소 설정

- **문서 정리** [x]
  - 불필요한 개발 과정 문서 삭제 (5개)
  - 핵심 문서만 유지 (9개)
  - INDEX.md 간소화

### 추가
- **Docker 통합 테스트 인프라 구축** [x] (2026-02-07)
  - Docker Compose 기반 테스트 환경 구성 (`docker-compose.yml`)
  - dockurr/windows 이미지 활용 (실제 Windows 11 환경)
  - **자동 DB 초기화**: entrypoint 스크립트로 스키마 적용 및 관리자 계정 자동 생성
  - **로컬 ISO 파일 마운트**: `/boot.iso`로 직접 마운트 (VERSION 환경변수 무시)
  - VNC 접속 지원 (웹 VNC: 8006, VNC: 5900, RDP: 3389)
  - 서버 컨테이너 자동 빌드 (`Dockerfile.server`, `docker-entrypoint.sh`)
  - 시스템 리소스 자동 감지 및 할당 (RAM, CPU)
  - 새 테스트 스크립트: `tests/docker_test.py` (색상 출력, 사전 요구사항 확인)
  - manage.py 통합: `python manage.py docker-test [옵션]`
  - 환경 설정 파일: `.env.docker`
  - **모든 테스트 통과**: 서버 헬스체크, 클라이언트 등록, Heartbeat (3/3)

- **Windows 백업 및 복원 시스템** [x] (2026-02-07)
  - 백업 스크립트: `scripts/backup-windows.ps1` (Docker 볼륨 → tar.gz)
  - 복원 스크립트: `scripts/restore-windows.ps1` (대화형 선택 지원)
  - 백업 가이드: `docs/DOCKER_WINDOWS_BACKUP.md`
  - 설치 시간 절약: 10-15분 부팅 → 백업 복원으로 1-2분
  - 자동 타임스탬프 파일명: `windows-clean-20260207_143022.tar.gz`
  - 백업 크기: 10-18 GB (압축)

- **PreShutdown 종료 감지 기능 완료** [x]
  - 클라이언트: PreShutdown 이벤트 핸들링 (`client/service.py`)
  - 클라이언트: 종료 신호 전송 함수 (`client/main.py`)
  - 서버: `/api/client/shutdown` 엔드포인트 (`server/api/client.py`)
  - 서버: `set_offline_immediately()` 서비스 (`server/services/pc_service.py`)
  - 상세: `plan.md` 참고

- **테스트 환경 개선** [x] (2026-01-30)
  - 문제: pytest conftest.py에서 Flask import 실패 (클라이언트 테스트)
  - 해결: `tests/conftest.py` Flask import 조건부 처리
  - 개선: `manage.py` test 명령 전 자동 의존성 설치
  - 결과: `python manage.py test` 명령 정상 작동 (45개 테스트 통과)

- **실시간 종료 감지 테스트 계획 추가** [x] (plan.md 섹션 4)
  - 6가지 상세 테스트 시나리오
  - PowerShell API 테스트 예제 코드
  - 트러블슈팅 테이블
  - 우선도별 리팩토링 5가지 항목

- **AI 컨텍스트 파일 생성** [x]
  - `AI_CONTEXT.md`: AI/신규 개발자를 위한 빠른 온보딩 가이드
  - 프로젝트 핵심 개념, 파일 맵, 작업 패턴, 의사결정 기록(ADR) 포함
  - 새 세션에서 빠른 적응 가능

- **서버 모듈화 완료** (Phase 1 - 100%)
  - 모델 레이어: `server/models/` (PC, Command, Admin)
  - API 레이어: `server/api/` (Client, Admin - Flask Blueprint)
  - 서비스 레이어: `server/services/` (PC, Command)
  - 유틸리티: `server/utils/` (Database, Auth, Validators)
  - 설정 관리: `server/config.py` (환경별 설정 분리)

- **클라이언트 개선** (Phase 2 - 60%)
  - 설정 중앙화: `client/config.py` (환경변수 지원)
  - 유틸리티: `client/utils.py` (네트워크 재시도, 안전한 요청)
  - 시스템 프로세스 JSON 외부화
  - `main.py` 리팩토링 (진행 중)

- **문서 체계화 및 정리** (2026-01-30)
  - 존재하지 않는 문서 참조 제거
  - 이모티콘 체크박스를 마크다운 표준으로 변경 ([x], [ ])
  - AI 규칙: `.github/copilot-instructions.md` 단일화
  - 중복 문서 제거 및 구조 간소화

- **테스트 인프라 구축**
  - archive 버전 검증 테스트: `tests/archive/test_complete.py` (32개 테스트)
  - 리팩터링 버전 검증 테스트: `tests/server/test_complete.py` (21개 테스트)
  - 전체 45개 테스트 통과

### 변경
- 서버 아키텍처: 단일 파일 (1,270줄) → 모듈화 (13개 파일, 2,680줄)
- 설계 패턴 적용: Repository, Blueprint, Service 레이어
- 타입 힌팅 추가 (모든 새 함수)
- 문서 구조: 명확한 역할 분리 및 중복 제거
- 프로젝트 구조 정리: archive, tests, docs, db, scripts 디렉토리 분리
- `plan.md`: 계획 문서 → 구현 완료 문서로 전환

### 수정
- **Docker 서버 DB 초기화 수정** [x] (2026-02-07)
  - 문제: manage.py가 환경변수 `WCMS_DB_PATH`를 무시하고 하드코딩 경로 사용
  - 해결: `manage.py init-db`가 환경변수를 우선 사용하도록 수정
  - 결과: 서버가 `/app/db/wcms.sqlite3` 경로로 올바르게 DB 접근
  - 영향: `docker-entrypoint.sh` 스크립트가 정상 작동

- **Docker 헬스체크 타임아웃 개선** [x] (2026-02-07)
  - 문제: 60초 타임아웃이 너무 짧아 DB 초기화 중 실패
  - 해결: `tests/docker_test.py`의 `wait_for_service()` 함수 개선
    - 타임아웃 60초 → 120초 증가
    - Docker 헬스체크 + HTTP 직접 확인 병행
    - 진행상황 15초마다 출력
  - 결과: 서버가 안정적으로 시작 완료 대기 (12초 소요)

- **[중요] CommandModel 스키마 호환성 버그 수정**
  - 문제: 리팩터링 코드가 archive DB 스키마에 없는 컬럼 사용 시도
  - 해결: 런타임 스키마 감지 및 호환성 레이어 추가
  - 영향: 모든 명령 전송 API (shutdown, reboot, account 관리 등)
  - 결과: archive DB와 리팩터링 DB 모두 지원 (마이그레이션 불필요)
- 네트워크 통신 안정성 개선 (자동 재시도)
- 설정 관리 개선 (하드코딩 → 환경변수)

---

## [0.6.0] - 2025-12-04

### 추가
- **일괄 명령 전송 기능 확장**
  - 드래그 선택으로 여러 PC 동시 선택
  - 체크박스 UI로 선택된 PC 시각적 확인
  - 온라인 PC 전체 선택 기능
  - 실시간 명령 결과 모달 (2초마다 자동 새로고침)
  
- **명령 초기화 시스템**
  - 대기 중인 명령 전체 조회 API
  - 개별 PC 명령 삭제
  - 일괄 명령 삭제 (선택된 PC들)
  - 부팅 시 밀린 명령 방지 기능

- **PC 상세 정보 향상**
  - CPU 모델명 표시 (WMI 통합)
  - Windows 에디션 표시 (Home/Pro/Education 등)
  - 디스크 정보 GB 단위 통일
  - 프로세스 목록 개선 (100+ 시스템 프로세스 필터링)

### 개선
- 명령 폴링 최적화 (Long-polling 10초)
- 하트비트 주기 최적화 (5분)
- 웹 UI 자동 새로고침 (30초)
- 백그라운드 오프라인 체크 (30초 주기)
- SQLite WAL 모드 적용 (동시성 개선)

### 수정
- 정적/동적 데이터 분리로 디스크 사용량 70% 감소
- 시스템 프로세스 필터링 정확도 향상
- CPU/RAM/디스크 정보 단위 통일 (GB)
- 명령 실행 안정성 개선

---

## [0.5.6] - 2025-11-19

### 추가
- Windows 서비스로 클라이언트 배포
- GitHub Actions 자동 빌드 및 배포
- 클라이언트 자동 버전 체크 기능
- 백그라운드 오프라인 체크 (30초 주기)
- Long-polling 최적화 (10초)

### 개선
- 정적/동적 데이터 분리로 디스크 사용량 70% 감소
- 하트비트 주기 최적화 (10분 → 5분)
- 명령 폴링 주기 최적화 (30초 → 10초)

### 수정
- SQLite WAL 모드 적용으로 동시성 개선
- 프로세스 필터링 개선 (100+ 시스템 프로세스)
- CPU/RAM/디스크 정보 GB 단위로 통일

---

## [0.5.0] - 2025-11-10

### 추가
- 일괄 명령 전송 기능 (드래그 선택, 체크박스)
- Windows 계정 관리 (생성/삭제/비밀번호 변경)
- 명령 실행 결과 보고 API
- 프로세스 실행 기록 페이지

### 개선
- 좌석 배치 편집기 UI 개선
- PC 상세 정보 모달 디자인 개선

---

## [0.4.0] - 2025-10-25

### 추가
- 명령 폴링 및 실행 시스템
- 명령 큐 시스템 (pc_command 테이블)
- 명령 상태 추적 (pending/executing/completed/error)

---

## [0.3.0] - 2025-10-15

### 추가
- 좌석 배치 관리 시스템 (드래그 앤 드롭)
- 실습실 관리 페이지

### 개선
- 데이터베이스 스키마 최적화 (정적/동적 데이터 분리)

---

## [0.2.0] - 2025-10-05

### 추가
- 클라이언트 기본 기능 (시스템 정보 수집, 하트비트)
- WMI를 통한 정확한 시스템 정보 수집

---

## [0.1.0] - 2025-09-20

### 추가
- Flask 서버 기본 구조
- SQLite 데이터베이스
- 초기 문서 작성

---

## 로드맵

### v0.7.0 (예정: 2025-01-10) - 리팩토링 완료
- [x] 서버 모듈화 완료
- [x] 클라이언트 구조 개선 (진행 중)
- [ ] 단위 테스트 80% 커버리지
- [x] 타입 힌팅 추가
- [ ] 코드 품질 도구 (Black, Flake8, mypy)

### v0.8.0 (예정: 2025-01-20) - 테스트 및 안정화
- [ ] app.py 완전 리팩토링 (Blueprint 통합)
- [ ] 단위 테스트 완료
- [ ] 통합 테스트 확장
- [ ] 성능 최적화
- [ ] 보안 강화

### v1.0.0 (예정: 2025-02-01) - 프로덕션 준비
- [ ] 프로덕션 배포 가이드
- [ ] 모니터링 시스템
- [ ] HTTPS 지원
- [ ] 인증서 관리

### v1.1.0 (예정: 2025-03-01) - 기능 확장
- [ ] 파일 업로드 기능
- [ ] 스크립트 실행 기능
- [ ] 예약 명령 실행
- [ ] 모바일 반응형 UI
- [ ] API 버전 관리 (/api/v1/)

---

**참고**: [Unreleased]는 다음 릴리스에 포함될 변경사항입니다.
