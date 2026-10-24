# WCMS 2026.1 계획 09 (앞부분): 개발 포트 8888과 Docker compose 운영 실행 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 개발 서버 기본 포트를 8888로 바꾸고, `deploy/`의 Docker compose 하나로 운영 형태(nginx + Django/uvicorn + Redis)를 바로 띄울 수 있게 한다. 계획 09의 예약 작업과 실습실 PC용 내부 TLS는 이 문서 범위 밖이다.

**Architecture:** 이미지 두 개. `server`는 Python 3.13 + uv로 Django를 uvicorn 한 프로세스로 띄우고, 시작할 때 migrate 한다. `web`은 화면을 빌드해 nginx에 넣는다. nginx는 웹 브라우저용(443 https, Cloudflare Origin 인증서. 화면 + `/api` + `/ws`, `/client`는 404. 80은 https로 돌려보냄)과 실습실 PC용(8889, `/client`와 `/healthz`만, `X-WCMS-Via: internal`을 붙임) 블록을 둔다. 웹 블록은 Cloudflare 대역에서 온 연결에 한해 `CF-Connecting-IP`를 실제 IP로 쓴다. Redis는 AOF로 저장하고 축출하지 않는다. SQLite는 `/data` 볼륨.

**Tech Stack:** Docker, compose v2, nginx 1.28, python 3.13 slim, uv, node 22 alpine, pnpm, redis 7.4

**선행 조건:** 계획 02, 03 완료

**설계 문서:** `docs/superpowers/specs/2026-10-24-wcms-2026-1-design.md` 2장(경로와 nginx), 8장(배포)

**작업 브랜치:** `feat/frontend-base`에서 `feat/deploy-compose`

## Global Constraints

- 포트: 8888은 개발용(uvicorn 개발 서버, Vite 프록시, 가짜 클라이언트 기본값)과 server 컨테이너 내부에만 쓴다. 운영 웹은 443(https)과 80(https로 돌려보냄), 실습실 PC용은 8889(`WCMS_CLIENT_PORT`).
- 웹 블록 인증서는 Cloudflare Origin 인증서(`deploy/certs/origin.pem`, `origin.key`). 인증서와 키는 저장소에 넣지 않는다.
- 비밀값(`WCMS_SECRET_KEY`)은 저장소에 넣지 않는다. `deploy/.env`는 git에서 제외하고 `deploy/.env.example`만 커밋한다.
- 웹 브라우저용 블록은 들어온 `X-WCMS-Via`를 지우고 `/client/`를 404로 막는다. `X-Real-IP`는 두 블록 모두 nginx가 덮어쓴다.
- 이미지 태그와 도구 버전은 정확히 고정한다 (`latest` 금지).
- 커밋 메시지에 작성자 표기(Co-Authored-By 등)를 넣지 않는다. 저장소 문서에 커밋 번호나 커밋·push 상태를 쓰지 않는다.

---

## 파일 구조

```
.dockerignore                 빌드 맥락에서 node_modules, .venv, DB, build 산출물 제외
deploy/
  compose.yaml                redis, server, web
  server.Dockerfile           Django + uvicorn
  web.Dockerfile              화면 빌드 → nginx
  nginx.conf                  server 블록 두 개
  snippets/proxy.conf         공통 프록시 헤더
  snippets/security.conf      공통 보안 헤더
  snippets/cloudflare.conf    Cloudflare 대역과 CF-Connecting-IP
  certs/                      Origin 인증서와 키 (커밋하지 않음)
  .env.example                운영 환경 변수 예시
  smoke.sh                    띄운 뒤 경로 확인
server/wcms/settings.py       DEBUG=0일 때 필수 환경 변수 확인
server/tests/test_settings_prod.py
server/tools/fake_client.py   기본 --server 8888
frontend/vite.config.ts       프록시 대상 8888
README.md                     개발 포트 8888, 운영 실행
```

---

### Task 1: 개발 기본 포트 8888

**Files:**
- Modify: `frontend/vite.config.ts`, `server/tools/fake_client.py`, `README.md`

- [ ] **Step 1: 바꾸기**

`frontend/vite.config.ts`: `const backend = 'http://localhost:8888';`

`server/tools/fake_client.py`: 맨 위 사용 예와 `--server` 기본값을 `http://localhost:8888`로.

