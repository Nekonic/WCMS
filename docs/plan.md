# WCMS 개발 계획

> **진행 중**: v0.9.1 (코드 정리 및 품질 개선)
> 완료된 버전 이력: `docs/CHANGELOG.md`

---

## [v0.9.1] - 코드 품질 개선 (진행 중)

### 버그 수정 (사전 분석 발견)
- [-] **클라이언트 API Rate Limit 제외** (`limiter.exempt(client_bp)`)
  - 코드 리뷰로 사전 발견: 2초 폴링(시간당 1,800회)이 전역 제한(50회/시간) 초과 예정
  - 실제 배포 전 수정, 실서비스 장애는 발생하지 않음
  - `docs/SECURITY.md` Rate Limit 표 업데이트
- [-] **ZAP/pip-audit CI 실패 처리 개선** (`continue-on-error: true`)

### 서버 코드 중복 제거
- [-] **`models/pc.py`**: `_to_json()` 헬퍼 추가 (4곳 중복 JSON 직렬화 통합)
- [-] **`api/admin.py`**: `_get_pc_or_404()`, `_queue_command()` 헬퍼 추가
  - PC 명령 6개 엔드포인트 중복 제거 (1163줄 → 921줄)
- [-] **`services/command_service.py`** 삭제 (173줄, 미사용 코드)

### CSS/JS 정적 파일 분리
- [-] **`base.html`** 인라인 CSS → `static/css/base.css`
- [-] **`index.html`** 인라인 CSS → `static/css/index.css`
- [-] **`base.html`** 인라인 JS → `static/js/modal.js`
- [-] **`index.html`** 인라인 JS → `static/js/pc-grid.js` + `static/js/commands.js`
- [-] `base.html`에 `{% block styles %}` 추가

### 인라인 CSS 제거 (UI 컴포넌트 통일)
- [ ] `static/css/components.css` 생성 (버튼, 패널, 폼, 테이블, 모달 공통 클래스)
- [ ] `about.html`, `system_status.html`, `layout_editor.html` 인라인 CSS 제거
- [ ] `room_manager.html`, `client_versions.html`, `registration_tokens.html` 인라인 CSS 제거
- [ ] `pc_detail.html`, `process_history.html`, `login.html` 인라인 CSS 제거

### 보안 취약점 수정
- [ ] 자동 스캔 보고서 기반 취약점 수정 (`docs/SECURITY_FINDINGS.md` 참고)

### 문서 정리
- [-] `docs/QUICK_REFERENCE.md` 삭제 (중복 내용)
- [-] `docs/INDEX.md` 삭제 (이모티콘, 중복)
- [-] `docs/archive/LEGACY_GUIDE.md` 삭제
- [-] `docs/CLIENT_AUTO_UPDATE.md` 내용을 `docs/ARCHITECTURE.md`로 통합
- [-] `docs/ARCHITECTURE.md` 최신 구조 반영 (이모티콘 제거, v0.9.1 구조 반영)
- [-] `AI_CONTEXT.md` 업데이트 (Addy Osmani AGENTS.md 기준, 권장 사항 형식)

---

## [v0.10.x ~] - 기능 추가 및 안정화

> v0.9.1 릴리스 후 기능별로 버전을 올려가며 진행.

### 인증 강화
- [ ] **관리자 2FA**: OTP 기반 2단계 인증 도입

### 기능 확장
- [ ] **로그 중앙화**: 클라이언트 로그를 서버로 전송하여 웹 UI에서 조회
- [ ] **원격 데스크톱**: VNC 또는 RDP 통합
- [ ] **파일 배포**: 서버에서 클라이언트로 파일 전송 기능 강화

### 모니터링 및 알림
- [ ] **대시보드 개선**: 실시간 리소스 사용량 그래프
- [ ] **알림 시스템**: 장애 발생 시 디스코드/슬랙 알림

### 테스트 및 품질
- [ ] **Docker E2E 테스트 강화**: 컨테이너 내 서비스 등록/시작 검증 자동화
- [ ] **CPU 부하 테스트**: 성능/안정성 테스트용 명령 추가