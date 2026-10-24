# WCMS

설계: docs/superpowers/specs/2026-10-24-wcms-2026-1-design.md
계획: docs/superpowers/plans/
클라이언트 프로토콜: protocol/README.md (예시: protocol/examples/)

- server/: Django + DRF + Channels. 명령은 server/ 에서 `uv run ...`. 패키지 추가는 `uv add` (pip 직접 사용 금지)
- frontend/: SvelteKit SPA (계획 03)
- 테스트: `cd server && uv run pytest`
- 버전: 루트 VERSION 파일 (형식 2026.1)
- 학생이 조작할 수 있는 값(창 제목, 프로세스 이름, 사용자 이름, 호스트 이름, 명령 출력)은 신뢰하지 않는다. 비로그인 응답에는 좌석 라벨과 켜짐/꺼짐만