`README.md`: 서버 실행 명령을 `uv run uvicorn wcms.asgi:application --port 8888 --reload`로, 화면 실행 절의 `localhost:8000`을 `localhost:8888`로.

- [ ] **Step 2: 확인**

Run: `grep -rn "8000" README.md frontend/vite.config.ts server/tools/fake_client.py`
Expected: 결과 없음

Run: `cd frontend && pnpm check && pnpm test`
Expected: 통과

- [ ] **Step 3: Commit**

```bash
git add frontend/vite.config.ts server/tools/fake_client.py README.md
git commit -m "chore: default dev server port 8888"
```

---

### Task 2: 운영 설정 누락이면 시작하지 않기

**Files:**
- Modify: `server/wcms/settings.py`
- Test: `server/tests/test_settings_prod.py`

**Interfaces:**
- `WCMS_DEBUG=0`이면 `WCMS_SECRET_KEY`(이미 있음), `WCMS_REDIS_URL`, `WCMS_ALLOWED_HOSTS`, `WCMS_CSRF_TRUSTED_ORIGINS`가 환경 변수로 주어져야 한다. 하나라도 없으면 `ImproperlyConfigured`로 시작 실패. 메시지는 빠진 이름을 모두 적는다.

- [ ] **Step 1: 실패하는 테스트**

`server/tests/test_settings_prod.py`:

```python
import os
import subprocess
import sys
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parent.parent
PROD = {
    "WCMS_DEBUG": "0",
    "WCMS_SECRET_KEY": "x" * 50,
    "WCMS_REDIS_URL": "redis://localhost:6379/0",
    "WCMS_ALLOWED_HOSTS": "wcms.example",
    "WCMS_CSRF_TRUSTED_ORIGINS": "https://wcms.example",
}


def load_settings(env: dict[str, str]) -> subprocess.CompletedProcess:
    base = {key: value for key, value in os.environ.items() if not key.startswith("WCMS_")}
    return subprocess.run(
        [sys.executable, "-c", "import wcms.settings"],
        cwd=SERVER_DIR,
        env={**base, **env},
        capture_output=True,
        text=True,
    )


def test_complete_production_settings_load():
    assert load_settings(PROD).returncode == 0


def test_missing_production_settings_are_named():
    env = {key: value for key, value in PROD.items() if key not in {"WCMS_REDIS_URL", "WCMS_ALLOWED_HOSTS"}}
    result = load_settings(env)
    assert result.returncode != 0
    assert "ImproperlyConfigured" in result.stderr
    assert "WCMS_REDIS_URL" in result.stderr
    assert "WCMS_ALLOWED_HOSTS" in result.stderr


def test_debug_needs_nothing():
    assert load_settings({}).returncode == 0


def test_empty_secret_key_is_rejected_like_the_dev_key():
    for secret in ("", "dev-only-insecure-key"):
        result = load_settings({**PROD, "WCMS_SECRET_KEY": secret})
        assert result.returncode != 0
        assert "WCMS_SECRET_KEY" in result.stderr
```

Run: `cd server && uv run pytest tests/test_settings_prod.py -q`
Expected: `test_missing_production_settings_are_named` 실패

- [ ] **Step 2: 구현**

`server/wcms/settings.py`의 SECRET_KEY 확인 바로 아래:

```python
if not DEBUG and (not SECRET_KEY or SECRET_KEY == DEV_SECRET_KEY):
    raise ImproperlyConfigured("WCMS_DEBUG=0이면 WCMS_SECRET_KEY를 반드시 설정해야 합니다.")

PRODUCTION_REQUIRED = ["WCMS_REDIS_URL", "WCMS_ALLOWED_HOSTS", "WCMS_CSRF_TRUSTED_ORIGINS"]
if not DEBUG:
    missing = [name for name in PRODUCTION_REQUIRED if not os.environ.get(name)]
    if missing:
        raise ImproperlyConfigured(f"WCMS_DEBUG=0이면 다음 환경 변수가 필요합니다: {', '.join(missing)}")
```

- [ ] **Step 3: 테스트**

Run: `cd server && uv run pytest -q`
Expected: 모두 통과

- [ ] **Step 4: Commit**

```bash
git add server/wcms/settings.py server/tests/test_settings_prod.py
git commit -m "feat(server): refuse to start in production without redis, hosts and trusted origins"
```

