# WCMS

실습실 PC 원격 관리 시스템.

- 서버: Django (`server/`)
- 클라이언트: C++ Windows 서비스 (`client/`, 작업 예정)

설계 문서: `docs/superpowers/specs/2026-10-24-wcms-2026-1-design.md`

## 서버 실행 (개발)

```bash
cd server
uv sync
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

가짜 클라이언트: `uv run python tools/fake_client.py --pin <PIN> --count 8`

## 테스트

```bash
cd server
uv run pytest
```
