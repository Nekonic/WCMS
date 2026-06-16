# WCMS 백엔드 (Django + DRF)

v0.10.0 재작성의 관리(admin) 백엔드. 아키텍처: `../docs/REWRITE_DESIGN.md`.

## 개발 실행

```bash
uv sync                              # 의존성

docker compose up -d                 # (선택) 개발 PostgreSQL
cp .env.example .env                 # DATABASE_URL 확인 (미지정 시 dev.sqlite3)

uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

admin: http://localhost:8000/admin/

## 앱 구조

- `fleet` — Client(PC 영속 신원/관리), ClientSpecs, ClientDynamicInfo, Room, Seat, NetworkEvent, ClientVersion
- `enrollment` — EnrollmentToken(PIN)
- `commands` — Command(delivery_mode/TTL/ack 생명주기, issuer 감사)
- `logs` — ClientLog(구조화 로그 수집)

관리자 인증은 Django 기본 auth(세션 + CSRF). 클라이언트 신원은 공개키 인증서(PKC).
DB 스키마/마이그레이션은 이 Django 프로젝트가 단독 소유한다.
