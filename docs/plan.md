# WCMS 개발 계획

> **현재 버전**: v0.8.6 (Released)
> **목표 버전**: v0.8.7

---

## [v0.8.7] - 클라이언트 자동 업데이트 및 프로그램 관리 강화

### 1. 클라이언트 자동 업데이트
- [x] **자동 업데이트 로직 구현**
  - `client/main.py`: `check_for_updates` 함수 개선
  - 새 버전 감지 시 `install.cmd` 또는 별도의 업데이트 스크립트 다운로드 및 실행
  - 서비스 중지 -> 파일 교체 -> 서비스 시작 프로세스 자동화

### 2. 프로그램 삭제
- [x] **프로그램 삭제 명령 추가**
  - `server/api/admin.py`: `/pc/<int:pc_id>/uninstall` 엔드포인트 추가
  - `client/executor.py`: `uninstall` 명령 처리 로직 추가 (Chocolatey 활용)

### 3. 윈도우 계정생성에서 언어 설정 지원
- [x] **계정 생성 시 언어 설정 파라미터 추가**
  - `server/api/admin.py`: `create_account` API에 `language` 파라미터 추가
  - `client/executor.py`: `create_user` 함수에 파라미터 전달 및 `RunOnce` 레지스트리 등록 로직 구현
  - `server/templates/index.html`: 일괄 계정 생성 모달에 언어 선택 옵션 추가

---

## [Backlog] - 향후 계획

### 보안 강화 (DevSecOps)
- [ ] **취약점 검사 자동화**: OWASP ZAP을 활용한 DAST(동적 애플리케이션 보안 테스트) GitHub Actions 워크플로우 구축
- [ ] **코드 보안 분석**: CodeQL을 이용한 SAST(정적 애플리케이션 보안 테스트) 적용
- [ ] **HTTPS 지원**: Let's Encrypt 인증서 자동 발급 및 갱신
- [ ] **관리자 2FA**: OTP 기반 2단계 인증 도입
- [ ] **의존성 보안**: Dependabot 설정으로 라이브러리 취약점 관리

### 테스트 및 품질
- [ ] **Docker E2E 테스트 강화**: Docker 컨테이너 내 서비스 등록/시작 검증 자동화
- [ ] **CPU 부하 테스트**: 클라이언트에 CPU 부하를 발생시키는 명령 추가 (성능/안정성 테스트용)

### 기능 확장
- [ ] **로그 중앙화**: 클라이언트 로그를 서버로 전송하여 웹 UI에서 조회
- [ ] **원격 데스크톱**: VNC 또는 RDP 통합
- [ ] **파일 배포**: 서버에서 클라이언트로 파일 전송 기능 강화

### 모니터링
- [ ] **대시보드 개선**: 실시간 리소스 사용량 그래프 (Grafana 연동 고려)
- [ ] **알림 시스템**: 장애 발생 시 디스코드 알림
