# WCMS

실습실 PC 원격 관리 시스템.

| 폴더 | 내용 |
|---|---|
| `server/` | Django + DRF + Channels |
| `frontend/` | SvelteKit SPA (계획 03) |
| `client/` | C++ Windows 클라이언트 (계획 05) |
| `protocol/` | 클라이언트-서버 프로토콜과 메시지 예시 |

설계 문서: `docs/superpowers/specs/2026-10-24-wcms-2026-1-design.md`

## 서버 실행 (개발)

```bash
cd server
uv sync
uv run python manage.py migrate
uv run python manage.py createadmin <아이디>
uv run uvicorn wcms.asgi:application --port 8000 --reload
```

`createadmin`이 출력한 `/enroll/...` 링크에서 비밀번호와 인증 앱을 등록한다 (화면은 계획 03).

가짜 클라이언트: `uv run python tools/fake_client.py --pin <PIN> --count 8`

## 화면 실행 (개발)

```bash
cd frontend
pnpm install
pnpm dev
```

`http://localhost:5173`. `/api`, `/ws`, `/client`는 `localhost:8000`의 서버로 넘긴다. 서버 API가 바뀌면 `pnpm gen:api`로 타입을 다시 만든다.

`localhost`가 아닌 주소(같은 망의 다른 PC 등)로 열려면 서버에 `WCMS_ALLOWED_HOSTS`와 `WCMS_CSRF_TRUSTED_ORIGINS`를 맞춰 준다. 개발 서버는 세션을 프로세스 메모리에 두므로 서버를 다시 켜면 다시 로그인해야 한다.

화면 테스트: `pnpm check && pnpm test`

## 테스트

```bash
cd server
uv run pytest
```

OpenAPI 스키마를 바꾼 뒤에는 `uv run python manage.py spectacular --file openapi.yaml --validate --fail-on-warn`으로 다시 만든다.
