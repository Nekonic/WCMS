# WCMS 보안 가이드

> **버전**: v0.9.5
> **최종 업데이트**: 2026-03-03

---

## 목차

1. [보안 개요](#보안-개요)
2. [HTTPS 설정](#https-설정)
3. [환경변수 설정](#환경변수-설정)
4. [보안 기능](#보안-기능)
5. [보안 체크리스트](#보안-체크리스트)
6. [취약점 신고](#취약점-신고)

---

## 보안 개요

### 구현된 보안 기능

- HTTPS 지원 (SSL/TLS)
- 보안 헤더: HSTS, CSP, X-Frame-Options 등 (Flask-Talisman)
- Rate Limiting: 로그인 Brute-force 방어
- 세션 보안: Secure/HttpOnly 쿠키
- 입력 검증: SQL Injection, XSS 방어
- PIN 인증: 6자리 숫자 기반 클라이언트 등록
- bcrypt 해싱: 관리자 비밀번호 암호화

---

## HTTPS 설정

### Let's Encrypt 인증서 발급 (권장)

```bash
# Certbot 설치 (Linux)
sudo apt-get install certbot

# 인증서 발급
sudo certbot certonly --standalone -d your-domain.com

# 자동 갱신 (crontab)
0 3 * * * certbot renew --quiet --post-hook "systemctl restart wcms"
```

### 자체 서명 인증서 (개발/테스트용)

```bash
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
```

> 자체 서명 인증서는 브라우저 경고가 표시됩니다. 프로덕션에서는 사용하지 마세요.

### 환경변수로 인증서 경로 설정

```bash
export WCMS_SSL_CERT="/etc/letsencrypt/live/your-domain.com/fullchain.pem"
export WCMS_SSL_KEY="/etc/letsencrypt/live/your-domain.com/privkey.pem"
python manage.py run
```

---

## 환경변수 설정

### 필수 (프로덕션)

```bash
export WCMS_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
export WCMS_ENV="production"
export WCMS_SSL_CERT="/path/to/cert.pem"
export WCMS_SSL_KEY="/path/to/key.pem"
```

### 선택

```bash
export WCMS_DB_PATH="/var/lib/wcms/db.sqlite3"
export WCMS_LOG_LEVEL="INFO"
export WCMS_PORT="5050"
```

### Docker

`.env.docker` 파일:
```env
WCMS_ENV=production
WCMS_SECRET_KEY=your-random-secret-key-here
WCMS_SSL_CERT=/etc/ssl/certs/wcms.crt
WCMS_SSL_KEY=/etc/ssl/private/wcms.key
```

---

## 보안 기능

### 보안 헤더 (Flask-Talisman)

```http
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline' cdn.jsdelivr.net
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
```

### Rate Limiting

| 엔드포인트 | 제한 | 설명 |
|-----------|------|------|
| `/login` | 5회/분 | Brute-force 방어 |
| `/api/client/*` | 제한 없음 | 토큰 인증으로 보호 |
| `/api/admin/*` | 제한 없음 | 세션 인증으로 보호 |

### 세션 보안

```python
SESSION_COOKIE_SECURE = True      # HTTPS에서만 전송
SESSION_COOKIE_HTTPONLY = True    # JavaScript 접근 차단
SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF 보호
PERMANENT_SESSION_LIFETIME = 3600 # 1시간 만료
```

### 입력 검증 (`server/utils/validators.py`)

- hostname: 알파벳, 숫자, 하이픈, 언더스코어
- username: Windows 계정명 규칙 (1-20자)
- IP/MAC: 형식 검증
- PIN: 6자리 숫자
- 명령 타입: 화이트리스트

### SQL Injection 방어

모든 DB 쿼리는 파라미터화된 쿼리를 사용합니다:

```python
# 안전
db.execute('SELECT * FROM pcs WHERE id=?', (pc_id,))
```

---

## 보안 체크리스트

### 프로덕션 배포 전

- [ ] `WCMS_SECRET_KEY` 환경변수 설정 (랜덤 생성)
- [ ] HTTPS 인증서 설정
- [ ] `WCMS_ENV=production` 설정
- [ ] 기본 관리자 비밀번호 변경 (`admin`/`admin`)
- [ ] 데이터베이스 파일 권한 제한 (`chmod 600`)
- [ ] 방화벽 설정 (5050 포트)
- [ ] 정기 백업 설정

---

## 취약점 신고

- **GitHub Security Advisory**: https://github.com/Nekonic/WCMS/security/advisories/new

신고 시 포함 정보: 취약점 설명, 재현 방법, 영향 범위

대응 기준: Critical 7일 / High 14일 / Medium 30일