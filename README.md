# WCMS

실습실 PC 원격 관리 시스템.

| 폴더 | 내용 |
|---|---|
| `server/` | Django + DRF + Channels |
| `frontend/` | SvelteKit SPA |
| `deploy/` | Docker compose (nginx, 서버, Redis) |
| `client/` | C++ Windows 클라이언트 (계획 05) |
| `protocol/` | 클라이언트-서버 프로토콜과 메시지 예시 |

설계 문서: `docs/superpowers/specs/2026-10-24-wcms-2026-1-design.md`

## 서버 실행 (개발)

```bash
cd server
uv sync
uv run python manage.py migrate
uv run python manage.py createadmin <아이디>
uv run uvicorn wcms.asgi:application --port 8888 --reload
```

`createadmin`이 출력한 `/enroll/...` 링크를 화면 개발 서버 주소 뒤에 붙여 열고 비밀번호와 인증 앱을 등록한다.

가짜 클라이언트: `uv run python tools/fake_client.py --pin <PIN> --count 8`

## 화면 실행 (개발)

```bash
cd frontend
pnpm install
pnpm dev
```

`http://localhost:5173`. `/api`, `/ws`, `/client`는 `localhost:8888`의 서버로 넘긴다. 서버 API가 바뀌면 `pnpm gen:api`로 타입을 다시 만든다.

`localhost`가 아닌 주소(같은 망의 다른 PC 등)로 열려면 서버에 `WCMS_ALLOWED_HOSTS`와 `WCMS_CSRF_TRUSTED_ORIGINS`를 맞춰 준다. 개발 서버는 세션을 프로세스 메모리에 두므로 서버를 다시 켜면 다시 로그인해야 한다.

화면 테스트: `pnpm check && pnpm test`

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

## 테스트

```bash
cd server
uv run pytest
```

OpenAPI 스키마를 바꾼 뒤에는 `uv run python manage.py spectacular --file openapi.yaml --validate --fail-on-warn`으로 다시 만든다.
