# WCMS 개발 계획

> **현재 버전**: v0.8.8 (Released)
> **목표 버전**: v0.9.0

---

## [v0.9.0] - 서버 보안 강화 및 모니터링 개선

### 1. HTTPS 지원 (Let's Encrypt)
- [ ] **인증서 발급 및 적용**
  - `certbot`을 이용한 Let's Encrypt 인증서 발급
  - Flask 서버(`app.py`)에 SSL 컨텍스트 적용 (`ssl_context`)
  - HTTP 요청을 HTTPS로 리다이렉트

### 2. 웹 보안 강화
- [ ] **보안 헤더 적용**
  - `Flask-Talisman` 도입
  - HSTS (HTTP Strict Transport Security) 적용
  - CSP (Content Security Policy) 설정
  - X-Frame-Options, X-Content-Type-Options 등 설정
- [ ] **Rate Limiting 강화**
  - `Flask-Limiter`를 사용하여 로그인 시도 횟수 제한 (Brute-force 방지)
- [ ] **robots.txt 생성**
  - 검색 엔진 크롤링 제어 (`User-agent: *`, `Disallow: /`)

### 3. 취약점 점검 자동화 (DevSecOps)
- [ ] **SAST (정적 분석)**
  - GitHub Actions에 CodeQL 워크플로우 추가
- [ ] **DAST (동적 분석)**
  - GitHub Actions에 OWASP ZAP 워크플로우 추가

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