---

### Task 3: deploy/ (compose, 이미지, nginx)

**Files:**
- Create: `.dockerignore`, `deploy/compose.yaml`, `deploy/server.Dockerfile`, `deploy/web.Dockerfile`, `deploy/nginx.conf`, `deploy/snippets/proxy.conf`, `deploy/snippets/security.conf`, `deploy/.env.example`, `deploy/smoke.sh`
- Modify: `.gitignore` (`deploy/.env`), `README.md`

- [ ] **Step 1: 버전 고정값 정하기**

- uv 0.13.3, pnpm 12.15.0 (개발 환경과 같은 버전)
- 이미지: `python:3.13.17-slim`, `node:22.23.4-alpine`, `nginx:1.28.3-alpine`(안정 계열), `redis:7.4.11-alpine`. 모두 `docker pull`로 확인한다.

- [ ] **Step 2: .dockerignore**

```
**/node_modules
**/.venv
**/__pycache__
**/.pytest_cache
**/*.sqlite3*
frontend/.svelte-kit
frontend/build
server/tools/.fake_clients.json
deploy/.env
.git
.superpowers
.claude
```

- [ ] **Step 3: server.Dockerfile**

```dockerfile
FROM python:3.13.17-slim
COPY --from=ghcr.io/astral-sh/uv:0.13.3 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app/server
COPY server/pyproject.toml server/uv.lock server/.python-version ./
RUN uv sync --frozen --no-dev
COPY VERSION /app/VERSION
COPY server/ ./
RUN useradd --system --home /app wcms && mkdir /data && chown wcms /data
USER wcms
ENV PATH="/app/server/.venv/bin:$PATH" WCMS_DB_PATH=/data/wcms.sqlite3
EXPOSE 8888
# --ws-max-size: 화면 프레임(계획 06)을 /client/ws로 받으려면 이 값을 올려야 한다
CMD ["sh", "-c", "python manage.py migrate --noinput && exec uvicorn wcms.asgi:application --host 0.0.0.0 --port 8888 --ws-ping-interval 20 --ws-ping-timeout 20 --ws-max-size 1048576"]
```

- [ ] **Step 4: web.Dockerfile**

```dockerfile
FROM node:22.23.4-alpine AS build
RUN npm install -g pnpm@12.15.0
WORKDIR /app/frontend
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

FROM nginx:1.28.3-alpine
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
COPY deploy/snippets/ /etc/nginx/snippets/
COPY --from=build /app/frontend/build /usr/share/nginx/html
```

- [ ] **Step 5: nginx**

`deploy/snippets/proxy.conf`:

```nginx
proxy_http_version 1.1;
proxy_set_header Host $http_host;
proxy_set_header X-Real-IP $remote_addr;
# 웹 블록은 nginx가 TLS를 끝내므로 https, 실습실 PC 블록은 http. 들어온 값은 쓰지 않는다
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection $connection_upgrade;
proxy_read_timeout 1h;
```

`deploy/snippets/security.conf`:

```nginx
add_header X-Content-Type-Options nosniff always;
add_header X-Frame-Options DENY always;
add_header Referrer-Policy same-origin always;
```

`deploy/nginx.conf`:

