# WCMS 프로덕션 배포 가이드

> 개발 환경 설정은 [GETTING_STARTED.md](GETTING_STARTED.md), 보안 세부 설정(HTTPS, 리버스 프록시)은 [SECURITY.md](SECURITY.md) 참고.

---

## 목차

1. [요구사항](#1-요구사항)
2. [설치](#2-설치)
3. [환경변수 설정](#3-환경변수-설정)
4. [DB 초기화 및 첫 실행 확인](#4-db-초기화-및-첫-실행-확인)
5. [systemd 서비스 등록](#5-systemd-서비스-등록)
6. [클라이언트 설치 스크립트 설정](#6-클라이언트-설치-스크립트-설정)
7. [리버스 프록시 연결](#7-리버스-프록시-연결)
8. [운영 관리](#8-운영-관리)
9. [업데이트](#9-업데이트)
10. [문제 해결](#10-문제-해결)

---

## 1. 요구사항

| 항목 | 최소 | 권장 |
|------|------|------|
| OS | Ubuntu 20.04+ / Debian 11+ | Ubuntu 22.04 LTS |
| Python | 3.9 | 3.11+ |
| RAM | 512 MB | 1 GB |
| 디스크 | 1 GB | 5 GB |
| 네트워크 | 포트 5050 개방 | 80/443 (리버스 프록시) |

```bash
# uv 설치
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/env
```

---

## 2. 설치

```bash
# 전용 사용자 생성 (권장)
sudo useradd -r -s /bin/false -d /opt/wcms wcms
sudo mkdir -p /opt/wcms
sudo git clone https://github.com/Nekonic/WCMS.git /opt/wcms
sudo chown -R wcms:wcms /opt/wcms

# 의존성 설치
cd /opt/wcms
sudo -u wcms python3 manage.py install
```

---

## 3. 환경변수 설정

환경변수 파일을 생성합니다:

```bash
sudo mkdir -p /etc/wcms
sudo nano /etc/wcms/env
```

```env
# /etc/wcms/env

# [필수] Flask 세션 서명 키 — 랜덤 생성값 사용
WCMS_SECRET_KEY=<python3 -c 'import secrets; print(secrets.token_hex(32))' 실행 후 붙여넣기>

# [필수] 프로덕션 모드
WCMS_ENV=production

# [선택] HTTPS 직접 종료 시 (리버스 프록시 사용 시 불필요)
# WCMS_SSL_CERT=/etc/letsencrypt/live/your-domain.com/fullchain.pem
# WCMS_SSL_KEY=/etc/letsencrypt/live/your-domain.com/privkey.pem

# [선택] DB 경로 (기본: /opt/wcms/server/db.sqlite3)
WCMS_DB_PATH=/var/lib/wcms/db.sqlite3

# [선택] 허용 CORS 오리진 (기본: *)
# WCMS_ALLOWED_ORIGINS=https://your-domain.com

# [선택] 클라이언트 버전 자동 등록 토큰 (GitHub Actions 연동 시)
UPDATE_TOKEN=<랜덤 값>
```

파일 권한을 제한합니다 (`wcms` 그룹이 읽을 수 있도록 640):

```bash
sudo chmod 640 /etc/wcms/env
sudo chown root:wcms /etc/wcms/env
```

> `WCMS_SECRET_KEY` 생성:
> ```bash
> python3 -c 'import secrets; print(secrets.token_hex(32))'
> ```

---

## 4. DB 초기화 및 첫 실행 확인

```bash
# DB 디렉토리 생성 (WCMS_DB_PATH 변경 시)
sudo mkdir -p /var/lib/wcms
sudo chown wcms:wcms /var/lib/wcms

# DB 초기화 (관리자 계정 생성)
cd /opt/wcms
export $(sudo cat /etc/wcms/env | xargs)
python3 manage.py init-db <관리자ID> <비밀번호>

# 프로덕션 모드 단발 실행으로 정상 동작 확인
python3 manage.py run --prod
# → http://서버IP:5050 에서 응답 확인 후 Ctrl+C
```

---

## 5. systemd 서비스 등록

```bash
sudo nano /etc/systemd/system/wcms.service
```

```ini
[Unit]
Description=WCMS - Woosuk Computer Management System
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=wcms
Group=wcms
WorkingDirectory=/opt/wcms
EnvironmentFile=/etc/wcms/env
Environment=PYTHONPATH=/opt/wcms/server

ExecStart=/opt/wcms/server/.venv/bin/gunicorn \
    -k gevent -w 1 --worker-connections 1000 \
    -b 0.0.0.0:5050 --timeout 120 \
    app:app
ExecReload=/bin/kill -HUP $MAINPID

Restart=on-failure
RestartSec=5
StartLimitBurst=3
StartLimitIntervalSec=60

# 로그를 systemd journal로 통합
StandardOutput=append:/var/log/wcms/server.log
StandardError=append:/var/log/wcms/server.log

# 보안 강화
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/opt/wcms /var/lib/wcms /var/log/wcms

[Install]
WantedBy=multi-user.target
```

```bash
# 로그 디렉토리 생성
sudo mkdir -p /var/log/wcms
sudo chown wcms:wcms /var/log/wcms

# 서비스 활성화 및 시작
sudo systemctl daemon-reload
sudo systemctl enable wcms
sudo systemctl start wcms

# 상태 확인
sudo systemctl status wcms
```

---

## 6. 클라이언트 설치 스크립트 설정

Windows 클라이언트 설치 스크립트(`install.cmd`, `install.ps1`)는 서버에서 동적으로 생성되며, 설치 시 서버 DB에 등록된 클라이언트 버전의 다운로드 URL을 참조합니다. 서버 시작 후 반드시 클라이언트 버전을 등록해야 합니다.

### 클라이언트 버전 등록

#### 방법 1: UPDATE_TOKEN으로 등록 (권장)

`/etc/wcms/env`에 `UPDATE_TOKEN`을 설정한 뒤 서비스를 재시작하고, 아래 명령으로 버전을 등록합니다:

```bash
curl -X POST http://localhost:5050/api/client/version \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <UPDATE_TOKEN 값>" \
  -d '{
    "version": "0.9.7",
    "download_url": "https://github.com/Nekonic/WCMS/releases/download/client-v0.9.7/WCMS-Client.exe",
    "changelog": "v0.9.7 릴리스"
  }'
```

#### 방법 2: 관리자 웹 UI

브라우저에서 `http://서버주소:5050` 로그인 → **클라이언트 버전 관리** 페이지에서 직접 등록.

#### 방법 3: GitHub Actions 자동 등록

`client-v*` 태그를 push하면 `build_client.yml`이 빌드 완료 후 서버에 자동 등록합니다. `UPDATE_TOKEN`이 환경변수에 설정되어 있어야 합니다.

```bash
# /etc/wcms/env에 추가
UPDATE_TOKEN=<랜덤 생성값>
```

GitHub Repository → Settings → Secrets → `UPDATE_TOKEN`, `SERVER_URL` 시크릿 등록 필요.

### 버전 등록 확인

```bash
curl http://localhost:5050/api/client/version
# {"version":"0.9.7","download_url":"https://...","status":"success"}
```

### 설치 스크립트 배포

서버가 실행 중이면 아래 URL에서 설치 스크립트를 즉시 다운로드할 수 있습니다:

| 스크립트 | URL |
|---------|-----|
| Windows CMD | `http://서버주소:5050/install/install.cmd` |
| PowerShell | `http://서버주소:5050/install/install.ps1` |

서버 URL을 명시적으로 지정하려면 `?server=` 파라미터를 사용합니다:

```
http://서버주소:5050/install/install.cmd?server=http://서버주소:5050
```

**Windows 클라이언트 설치 명령 (CMD, 관리자 권한):**

```cmd
curl -fsSL http://서버주소:5050/install/install.cmd -o install.cmd && install.cmd && del install.cmd
```

---

## 7. 리버스 프록시 연결

> 상세 설정은 [SECURITY.md — 리버스 프록시 설정](SECURITY.md#리버스-프록시-설정) 참고.

리버스 프록시(Apache/nginx) 사용 시 `WCMS_SSL_CERT`/`WCMS_SSL_KEY` 환경변수는 불필요하며, `force_https`는 자동으로 비활성화됩니다. 프록시 측에서 HTTPS를 종료하고 HTTP로 Gunicorn에 전달하는 구조입니다.

**포트 요약:**

```
클라이언트 → 443(HTTPS) → Apache/nginx → 5050(HTTP) → Gunicorn
```

---

## 8. 운영 관리

### 서비스 제어

```bash
sudo systemctl start wcms      # 시작
sudo systemctl stop wcms       # 중지
sudo systemctl restart wcms    # 재시작
sudo systemctl reload wcms     # 설정 재로드 (HUP 신호)
```

### 로그 확인

```bash
# systemd journal
sudo journalctl -u wcms -f

# 파일 로그
sudo tail -f /var/log/wcms/server.log

# 최근 오류만
sudo journalctl -u wcms -p err --since "1 hour ago"
```

### DB 백업

```bash
# 백업 스크립트 (crontab 등록 권장)
#!/bin/bash
BACKUP_DIR=/var/backups/wcms
DB_PATH=/var/lib/wcms/db.sqlite3
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
# WAL 체크포인트 후 복사 (데이터 일관성 보장)
sqlite3 $DB_PATH "PRAGMA wal_checkpoint(FULL);"
cp $DB_PATH $BACKUP_DIR/db_$DATE.sqlite3

# 30일 이상 된 백업 삭제
find $BACKUP_DIR -name "db_*.sqlite3" -mtime +30 -delete
```

crontab 등록 (매일 새벽 3시):

```bash
sudo crontab -e
# 추가:
0 3 * * * /opt/wcms/scripts/backup.sh >> /var/log/wcms/backup.log 2>&1
```

### SSL 인증서 자동 갱신 (Let's Encrypt)

```bash
# /etc/cron.d/certbot 또는 systemd timer 사용
0 3 * * * certbot renew --quiet --post-hook "systemctl restart wcms"
```

---

## 9. 업데이트

```bash
# 1. 저장소 업데이트
cd /opt/wcms
sudo -u wcms git pull

# 2. 의존성 업데이트
sudo -u wcms python3 manage.py install

# 3. DB 마이그레이션 필요 시 (스키마 변경)
# schema.sql 변경 내역을 CHANGELOG.md에서 확인 후 수동 적용
# sudo -u wcms env $(cat /etc/wcms/env | xargs) python3 manage.py init-db --force  ← DB 초기화 (데이터 삭제)

# 4. 서비스 재시작
sudo systemctl restart wcms
sudo systemctl status wcms
```

> `init-db --force`는 기존 데이터를 **전부 삭제**합니다. 마이그레이션이 필요하면 수동으로 ALTER TABLE을 실행하거나 백업 후 복구하세요.

---

## 10. 문제 해결

### 서비스가 시작되지 않는 경우

```bash
# 상세 오류 확인
sudo journalctl -u wcms -n 50 --no-pager

# 환경변수 누락 확인 (WCMS_SECRET_KEY 필수)
sudo -u wcms env $(cat /etc/wcms/env | xargs) python3 -c "from server.config import get_config; get_config('production')"
```

### 포트가 이미 사용 중

```bash
sudo ss -tlnp | grep 5050
sudo kill -9 <PID>
```

### DB 잠김 오류 (`database is locked`)

SQLite WAL 모드에서 Gunicorn 워커가 1개 이상일 때 발생합니다. `/etc/wcms/env`에서 `-w 1` 설정이 유지되고 있는지 확인하세요. WCMS는 기본적으로 단일 워커를 사용합니다.

### 클라이언트 IP가 전부 127.0.0.1로 표시

리버스 프록시의 `X-Forwarded-For` 헤더 설정을 확인하세요 → [SECURITY.md 리버스 프록시 설정](SECURITY.md#리버스-프록시-설정).

### 관리자 로그인 후 즉시 로그아웃

`WCMS_SECRET_KEY`가 서버 재시작마다 바뀌고 있을 가능성이 높습니다. `/etc/wcms/env`에 고정값으로 설정되어 있는지 확인하세요.

---

## 배포 전 최종 체크리스트

- [ ] `WCMS_SECRET_KEY` 설정 (랜덤 생성, 고정값)
- [ ] `WCMS_ENV=production` 설정
- [ ] 기본 관리자 비밀번호 변경 (`admin`/`admin` → 강력한 비밀번호)
- [ ] DB 파일 권한 확인 (`ls -la /var/lib/wcms/db.sqlite3` → `wcms` 소유)
- [ ] 방화벽: 5050 포트 외부 차단 (리버스 프록시 사용 시), 443 허용
- [ ] HTTPS 인증서 적용 확인
- [ ] `systemctl status wcms` 정상 확인
- [ ] 로그인 및 클라이언트 등록 동작 확인
- [ ] 백업 스크립트 crontab 등록 확인