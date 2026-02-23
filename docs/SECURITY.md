# WCMS 보안 가이드

> **버전**: v0.9.0
> **최종 업데이트**: 2026-02-24

---

## 📋 목차

1. [보안 개요](#보안-개요)
2. [HTTPS 설정](#https-설정)
3. [환경변수 설정](#환경변수-설정)
4. [보안 기능](#보안-기능)
5. [보안 체크리스트](#보안-체크리스트)
6. [취약점 신고](#취약점-신고)

---

## 보안 개요

WCMS v0.9.0부터 다음과 같은 보안 기능이 추가되었습니다:

### ✅ 구현된 보안 기능

- **HTTPS 지원**: SSL/TLS 암호화 통신
- **보안 헤더**: HSTS, CSP, X-Frame-Options 등
- **Rate Limiting**: Brute-force 공격 방어
- **세션 보안**: Secure/HttpOnly 쿠키
- **입력 검증**: SQL Injection, XSS 방어
- **PIN 인증**: 6자리 숫자 기반 클라이언트 등록
- **bcrypt 해싱**: 관리자 비밀번호 암호화

---

## HTTPS 설정

### 1. Let's Encrypt 인증서 발급 (권장)

#### Linux/Docker 환경
```bash
# Certbot 설치
sudo apt-get update
sudo apt-get install certbot

# 인증서 발급 (Standalone 모드)
sudo certbot certonly --standalone -d your-domain.com

# 인증서 경로 확인
ls /etc/letsencrypt/live/your-domain.com/
# - fullchain.pem (인증서)
# - privkey.pem (개인키)
```

#### 자동 갱신 설정
```bash
# 크론탭에 추가 (매일 자동 갱신 시도)
sudo crontab -e
# 다음 줄 추가:
0 3 * * * certbot renew --quiet --post-hook "systemctl restart wcms"
```

### 2. 자체 서명 인증서 (개발/테스트용)

```bash
# OpenSSL로 자체 서명 인증서 생성
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# 생성된 파일:
# - cert.pem (인증서)
# - key.pem (개인키)
```

⚠️ **주의**: 자체 서명 인증서는 브라우저에서 경고가 표시되며, 프로덕션 환경에서는 사용하지 마세요.

### 3. 환경변수 설정

```bash
# 인증서 경로 설정
export WCMS_SSL_CERT="/etc/letsencrypt/live/your-domain.com/fullchain.pem"
export WCMS_SSL_KEY="/etc/letsencrypt/live/your-domain.com/privkey.pem"

# 서버 시작
python manage.py run
```

### 4. 클라이언트 설정 변경

클라이언트는 HTTPS 엔드포인트로 연결해야 합니다:

```json
// C:\ProgramData\WCMS\config.json
{
  "SERVER_URL": "https://your-domain.com:5050/",
  "MACHINE_ID": "...",
  "REGISTRATION_PIN": "..."
}
```

---

## 환경변수 설정

### 필수 환경변수 (프로덕션)

```bash
# SECRET_KEY: Flask 세션 암호화 키 (랜덤 생성 권장)
export WCMS_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"

# 환경 모드
export WCMS_ENV="production"

# SSL 인증서 (HTTPS 사용 시)
export WCMS_SSL_CERT="/path/to/cert.pem"
export WCMS_SSL_KEY="/path/to/key.pem"
```

### 선택 환경변수

```bash
# 데이터베이스 경로
export WCMS_DB_PATH="/var/lib/wcms/db.sqlite3"

# 로그 레벨
export WCMS_LOG_LEVEL="INFO"

# 서버 포트
export WCMS_PORT="5050"
```

### Docker 환경

`.env.docker` 파일에 환경변수를 설정하세요:

```env
WCMS_ENV=production
WCMS_SECRET_KEY=your-random-secret-key-here
WCMS_SSL_CERT=/etc/ssl/certs/wcms.crt
WCMS_SSL_KEY=/etc/ssl/private/wcms.key
```

---

## 보안 기능

### 1. 보안 헤더

v0.9.0부터 Flask-Talisman을 통해 다음 헤더가 자동 적용됩니다:

```http
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline' cdn.jsdelivr.net
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
```

### 2. Rate Limiting

| 엔드포인트 | 제한 | 설명 |
|-----------|------|------|
| `/login` | 5회/분 | Brute-force 공격 방어 |
| `/api/client/register` | 10회/시간 | 대량 등록 차단 |
| 기타 API | 50회/시간 | 일반 트래픽 제한 |

### 3. 세션 보안

```python
# 세션 쿠키 설정 (config.py)
SESSION_COOKIE_SECURE = True      # HTTPS에서만 전송
SESSION_COOKIE_HTTPONLY = True    # JavaScript 접근 차단
SESSION_COOKIE_SAMESITE = 'Lax'   # CSRF 보호
PERMANENT_SESSION_LIFETIME = 3600 # 1시간 만료
```

### 4. 입력 검증

모든 사용자 입력은 `server/utils/validators.py`에서 검증됩니다:

- **hostname**: 알파벳, 숫자, 하이픈, 언더스코어만 허용
- **username**: Windows 계정명 규칙 (1-20자, 특수문자 제한)
- **IP 주소**: IPv4 형식 검증
- **MAC 주소**: XX:XX:XX:XX:XX:XX 형식
- **PIN**: 6자리 숫자
- **명령 타입**: 화이트리스트 방식

### 5. SQL Injection 방어

모든 DB 쿼리는 파라미터화된 쿼리를 사용합니다:

```python
# ✅ 안전 (파라미터화)
db.execute('SELECT * FROM pc_info WHERE id=?', (pc_id,))

# ❌ 위험 (문자열 연결)
db.execute(f'SELECT * FROM pc_info WHERE id={pc_id}')
```

---

## 보안 체크리스트

### 프로덕션 배포 전 필수 확인사항

- [ ] `WCMS_SECRET_KEY` 환경변수 설정 (랜덤 생성)
- [ ] HTTPS 인증서 설정 (Let's Encrypt)
- [ ] `WCMS_ENV=production` 설정
- [ ] 기본 관리자 비밀번호 변경 (`admin`/`admin` → 강력한 비밀번호)
- [ ] 데이터베이스 파일 권한 제한 (`chmod 600`)
- [ ] 로그 파일 권한 제한
- [ ] 방화벽 설정 (5050 포트만 허용)
- [ ] 정기적인 백업 설정
- [ ] 클라이언트 자동 업데이트 활성화

### 개발 환경 확인사항

- [ ] `WCMS_ENV=development` 설정
- [ ] 자체 서명 인증서 사용 (선택)
- [ ] 디버그 모드 활성화

---

## 취약점 신고

보안 취약점을 발견하신 경우 다음 절차를 따라주세요:

### 1. 신고 방법

- **GitHub Security Advisory**: https://github.com/Nekonic/WCMS/security/advisories/new
- **이메일**: (프로젝트 관리자 이메일 추가)

### 2. 신고 시 포함 정보

- 취약점 설명
- 재현 방법 (PoC)
- 영향 범위
- 제안 해결책 (선택)

### 3. 대응 절차

1. 신고 접수 (24시간 내 응답)
2. 취약점 검증 및 분류
3. 패치 개발 (Critical: 7일, High: 14일, Medium: 30일)
4. 보안 업데이트 릴리스
5. CVE 발급 (필요 시)

---

## 보안 모범 사례

### 관리자

1. **강력한 비밀번호 사용**: 최소 12자, 대소문자/숫자/특수문자 혼합
2. **정기적인 비밀번호 변경**: 3개월마다 변경 권장
3. **등록 토큰 관리**: 1회용 토큰 사용, 사용 후 즉시 삭제
4. **로그 모니터링**: 비정상 로그인 시도 확인
5. **정기 업데이트**: 보안 패치 즉시 적용

### 시스템 관리자

1. **최소 권한 원칙**: 서버는 전용 계정으로 실행
2. **네트워크 분리**: 관리 네트워크와 클라이언트 네트워크 분리
3. **백업**: 일일 자동 백업 설정
4. **감사 로그**: 모든 관리자 작업 기록
5. **의존성 업데이트**: 정기적인 라이브러리 업데이트

---

**문서 버전**: 1.0
**최종 업데이트**: 2026-02-24
**작성자**: WCMS Team