```nginx
map $http_upgrade $connection_upgrade {
    default upgrade;
    '' close;
}

# server 컨테이너가 다시 만들어져 IP가 바뀌어도 따라가도록 Docker 내장 DNS를 주기적으로 다시 조회한다
resolver 127.0.0.11 valid=10s ipv6=off;

upstream wcms_server {
    zone wcms_server 64k;
    server server:8888 resolve;
}

# 80은 https로 돌려보낸다
server {
    listen 80;
    server_tokens off;
    return 301 https://$host$request_uri;
}

# 웹 브라우저용: 화면, /api, /ws. 클라이언트 경로는 막는다
# 인증서는 Cloudflare Origin 인증서(deploy/certs/origin.pem, origin.key)
server {
    listen 443 ssl;
    http2 on;
    server_tokens off;
    ssl_certificate /etc/nginx/certs/origin.pem;
    ssl_certificate_key /etc/nginx/certs/origin.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    root /usr/share/nginx/html;
    include /etc/nginx/snippets/cloudflare.conf;

    location = /api {
        include /etc/nginx/snippets/proxy.conf;
        proxy_set_header X-WCMS-Via "";
        proxy_pass http://wcms_server;
    }

    location /api/ {
        include /etc/nginx/snippets/proxy.conf;
        proxy_set_header X-WCMS-Via "";
        proxy_pass http://wcms_server;
    }

    location /ws/ {
        include /etc/nginx/snippets/proxy.conf;
        proxy_set_header X-WCMS-Via "";
        proxy_pass http://wcms_server;
    }

    location /client/ {
        return 404;
    }

    location /_app/immutable/ {
        include /etc/nginx/snippets/security.conf;
        add_header Cache-Control "public, max-age=31536000, immutable" always;
        try_files $uri =404;
    }

    location / {
        include /etc/nginx/snippets/security.conf;
        add_header Cache-Control "no-cache" always;
        try_files $uri /index.html;
    }
}

# 실습실 PC용: /client 와 /healthz 만
server {
    listen 8889;
    server_tokens off;
    # 파일 업로드(계획 08)를 붙일 때는 이 블록에 client_max_body_size를 올려야 한다(기본 1m)

    location /client/ {
        include /etc/nginx/snippets/proxy.conf;
        proxy_set_header X-WCMS-Via internal;
        proxy_pass http://wcms_server;
    }

    location = /healthz {
        include /etc/nginx/snippets/proxy.conf;
        proxy_pass http://wcms_server;
    }

    location / {
        return 404;
    }
}
```

`deploy/snippets/cloudflare.conf`:

```nginx
# Cloudflare가 공개하는 주소 범위. 출처:
#   https://www.cloudflare.com/ips-v4
#   https://www.cloudflare.com/ips-v6
# Cloudflare가 목록을 바꾸면 이 파일을 다시 받아 갱신해야 한다.
# 여기 적힌 주소에서 온 연결에 한해 CF-Connecting-IP를 클라이언트 주소($remote_addr)로 삼는다.
# 그 밖의 연결에서는 이 헤더를 무시하고 TCP 상대 주소를 그대로 쓴다.
set_real_ip_from 173.245.48.0/20;
set_real_ip_from 103.21.244.0/22;
set_real_ip_from 103.22.200.0/22;
set_real_ip_from 103.31.4.0/22;
set_real_ip_from 141.101.64.0/18;
set_real_ip_from 108.162.192.0/18;
set_real_ip_from 190.93.240.0/20;
set_real_ip_from 188.114.96.0/20;
set_real_ip_from 197.234.240.0/22;
set_real_ip_from 198.41.128.0/17;
set_real_ip_from 162.158.0.0/15;
set_real_ip_from 104.16.0.0/13;
set_real_ip_from 104.24.0.0/14;
set_real_ip_from 172.64.0.0/13;
set_real_ip_from 131.0.72.0/22;
set_real_ip_from 2400:cb00::/32;
set_real_ip_from 2606:4700::/32;
set_real_ip_from 2803:f800::/32;
set_real_ip_from 2405:b500::/32;
set_real_ip_from 2405:8100::/32;
set_real_ip_from 2a06:98c0::/29;
set_real_ip_from 2c0f:f248::/32;
real_ip_header CF-Connecting-IP;
```

- [ ] **Step 6: compose와 환경 변수**

`deploy/compose.yaml`:

```yaml
name: wcms

x-logging: &logging
  driver: json-file
  options:
    max-size: 10m
    max-file: "5"

services:
  redis:
    image: redis:7.4.11-alpine
    # maxmemory는 일부러 두지 않는다. 나중에 메모리 제한을 걸어도 noeviction이라 키가 밀려나지 않는다
    command: ["redis-server", "--appendonly", "yes", "--maxmemory-policy", "noeviction"]
    volumes:
      - redis:/data
    restart: unless-stopped
    logging: *logging

  server:
    build:
      context: ..
      dockerfile: deploy/server.Dockerfile
    env_file: .env
    environment:
      WCMS_DEBUG: "0"
      WCMS_REDIS_URL: redis://redis:6379/0
      WCMS_REQUIRE_INTERNAL: "1"
      WCMS_TRUST_X_REAL_IP: "1"
      WCMS_BEHIND_TLS_PROXY: "1"
    volumes:
      - data:/data
    depends_on:
      - redis
    healthcheck:
      # ALLOWED_HOSTS에 127.0.0.1이 없어도 되도록 HTTP가 아니라 TCP 연결만 본다
      test: ["CMD", "python", "-c", "import socket; socket.create_connection(('127.0.0.1', 8888), 2).close()"]
      interval: 10s
      timeout: 3s
      retries: 6
    restart: unless-stopped
    logging: *logging

  web:
    build:
      context: ..
      dockerfile: deploy/web.Dockerfile
    ports:
      - "${WCMS_HTTPS_PORT:-443}:443"
      - "${WCMS_HTTP_PORT:-80}:80"
      - "${WCMS_CLIENT_PORT:-8889}:8889"
    volumes:
      - ./certs:/etc/nginx/certs:ro
    depends_on:
      server:
        condition: service_healthy
    restart: unless-stopped
    logging: *logging

volumes:
  data:
  redis:
```

