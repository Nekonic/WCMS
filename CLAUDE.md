# WCMS

설계: docs/superpowers/specs/2026-10-24-wcms-2026-1-design.md
계획: docs/superpowers/plans/
프로토콜: docs/protocol.md

- server/: Django + Channels. 명령은 server/ 에서 `uv run ...`. 패키지 추가는 `uv add` (pip 직접 사용 금지)
- 테스트: `cd server && uv run pytest`
- 버전: 루트 VERSION 파일 (형식 2026.1)
- 학생이 조작할 수 있는 값(창 제목, 프로세스 이름, 사용자 이름, 호스트 이름, 명령 출력)은 템플릿에서 `|safe` 금지, JS에서는 textContent만 사용
