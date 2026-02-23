# WCMS 개발 계획

> **현재 버전**: v0.8.11 (Released)
> **목표 버전**: v0.9.0 (작업 완료 → 테스트 후 릴리스 예정)

---

## [v0.9.0] - 서버 보안 강화 (2026-02-24 완료)

### 1. HTTPS 지원 ✅
- [x] **인증서 발급 및 적용**
  - 환경변수로 SSL 인증서 경로 설정 (`WCMS_SSL_CERT`, `WCMS_SSL_KEY`)
  - Flask 서버(`app.py`)에 SSL 컨텍스트 적용
  - Let's Encrypt 가이드 작성 (`docs/SECURITY.md`)

### 2. 웹 보안 강화 ✅
- [x] **보안 헤더 적용**
  - `Flask-Talisman` 도입 완료
  - HSTS (HTTP Strict Transport Security) 적용
  - CSP (Content Security Policy) 설정
  - X-Frame-Options, X-Content-Type-Options 자동 적용
- [x] **Rate Limiting 강화**
  - `Flask-Limiter` 도입 완료
  - 로그인 엔드포인트: 5회/분 제한 (Brute-force 방어)
  - 전역 제한: 50회/시간, 200회/일
- [x] **robots.txt 생성**
  - `/robots.txt` 엔드포인트 구현
  - 검색 엔진 크롤링 차단 (`Disallow: /`)

### 3. SECRET_KEY 보안 강화 ✅
- [x] **하드코딩 제거**
  - 프로덕션 환경에서 `WCMS_SECRET_KEY` 환경변수 필수화
  - 개발 환경에서만 기본값 사용
  - 랜덤 키 생성 가이드 제공

### 4. 세션 보안 강화 ✅
- [x] **쿠키 보안 설정**
  - `SESSION_COOKIE_SECURE=True` (HTTPS 전용)
  - `SESSION_COOKIE_HTTPONLY=True` (XSS 방어)
  - `SESSION_COOKIE_SAMESITE='Lax'` (CSRF 보호)
  - 세션 만료 시간: 1시간

### 5. 입력 검증 강화 ✅
- [x] **validators.py 확장**
  - `validate_username()`: Windows 계정명 검증
  - `validate_pin()`: 6자리 PIN 검증
  - `sanitize_path()`: 경로 탐색 공격 방어
  - 기존 검증 함수 개선 (hostname, IP, MAC 주소)

### 6. 보안 문서화 ✅
- [x] **SECURITY.md 작성**
  - HTTPS 설정 가이드 (Let's Encrypt, 자체 서명)
  - 환경변수 설정 가이드
  - 보안 체크리스트
  - 취약점 신고 절차

### 7. 소개 페이지 제작 ✅
- [x] **about.html 템플릿 작성**
  - 프로젝트 개요, 주요 기능, 기술 스택, 버전 정보, 링크 섹션
  - 다크 테마 일관성 유지
- [x] **`/about` 라우트 구현** (`app.py`)

### 8. 취약점 점검 자동화 ✅
- [x] **SAST (정적 분석)**
  - `.github/workflows/codeql.yml` 추가
  - Python 코드 정적 분석, security-and-quality 쿼리 적용
  - push/PR/주간 스케줄 트리거
- [x] **DAST (동적 분석)**
  - `.github/workflows/zap.yml` 추가
  - Flask 서버 로컬 실행 후 OWASP ZAP baseline 스캔
  - SARIF 결과를 GitHub Security 탭으로 연동
  - `.github/zap-rules.tsv` 로 false-positive 규칙 제어
- [x] **의존성 스캔**
  - `.github/dependabot.yml` 추가 (pip + GitHub Actions 주간 업데이트)
  - `.github/workflows/security_scan.yml` 추가 (pip-audit 스캔)

---

## [Backlog] - 향후 계획

### 인증 강화
- [ ] **관리자 2FA (2단계 인증)**: OTP 기반 2단계 인증 도입

### 기능 확장
- [ ] **로그 중앙화**: 클라이언트 로그를 서버로 전송하여 웹 UI에서 조회
- [ ] **원격 데스크톱**: VNC 또는 RDP 통합
- [ ] **파일 배포**: 서버에서 클라이언트로 파일 전송 기능 강화

### 모니터링 및 알림
- [ ] **대시보드 개선**: 실시간 리소스 사용량 그래프 (Grafana 연동 고려)
- [ ] **알림 시스템**: 장애 발생 시 디스코드/슬랙 알림

### 테스트 및 품질
- [ ] **Docker E2E 테스트 강화**: Docker 컨테이너 내 서비스 등록/시작 검증 자동화
- [ ] **CPU 부하 테스트**: 클라이언트에 CPU 부하를 발생시키는 명령 추가 (성능/안정성 테스트용)