`deploy/.env.example`:

```bash
# cp .env.example .env 후 값을 채운다. .env는 커밋하지 않는다
# 비밀 키: python -c "import secrets; print(secrets.token_urlsafe(50))"
WCMS_SECRET_KEY=
# 브라우저가 쓰는 도메인과 실습실 PC가 붙는 서버 내부 주소를 모두 적는다
WCMS_ALLOWED_HOSTS=localhost,127.0.0.1
# 브라우저 주소의 origin. 운영은 https://<도메인>
WCMS_CSRF_TRUSTED_ORIGINS=https://localhost
# 호스트에 공개하는 포트 (기본값)
# WCMS_HTTPS_PORT=443
# WCMS_HTTP_PORT=80
WCMS_CLIENT_PORT=8889
```

`.gitignore`에 `deploy/.env` 추가.

- [ ] **Step 7: smoke.sh**

`deploy/smoke.sh` (실행 권한):

```bash
#!/bin/sh
# 띄운 compose의 경로 규칙을 확인한다. 사용: deploy/smoke.sh [웹 https 주소] [클라이언트 주소] [웹 http 주소]
# 로컬 확인용 자체 서명 인증서도 받도록 curl -k 를 쓴다
set -u
WEB=${1:-https://localhost}
CLIENT=${2:-http://localhost:8889}
HTTP=${3:-http://localhost}
fail=0

check() {
    name=$1 expected=$2 actual=$3
    if [ "$expected" = "$actual" ]; then
        echo "ok   $name"
    else
        echo "FAIL $name: expected $expected, got $actual"
        fail=1
    fi
}

status() { curl -sk -o /dev/null -w '%{http_code}' "$@"; }
ctype() { curl -sk -o /dev/null -w '%{content_type}' "$@"; }

check "화면" 200 "$(status "$WEB/")"
check "화면 경로 fallback" 200 "$(status "$WEB/rooms/1")"
check "없는 /api 경로는 404" 404 "$(status "$WEB/api/nope")"
check "없는 /api 경로는 JSON" application/json "$(ctype "$WEB/api/nope" | cut -d';' -f1)"
check "/api 그 자체도 JSON 404" 404 "$(status "$WEB/api")"
check "로그인 상태" 200 "$(status "$WEB/api/auth/me")"
check "웹 블록의 /client 는 404" 404 "$(status -X POST "$WEB/client/register")"
check "X-WCMS-Via 위조도 404" 404 "$(status -X POST -H 'X-WCMS-Via: internal' "$WEB/client/register")"
check "/ws/live 업그레이드" 101 "$(curl -sk -o /dev/null -w '%{http_code}' -m 3 --http1.1 \
    -H 'Connection: Upgrade' -H 'Upgrade: websocket' -H 'Sec-WebSocket-Version: 13' \
    -H 'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==' -H "Origin: $WEB" "$WEB/ws/live")"
check "http는 https로 301" 301 "$(status "$HTTP/")"
check "클라이언트 블록의 등록은 Django까지 간다" 400 "$(status -X POST -H 'Content-Type: application/json' -d '{}' "$CLIENT/client/register")"
check "클라이언트 블록의 /api 는 404" 404 "$(status "$CLIENT/api/auth/me")"
check "클라이언트 블록 healthz" 200 "$(status "$CLIENT/healthz")"

exit $fail
```

- [ ] **Step 8: README 운영 실행**

`README.md`의 테스트 절 앞에:

