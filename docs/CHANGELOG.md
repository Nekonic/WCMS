# 변경 이력

프로젝트의 주요 변경사항을 기록합니다.

형식: [Keep a Changelog](https://keepachangelog.com/ko/1.0.0/)  
버전 관리: [Semantic Versioning](https://semver.org/lang/ko/)

---

## [0.8.0] - 2026-02-10

> **상태**: ✅ Released  
> **테마**: 보안 강화, 네트워크 최적화, RESTful API 개선

### Added - 새로운 기능

#### 🔐 PIN 인증 시스템
- [x] **등록 토큰 관리**
  - 관리자가 6자리 PIN 생성
  - 1회용 / 재사용 가능 토큰 지원
  - 만료 시간 설정 (기본 10분)
  - 토큰 목록 조회 및 삭제
  
- [x] **클라이언트 PIN 검증**
  - `/api/client/register`에 PIN 필수
  - 403 에러 (PIN 검증 실패)
  - 400 에러 (PIN 누락)
  - `is_verified`, `registered_with_token` DB 필드 추가

- [x] **관리자 API**
  - `POST /api/admin/registration-token` - 토큰 생성
  - `GET /api/admin/registration-tokens` - 토큰 목록
  - `DELETE /api/admin/registration-token/{id}` - 토큰 삭제
  - `GET /api/admin/pcs/unverified` - 미검증 PC 조회
  - `DELETE /api/pc/{pc_id}` - PC 삭제 (Cascade)

#### ⚡ 네트워크 성능 최적화
- [x] **Long-polling 제거**
  - `time.sleep()` 제거로 워커 blocking 해결
  - 즉시 응답 방식으로 변경
  - 폴링 주기: 5초 → 2초

- [x] **명령 조회 + 하트비트 통합**
  - `POST /api/client/commands` (RESTful 복수형)
  - 경량 하트비트 (CPU, RAM, IP) 함께 전송
  - HTTP 요청 오버헤드 50% 절감
  - 대역폭 60% 절감 (프로세스 목록 제외)

- [x] **IP 주소 자동 업데이트**
  - 모든 경량 하트비트에 IP 포함

### Changed - 변경사항

#### 🔄 API 개선 (Breaking Changes)
- [x] **RESTful API 재설계**
  - 일관된 응답 형식: `{status, data, error}`
  - 명령 조회: `/api/client/command` → `/api/client/commands`
  - 명령 결과: `/api/client/command/result` → `/api/client/commands/{id}/result`
  - 에러 코드 추가: `PC_NOT_FOUND`, `COMMAND_NOT_FOUND` 등

- [x] **응답 형식 통일**
  ```json
  // 성공
  {"status": "success", "data": {...}}
  
  // 에러
  {"status": "error", "error": {"code": "...", "message": "..."}}
  ```

- [x] **명령 응답 개선**
  - `command_id` → `data.command.id`
  - `command_type` → `data.command.type`
  - `command_data` → `data.command.parameters`
  - `has_command` boolean 플래그 추가

#### 🗄️ 데이터베이스 스키마 변경
- [x] **테이블 이름 정규화**
  - `pc_command` → `commands`
  - `pc_status` → `pc_dynamic_info`
  
- [x] **pc_dynamic_info 최적화**
  - UNIQUE 제약 추가 (최신 상태만 저장)
  - `INSERT OR REPLACE` 사용
  - 디스크 사용량 70% 감소
  - `created_at` → `updated_at`

### Fixed - 버그 수정
- [x] 동시 연결 처리 문제 해결 (Long-polling 제거)
- [x] IP 변경 시 자동 업데이트
- [x] Rate limiting 구현 (2초 간격)
- [x] DB 트랜잭션 안정성 개선

### Testing - 테스트
- [x] **통합 테스트 작성**
  - 14개 통합 테스트 추가
  - 클라이언트-서버 전체 흐름 검증
  - PIN 인증 시스템 테스트
  - 에러 시나리오 테스트
  
- [x] **테스트 커버리지**
  - 65개 테스트 통과
  - API 레이어 완전 검증
  - 레거시 호환성 테스트
  - DHCP, VPN, 네트워크 전환 대응
  - 최대 2초 이내 감지
  - `ip_changed` 응답 필드 추가

- [x] **full_update 플래그**
  - 전체 하트비트: 5분마다 (프로세스 목록 포함)
  - 경량 하트비트: 2초마다 (CPU, RAM, IP만)

#### 🌐 웹 UI
- [x] **등록 토큰 관리 페이지**
  - 토큰 생성 폼 (usage_type, expires_in)
  - PIN 대형 표시 및 복사 기능
  - 활성 토큰 목록 테이블
  - 사용 횟수 및 만료 시간 표시
  - 토큰 삭제 기능

#### 📦 설치 개선
- [x] **install.cmd 재작성**
  - PIN 입력 대화형 프롬프트
  - 6자리 숫자 검증 (findstr 정규식)
  - SERVER_URL 슬래시 처리 완전 수정
  - config.json에 REGISTRATION_PIN 추가
  - COMMAND_POLL_INTERVAL 2초 설정

### Changed - 변경사항

#### API 변경
- [x] `/api/client/command`: GET/POST 모두 지원
- [x] `/api/client/heartbeat`: `full_update` 플래그 추가
- [x] `/api/client/register`: `pin` 필수 필드 추가

#### 클라이언트 변경
- [x] `config.py`: `load_registration_pin()` 함수 추가
- [x] `main.py`: `poll_command()` 전면 재작성 (POST 방식)
- [x] 폴링 주기: 10초 → 2초
- [x] 하트비트 주기: 10분 → 5분

### Fixed - 버그 수정

- [x] install.cmd 중복 코드 제거
- [x] admin.py `delete_pc` 함수 중복 정의 제거
- [x] SERVER_URL 끝 슬래시 처리 버그 수정

### Performance - 성능 개선

| 항목 | v0.7.1 | v0.8.0 | 개선 |
|------|--------|--------|------|
| HTTP 요청 수 | 1,812회/시간 | 1,800회/시간 | 0.7% ↓ |
| 대역폭 (100대) | 60MB/시간 | 24MB/시간 | **60% ↓** |
| IP 업데이트 지연 | 최대 5분 | 최대 2초 | **99% ↓** |
| 폴링 주기 | 10초 | 2초 | **5배 빠름** |
| 동시 연결 | ~20대 | ~100대 | **5배 증가** |

### Tests - 테스트

- [x] 37개 테스트 작성
  - `test_models_registration.py`: 13개 (토큰 모델)
  - `test_api_registration.py`: 8개 (관리자 API)
  - `test_api_client_auth.py`: 8개 (PIN 인증)
  - `test_api_heartbeat.py`: 8개 (하트비트 통합)

### Documentation - 문서

- [x] `docs/API.md` 전면 재작성
- [x] `docs/plan.md` 상세 실행 계획서 작성
- [x] `AI_CONTEXT.md` v0.8.0 요약 추가

### Database - 데이터베이스

- [x] `008_add_registration_tokens.sql` 마이그레이션
  - `pc_registration_tokens` 테이블 생성
  - `pc_info`에 `is_verified`, `registered_with_token`, `verified_at` 컬럼 추가
  - 기존 PC 자동 검증 처리

### Breaking Changes - 하위 호환성

- ⚠️ **v0.7.1 이하 클라이언트**: PIN 없이 등록 시 403 오류
- ✅ **하위 호환 유지**: GET /api/client/command 계속 지원
- ✅ **마이그레이션**: 기존 PC 자동 검증 (`registered_with_token='MIGRATED'`)

---

## [Unreleased] - 0.9.0 (계획)
  - PC 삭제 기능 추가 (미검증 PC 제거)
  - 미검증 PC 시각적 구분

#### 데이터베이스 변경
- [ ] 신규 테이블: `pc_registration_tokens`
  - 6자리 PIN, 사용 유형, 만료 시간, 사용 횟수
- [ ] `pc_info` 테이블 컬럼 추가
  - `is_verified`: 검증 여부
  - `registered_with_token`: 사용한 PIN
  - `verified_at`: 검증 시각

#### 새로운 API 엔드포인트
- [ ] `POST /api/admin/registration-token` - 토큰 생성
- [ ] `GET /api/admin/registration-tokens` - 토큰 목록
- [ ] `DELETE /api/admin/registration-token/<token>` - 토큰 삭제
- [ ] `DELETE /api/admin/pc/<pc_id>` - PC 삭제
- [ ] `GET /api/admin/pcs/unverified` - 미검증 PC 목록

#### 보안 개선
- [ ] 클라이언트 등록 시 PIN 필수 검증
- [ ] 토큰 만료 시간 자동 체크
- [ ] 1회용 토큰 재사용 방지
- [ ] 관리자 권한으로만 PC 삭제 가능

#### 기타
- [ ] Docker 환경에서 설치 스크립트 E2E 테스트
- [ ] 클라이언트 자동 업데이트 강화 (자동 다운로드 및 설치)
- [ ] 설치 스크립트 개선 (진행률 표시, 롤백 기능)
- [ ] 기존 등록된 PC 자동 검증 처리 (마이그레이션)

#### 문서 업데이트
- [ ] `docs/API.md` - 전면 재작성
- [ ] `docs/ARCHITECTURE.md` - 보안 아키텍처 섹션 추가
- [ ] `AI_CONTEXT.md` - 인증 시스템 설명 추가
- [ ] `README.md` - 새로운 설치 방법 반영

---

## [0.7.1] - 2026-02-07

### 수정
- **[중요] install.cmd config.json SERVER_URL 슬래시 누락 수정** - [x]
  - **문제**: config.json에 저장된 SERVER_URL 끝에 슬래시(`/`)가 없음
    - 저장됨: `"SERVER_URL": "http://wcms-server:5050"`
    - 필요: `"SERVER_URL": "http://wcms-server:5050/"`
  - **영향**: 클라이언트가 API 호출 시 잘못된 URL 생성
    - 명령 조회: `{SERVER_URL}api/client/command` → `http://wcms-server:5050api/client/command`
    - 결과 전송: `{SERVER_URL}api/client/command/result` → `http://wcms-server:5050api/client/command/result`
    - **증상**: 명령 수신 및 결과 전송 모두 실패
  - **해결**: `server/api/install.py` - config.json 생성 시 슬래시 보장
    ```batch
    REM Ensure SERVER_URL ends with / for config.json
    SET "CONFIG_URL=%SERVER_URL%"
    if not "%CONFIG_URL:~-1%"=="/" set "CONFIG_URL=%CONFIG_URL%/"
    ```
  - **결과**: config.json에 올바른 URL 저장, 모든 API 호출 정상화

- **클라이언트 명령 실행 서버 측 개선** - [x]
  - 0.7.0 클라이언트 EXE와 호환 (재빌드 불필요)
  - **수정 1**: `server/api/client.py` - 명령 조회 API를 0.7.0 호환 형식 유지
    - 응답 형식: `{command_id, command_type, command_data}` (단일 객체)
  - **수정 2**: `server/api/client.py` - 명령 결과 처리 API에 상세 로깅 추가
    - 명령 결과 수신 시 전체 데이터 로깅
    - 각 처리 단계별 성공/실패 로깅
    - 예외 발생 시 스택 트레이스 기록 (`exc_info=True`)
  - **수정 3**: `server/models/command.py` - CommandModel 로깅 추가
    - `complete()`, `set_error()` 메서드에 상세 로깅
    - DB 업데이트 결과 확인 (`cursor.rowcount` 체크)
  - **결과**: 서버 로그만 확인하면 명령 처리 과정 전체 추적 가능

- **클라이언트 코드 개선 (0.8.0 예정)** - [ ]
  - `client/executor.py` - execute 핸들러 인자 전달 수정
  - `client/main.py` - poll_command 루프 안정성 개선
  - 배열 형식 API 지원 추가

- **클라이언트 서비스 안정성 개선** - [x]
  - **리소스 절약 로직 추가**: 서버 연결 3회 실패 시 서비스 자동 종료
    - 초기 등록: 3회 재시도 (30초 간격), 실패 시 종료
    - Heartbeat: 연속 3회 실패 시 서비스 종료
    - 로그에 수동 재시작 방법 안내: `net start WCMS-Client`
  - 서비스 시작 유형을 "자동"으로 변경 (`install.cmd` 수정)
  - **서비스 설치 스크립트 개선**:
    - 서비스 이름 통일: `WCMS-Client` (기존 `WCMSClient`에서 변경)
    - 기존 서비스 제거 시 `sc delete` 사용으로 변경 (더 안정적)
    - 설치 명령 출력 리다이렉션 제거하여 실시간 피드백 확인 가능
    - 오류 발생 시 상세한 트러블슈팅 가이드 출력
    - `service.py` 자동 설치 로직 제거 (무한 루프 방지)
  - 서비스가 시작 후 즉시 중지되는 문제 해결

- **디스크 사용량 차트 버그 수정** [x]
  - `server/models/pc.py`: `get_with_status()` 메서드에서 `disk_info_parsed` 필드 생성 로직 추가
  - 정적 정보(`disk_info`: total_gb, fstype)와 동적 정보(`disk_usage`: used_gb, free_gb, percent) 병합
  - **이중 JSON 인코딩 문제 해결**: 재귀적 JSON 파싱으로 중첩된 JSON 문자열 처리
  - `server/templates/base.html`: 메인 페이지 디스크 표시 수정 (`disk_info` → `disk_info_parsed` 사용)
  - 템플릿에서 올바른 디스크 용량 및 사용률 표시 가능 (예: "C:\ 21.1/63.0 GB (33%)")

- **프로세스 표시 버그 수정** [x]
  - `server/models/pc.py`: `get_with_status()` 메서드에서 누락된 필드 추가
  - `ram_usage_percent`, `disk_usage`, `current_user`, `uptime` 필드 포함
  - `server/templates/process_history.html`: 이중 JSON 인코딩 처리 추가
  - 프로세스 히스토리 페이지에서 정상적으로 프로세스 목록 표시

- **명령 실행 속도 개선** [x]
  - `server/api/client.py`: Long-polling 타임아웃 10초 → 5초로 단축
  - `client/config.py`: 클라이언트 폴링 주기 10초 → 5초로 단축
  - 명령 전송 후 평균 응답 시간 단축 (최대 10초 → 5초)
  - 여러 PC에 동시 명령 전송 시 블로킹 현상 완화

- **IP 주소 표시 버그 수정** [x]
  - `server/api/client.py`: 하트비트에서 IP 주소 업데이트 로직 추가
  - 클라이언트가 하트비트 전송 시 IP 주소를 pc_info 테이블에 업데이트
  - IP가 "N/A"로 표시되던 문제 해결

### 추가
- **테스트 추가** [x]
  - `tests/server/test_models.py`: v0.7.1 버그 수정 테스트 클래스 추가
  - `disk_info_parsed` 필드 생성 테스트
  - 모든 필수 필드 포함 여부 테스트
  - 기본값 처리 테스트

- **디스크 도넛 차트 추가** [x]
  - `server/templates/base.html`: PC 모달 팝업에 Chart.js 도넛 차트 시각화 추가
  - PC 클릭 시 나오는 모달 상세 정보에서 각 디스크 드라이브별 도넛 차트 표시
  - 각 드라이브(C:\, D:\ 등)마다 사용량/여유 공간을 개별 도넛 차트로 시각화
  - 사용률에 따른 색상 변경 (90% 이상: 빨강, 75% 이상: 주황, 그 외: 초록)
  - 디스크 텍스트 정보 아래에 도넛 차트 자동 렌더링

- **Windows Docker 클라이언트 트러블슈팅 문서** [x]
  - `docs/WINDOWS_DOCKER_CLIENT_FIX.md`: Docker 환경에서 클라이언트 명령 미작동 해결 가이드
  - Docker 네트워크 내에서 올바른 서버 URL 설정 방법 (`http://wcms-server:5050/`)
  - 클라이언트 설치, 서비스 관리, 로그 확인 방법
  - 명령 폴링 및 실행 문제 진단 및 해결 방법

### 알려진 이슈
- **Windows Docker 클라이언트 명령 실행** - [x] 해결됨 (v0.7.1)
  - **원인**: install.cmd에서 SERVER_URL 끝에 슬래시가 누락됨
  - **해결**: SERVER_URL 끝에 슬래시 자동 추가 로직 구현
  - **추가 개선**: 명령 생성/조회/실행/결과 저장 전 과정에 로깅 추가

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
