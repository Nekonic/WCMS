# WCMS 개발 계획

> **진행 중**: v0.9.3
> 완료된 버전 이력: `docs/CHANGELOG.md`

---

## [v0.9.3] - 보안 강화 (ZAP 보고서 기반)

`docs/SECURITY_FINDINGS.md` 기반. ZAP 스캔 보고서(v0.9.2 기준) 신규 발견 항목.

### 신규 보안 항목

- [ ] SRI (Subresource Integrity): CDN 링크에 `integrity` 속성 추가
  - Font Awesome (`cdnjs.cloudflare.com`)
  - Chart.js (`cdn.jsdelivr.net`)
- [ ] Cross-Origin 헤더 추가 (Talisman 설정)
  - `Cross-Origin-Embedder-Policy: require-corp`
  - `Cross-Origin-Opener-Policy: same-origin`
  - `Cross-Origin-Resource-Policy: same-origin`
- [ ] `Permissions-Policy` 헤더 추가 (Talisman 설정)
- [ ] `Server` 헤더 버전 정보 노출 제거 (`Werkzeug/3.1.6 Python/3.9.25`)
  - Gunicorn 설정 또는 Flask after_request 훅으로 제거
- [ ] 로그인 500 에러 원인 조사
  - ZAP POST `/login` → HTTP 500, SQL 구문이 에러 페이지에 노출됨
  - CSRF 수정 후 재현 여부 확인 (이제 400 반환 예상)

---

## [v0.10.x ~] - 기능 추가 및 안정화

> v0.9.x 안정화 후 기능별로 버전 올리며 진행.

### 인증 강화
- [ ] 관리자 2FA (OTP 기반)

### 기능 확장
- [ ] 원격 데스크톱 (VNC 또는 RDP 통합)

### 모니터링
- [ ] 대시보드 개선 (실시간 리소스 그래프)
- [ ] 알림 시스템 (디스코드/슬랙)

### 테스트
- [ ] Docker E2E 테스트 강화