````markdown

## 운영 실행 (Docker)

```bash
cd deploy
cp .env.example .env   # WCMS_SECRET_KEY 등을 채운다
# Cloudflare Origin 인증서와 키를 certs/origin.pem, certs/origin.key 로 둔다
docker compose up -d --build
docker compose exec server python manage.py createadmin <아이디>
./smoke.sh
```

웹 브라우저는 443(https, http 80은 https로 돌려보냄), 실습실 PC 클라이언트는 `WCMS_CLIENT_PORT`(기본 8889)로 붙는다. Cloudflare SSL 모드는 Full (strict). `createadmin`이 출력한 `/enroll/...`를 웹 주소 뒤에 붙여 연다. DB는 `data` 볼륨, Redis는 `redis` 볼륨에 남는다.

로컬에서 확인할 때는 자체 서명 인증서로 띄우고 `https://localhost`로 연다.

```bash
mkdir -p certs && openssl req -x509 -newkey rsa:2048 -nodes -days 30 -subj /CN=localhost \
  -addext subjectAltName=DNS:localhost -keyout certs/origin.key -out certs/origin.pem
```

`smoke.sh`의 기본 주소는 `localhost`이므로 `WCMS_ALLOWED_HOSTS`에 `localhost`를 남겨 두거나 `./smoke.sh https://<도메인> http://<내부 주소>:8889 http://<도메인>`으로 실행한다.

Linux 호스트에 배포한다. Docker Desktop의 포트 프록시는 실제 클라이언트 주소를 가려서, 실습실 PC 등록 횟수 제한이 제대로 동작하지 않는다.

````

- [ ] **Step 9: 빌드와 확인**

Run: `cd deploy && cp .env.example .env && <WCMS_SECRET_KEY 채우기> && <README의 openssl 명령으로 자체 서명 인증서> && docker compose up -d --build && ./smoke.sh`
Expected: smoke 모두 ok. 확인 뒤 `docker compose down -v`, `deploy/.env`와 `deploy/certs/`를 지운다.

- [ ] **Step 10: Commit**

```bash
git add .dockerignore .gitignore deploy README.md
git commit -m "feat(deploy): docker compose with nginx, server and redis"
```

---

### Task 4: 운영 형태로 실제 확인 (컨트롤러가 내장 브라우저로)

- [ ] compose로 띄우고 `createadmin` → `https://localhost/enroll/...` 등록 → 로그인 → 실습실 추가 → PIN → `uv run python tools/fake_client.py --server http://localhost:8889 --pin <PIN> --count 3` → 자리 배치 → 실습실 화면에서 실시간 갱신 → 로그아웃 뒤 비로그인 화면
- [ ] `docker compose restart server` 뒤 화면이 다시 연결되고 PC가 다시 온라인으로 바뀌는지
- [ ] 정리: `docker compose down -v`, `deploy/.env`와 `deploy/certs/` 삭제

---

## 실행 결과 및 다음으로 넘기는 항목

이 문서의 범위는 완료됐다 (서버 테스트 263개 통과). compose로 띄워 smoke 13개를 확인했고, 내장 브라우저로 등록·로그인·PIN·가짜 클라이언트(8889)·자리 배치·실시간 갱신·서버 재시작 뒤 복구·비로그인 응답을, 자체 서명 인증서로 https 로그인 CSRF와 Secure 쿠키를 확인했다.

### 계획 09 나머지에서 처리

- 실습실 PC용 내부 TLS (자체 루트 CA, 계획 05와 함께)
- 원 서버의 443은 Cloudflare에서만 닿게 방화벽을 둔다 (직접 접속하면 한국만 허용 WAF를 우회)
- CI에서 compose를 띄워 `deploy/smoke.sh` 실행 (`.env`는 임의 비밀 키, 인증서는 자체 서명, `localhost`를 ALLOWED_HOSTS에 남김)
- `cloudflare.conf` 대역 목록 갱신 절차, Content-Security-Policy
- 예약 작업, 로그·백업 압축 보관

### 계획 06·08에서 처리

- 화면 프레임: `--ws-max-size`(1MiB)를 `/client/ws`에 맞게 올린다
- 설치 파일 업로드: 내부 블록 `client_max_body_size`(기본 1m), X-Accel-Redirect 내려받기 location
