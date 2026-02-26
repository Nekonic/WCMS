# WCMS 보안 취약점 수정 계획

자동화 스캔 도구(ZAP, CodeQL, pip-audit)의 보고서를 기반으로 발견된 취약점 및 수정 계획을 관리하는 문서.

---

## 스캔 보고서 위치

| 도구 | 보고서 위치 | 실행 조건 |
|------|------------|----------|
| OWASP ZAP (DAST) | GitHub Actions Artifacts → `zap-scan-report-{run}` (HTML/JSON) | push to main, PR, 매주 화요일 |
| CodeQL (SAST) | GitHub → Security → Code scanning alerts | push to main, PR, 매주 일요일 |
| pip-audit | GitHub Actions 로그 → `security-scan` 워크플로우 | push to main, PR, 매주 월요일 |

보고서 확인 경로: `https://github.com/Nekonic/WCMS/security` (Code scanning)

---

## 취약점 목록

> 상태: `[ ]` 미수정 / `[-]` 수정 완료 / `[~]` 부분 수정 / `[?]` 검토 필요

### ZAP (DAST) 발견 항목

| # | 항목 | 심각도 | 상태 | 비고 |
|---|------|--------|------|------|
| Z-01 | Content Security Policy: `unsafe-inline` 허용 | Medium | `[-]` | `style-src` unsafe-inline 제거, progress bar → data-width+JS |
| Z-02 | CORS: `/api/*` 전체 오리진 허용 (`origins: "*"`) | Medium | `[-]` | `WCMS_ALLOWED_ORIGINS` 환경변수로 제어 |
| Z-03 | Anti-CSRF 토큰 없음 (로그인 폼) | Low | `[-]` | Flask-WTF CSRFProtect 적용, API Blueprint 제외 |
| Z-04 | X-Content-Type-Options 헤더 | Low | `[-]` | Talisman이 자동 적용 |
| Z-05 | Referrer-Policy 헤더 | Info | `[ ]` | Talisman 설정에 추가 필요 |

### CodeQL (SAST) 발견 항목

| # | 항목 | 심각도 | 상태 | 비고 |
|---|------|--------|------|------|
| C-01 | `subprocess(shell=True)` 사용 | High | `[-]` | `shutdown/reboot/install/uninstall/net/taskkill/msg` 리스트 전환 |
| C-02 | 사용자 입력이 명령 파라미터로 전달 | High | `[-]` | 리스트 방식으로 쉘 주입 방지. `execute()`는 관리자 전용 유지 |
| C-03 | 민감 정보 로그 출력 가능성 | Low | `[ ]` | 예외 메시지에 내부 경로 포함 가능 |

### pip-audit 발견 항목

| # | 패키지 | CVE | 심각도 | 상태 | 수정 버전 |
|---|--------|-----|--------|------|----------|
| P-01 | _(최신 보고서 확인 후 기입)_ | - | - | `[ ]` | - |

> pip-audit 보고서는 CI 실행마다 갱신됨. 최신 결과를 위 표에 반영.

---

## 수정 계획

### [C-01, C-02] subprocess shell=True + 입력 주입

**위치**: `client/executor.py`

**문제**: `shell=True`로 실행 시 명령어 문자열에 삽입된 특수문자(`;`, `&`, `|` 등)로 추가 명령 실행 가능.

**계획**:
- `shutdown`, `reboot` 명령: 파라미터를 리스트로 전달 (`shell=False`)
- `execute` 명령: 관리자 직접 입력이므로 허용 범위 검토 후 결정
- `message`, `kill_process`: 인자 이스케이프 또는 리스트 전달

```python
# 수정 예시 (shutdown)
subprocess.run(['shutdown', '/s', '/t', str(delay)], shell=False)
```

---

### [Z-01] CSP unsafe-inline 제거

**위치**: `server/app.py` CSP 설정

**문제**: `style-src: unsafe-inline` 허용으로 XSS 공격 시 스타일 인젝션 가능.

**계획**:
- 인라인 CSS 제거 완료 후 (plan.md 인라인 CSS 항목) `unsafe-inline` 삭제 가능
- `script-src`는 이미 nonce 적용 중 (`content_security_policy_nonce_in=['script-src']`)
- `style-src`도 nonce 또는 hash 방식으로 전환

---

### [Z-02] CORS 오리진 제한

**위치**: `server/app.py`

```python
# 현재
CORS(app, resources={r"/api/*": {"origins": "*"}})

# 계획: 환경변수로 허용 오리진 지정
allowed = os.getenv('WCMS_ALLOWED_ORIGINS', '*').split(',')
CORS(app, resources={r"/api/*": {"origins": allowed}})
```

---

### [Z-03] CSRF 보호 적용

**위치**: `server/app.py`, 로그인 폼

**계획**:
- `flask-wtf`의 `CSRFProtect` 적용
- 로그인 폼에 `{{ form.hidden_tag() }}` 추가
- API 엔드포인트는 `@csrf.exempt` 처리 (토큰 인증으로 대체)

---

## 향후 스캔 실행 방법

```bash
# 로컬 pip-audit 실행
cd server && uv run pip-audit

# ZAP 로컬 실행 (Docker 필요)
docker run -t owasp/zap2docker-stable zap-baseline.py -t http://localhost:5050
```