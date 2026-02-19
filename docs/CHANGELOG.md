# 변경 이력

프로젝트의 주요 변경사항을 기록합니다.

형식: [Keep a Changelog](https://keepachangelog.com/ko/1.0.0/)  
버전 관리: [Semantic Versioning](https://semver.org/lang/ko/)

---

## [0.8.8] - 2026-02-18

> **상태**: Released  
> **테마**: 버그 수정 및 기능 완성도 향상

### Added - 새로운 기능
- [x] **계정 생성 시 언어 설정 구현**
  - `RunOnce` 레지스트리를 활용하여 사용자 최초 로그인 시 언어 설정(`Set-WinUserLanguageList`)이 적용되도록 구현
  - 지원 언어: 한국어, 영어, 중국어, 몽골어

### Changed - 변경사항
- [x] **계정 관리 UI 개선**
  - 불필요한 키보드 레이아웃 설정 제거 (언어 설정에 따라 자동 적용됨)
  - 일괄 계정 관리 모달 UI 최적화
- [x] **메뉴 정리**
  - 사용하지 않는 `/account/manager` 라우트 및 메뉴 링크 제거 (일괄 관리로 통합)

### Fixed - 버그 수정
- [x] **토큰 삭제 버그 수정**
  - 토큰 삭제 시 ID 대신 토큰 문자열을 사용하여 삭제되지 않던 문제 해결 (`token.id` 사용)

---

## [0.8.7] - 2026-02-18

> **상태**: Released  
> **테마**: 자동 업데이트, 프로그램 관리, 계정 생성 옵션

### Added - 새로운 기능
- [x] **클라이언트 자동 업데이트**
  - 클라이언트가 서버에서 새 버전을 감지하고 자동으로 업데이트
  - `install.cmd` 또는 별도의 업데이트 스크립트를 다운로드하여 실행
  - 서비스 중지 -> 파일 교체 -> 서비스 시작 프로세스 자동화
- [x] **프로그램 삭제**
  - `chocolatey`를 사용하여 프로그램을 삭제하는 기능 추가
  - `/api/admin/pc/{pc_id}/uninstall` 엔드포인트 추가
- [x] **계정 생성 옵션**
  - 윈도우 계정 생성 시 언어 설정 파라미터 추가 (`language`)

### Changed - 변경사항
- [x] **계정 관리 UI 개선**
  - 일괄 계정 관리 모달에서 언어 설정 옵션 추가

---

## [0.8.6] - 2026-02-11

> **상태**: Released  
> **테마**: 안정성 강화, Chocolatey 도입, UI 개선

### Added - 새로운 기능
- [x] **Chocolatey 지원**
  - `winget` 대신 `chocolatey`를 사용하여 프로그램 설치
  - 서비스 환경(`LocalSystem`)에서도 안정적인 설치 지원
  - Chocolatey 미설치 시 자동 설치 기능 추가
- [x] **UI 개선**
  - 계정 관리 모달: 작업 유형 선택 및 동적 입력 필드 제공
  - 전원 관리 모달: 종료/재시작 버튼 제공
  - 프로세스 종료 모달: 수집된 프로세스 목록에서 선택 가능 (`datalist`)
  - PC 상세 정보: RAM 사용량 도넛 차트 추가
- [x] **프로세스 목록 조회 API**
  - `GET /api/admin/processes`: 수집된 프로세스 목록 조회 (중복 제거)

### Changed - 변경사항
- [x] **서비스 설치 방식 개선**
  - `install.cmd`에서 `sc create`를 사용하여 서비스 직접 등록 (안정성 향상)
  - 서비스 시작 유형을 `delayed-auto` (지연된 자동 시작)로 설정하여 부팅 시 안정성 확보
  - 서비스 실패 시 자동 재시작 설정 추가 (`sc failure`)
- [x] **명령 실행 개선**
  - `download` 명령: `destination` 파라미터 지원 (저장 경로 지정 가능)
  - `install` 명령: `app_id` 파라미터 사용 (기존 `app_name` 혼용 해결)

### Fixed - 버그 수정
- [x] 서비스 재시작 시 자동 시작되지 않는 문제 해결
- [x] `install.cmd` 실행 시 멈추는 현상 해결
- [x] `winget`이 서비스 계정에서 실행되지 않는 문제 해결 (Chocolatey로 대체)

---

## [0.8.5] - 2026-02-11

> **상태**: Yanked (서비스 설치 문제)  
> **테마**: Chocolatey 도입 시도

---

## [0.8.4] - 2026-02-11

> **상태**: Released (Internal)  
> **테마**: 서비스 시작 로직 수정

### Fixed - 버그 수정
- [x] **서비스 시작 로직 수정**
  - `client/service.py`: 인자 없이 실행될 때 서비스 디스패처 연결 시도하도록 수정
  - `install.cmd`: `binPath`에서 `start` 인자 제거 (서비스 표준 방식 준수)

---

## [0.8.3] - 2026-02-11

> **상태**: Released (Internal)  
> **테마**: 설치 스크립트 개선

### Changed - 변경사항
- [x] **설치 스크립트 개선**
  - `install.cmd`: PowerShell 호출 방식 변경 (`Start-Process` 사용)
  - 경로 공백 처리 및 따옴표 문제 해결 시도

---

## [0.8.2] - 2026-02-11

> **상태**: Released  
> **테마**: 클라이언트 안정성 및 데이터 무결성

### Fixed - 버그 수정
- [x] **프로세스 중복 실행 방지**
  - `client/service.py`: 인자 없이 실행 시 자동 설치 로직 제거
- [x] **JSON 이중 인코딩 해결**
  - `client/collector.py`: 데이터를 JSON 문자열로 미리 변환하지 않고 객체 그대로 반환
  - 서버에서 이중으로 인코딩되어 DB에 저장되는 문제 해결
- [x] **중복 등록 방지**
  - `client/main.py`: `registered.flag` 파일을 사용하여 불필요한 재등록 방지
- [x] **디스크 정보 수집 개선**
  - 고정 디스크(`fixed`)만 수집하도록 필터링 추가

---

## [0.8.0] - 2026-02-10

> **상태**: Released  
> **테마**: 보안 강화, 네트워크 최적화, RESTful API 개선

### Added - 새로운 기능

#### PIN 인증 시스템
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

#### 네트워크 성능 최적화
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

#### API 개선 (Breaking Changes)
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

#### 데이터베이스 스키마 변경
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

---

## [0.7.1] - 2026-02-07

### 수정
- **[중요] install.cmd config.json SERVER_URL 슬래시 누락 수정** - [x]
- **클라이언트 명령 실행 서버 측 개선** - [x]
- **클라이언트 서비스 안정성 개선** - [x]
- **디스크 사용량 차트 버그 수정** [x]
- **프로세스 표시 버그 수정** [x]
- **명령 실행 속도 개선** [x]
- **IP 주소 표시 버그 수정** [x]

### 추가
- **테스트 추가** [x]
- **디스크 도넛 차트 추가** [x]
- **Windows Docker 클라이언트 트러블슈팅 문서** [x]

---

## [0.7.0] - 2026-02-07

### 추가
- **한 줄 설치 스크립트 구현 (Phase 2 완료)** [x]
- **클라이언트 서버 URL 설정 개선** [x]
- **문서 정리** [x]
- **Docker 통합 테스트 인프라 구축** [x]
- **Windows 백업 및 복원 시스템** [x]
- **PreShutdown 종료 감지 기능 완료** [x]
- **테스트 환경 개선** [x]
- **AI 컨텍스트 파일 생성** [x]
- **서버 모듈화 완료** (Phase 1 - 100%)
- **클라이언트 개선** (Phase 2 - 60%)

### 변경
- 서버 아키텍처: 단일 파일 (1,270줄) → 모듈화 (13개 파일, 2,680줄)
- 설계 패턴 적용: Repository, Blueprint, Service 레이어
- 타입 힌팅 추가 (모든 새 함수)
- 문서 구조: 명확한 역할 분리 및 중복 제거
- 프로젝트 구조 정리: archive, tests, docs, db, scripts 디렉토리 분리

### 수정
- **Docker 서버 DB 초기화 수정** [x]
- **Docker 헬스체크 타임아웃 개선** [x]
- **[중요] CommandModel 스키마 호환성 버그 수정**

---

## [0.6.0] - 2025-12-04

### 추가
- **일괄 명령 전송 기능 확장**
- **명령 초기화 시스템**
- **PC 상세 정보 향상**

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
