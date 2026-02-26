# WCMS 개발 계획

> **진행 중**: v0.9.2
> 완료된 버전 이력: `docs/CHANGELOG.md`

---

## [v0.9.2] - UI 정리 및 클라이언트 통신 개선

### 인라인 CSS 제거 (v0.9.1 미완)

`static/css/components.css` 생성 후 아래 템플릿에서 인라인 `style="..."` 제거.
공통 클래스: `.btn`, `.btn-primary/danger/warning`, `.panel`, `.modal`, `.table` 등.

- [ ] `static/css/components.css` 생성
- [ ] `about.html` 인라인 CSS 제거
- [ ] `system_status.html` 인라인 CSS 제거
- [ ] `layout_editor.html` 인라인 CSS 제거
- [ ] `room_manager.html` 인라인 CSS 제거
- [ ] `client_versions.html` 인라인 CSS 제거
- [ ] `registration_tokens.html` 인라인 CSS 제거
- [ ] `pc_detail.html` 인라인 CSS 제거
- [ ] `process_history.html` 인라인 CSS 제거
- [ ] `login.html` 인라인 CSS 제거

### 클라이언트 통신 방식 개선

**현황**: 2초 폴링 → 클라이언트 1대당 1,800 req/시간, 실습실 30대 기준 54,000 req/시간

**목표**:
- 폴링 주기 조정으로 네트워크 부하 절감
- 오프라인 판단을 타임아웃 기반에서 네트워크 연결 상태 기반으로 전환

**설계**:

- [ ] **명령 폴링 주기 조정**
  - 현재: 2초마다 `POST /api/client/commands` (경량 하트비트 포함)
  - 변경: 30초 수준으로 조정 (명령 응답성 vs 네트워크 부하 균형 실측 후 결정)

- [ ] **오프라인 감지 방식 변경**
  - 현재: 서버 백그라운드 워커가 `last_seen` 타임아웃으로 offline 판정
  - 변경: 클라이언트가 Windows 이벤트 또는 WMI로 NIC 연결 상태를 감지
    - NIC 연결 끊김 → 서버에 `POST /api/client/offline` 즉시 전송 시도
    - 서버 응답 불가(네트워크 단절) 시 → 서버는 짧은 타임아웃(폴링 주기 2배)으로 offline 판정
    - PreShutdown 이벤트(기존 구현) + NIC 단절 이벤트 두 경로 모두 처리

- [ ] **전체 하트비트 주기 검토** (현재 5분, 유지 또는 조정)

### 보안 취약점 수정 (v0.9.1 미완)

`docs/SECURITY_FINDINGS.md` 기반. CI 스캔 결과 확인 후 우선순위대로 수정.

- [ ] Z-01: CSP `style-src unsafe-inline` 제거 (인라인 CSS 제거 완료 후 가능)
- [ ] Z-02: CORS 오리진 `*` → 환경변수로 명시적 허용 오리진 지정
- [ ] Z-03: 로그인 폼 CSRF 보호 (`Flask-WTF CSRFProtect`)
- [ ] C-01/C-02: `client/executor.py` `subprocess(shell=True)` → 리스트 방식으로 교체

---

## [v0.10.x ~] - 기능 추가 및 안정화

> v0.9.x 안정화 후 기능별로 버전 올리며 진행.

### 인증 강화
- [ ] 관리자 2FA (OTP 기반)

### 기능 확장
- [ ] 로그 중앙화 (클라이언트 로그 → 서버 → 웹 UI 조회)
- [ ] 원격 데스크톱 (VNC 또는 RDP 통합)

### 모니터링
- [ ] 대시보드 개선 (실시간 리소스 그래프)
- [ ] 알림 시스템 (디스코드/슬랙)

### 테스트
- [ ] Docker E2E 테스트 강화 (서비스 등록/시작 자동 검증)