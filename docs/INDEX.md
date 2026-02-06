# WCMS 문서 목록

---

## 📌 필수 문서

| 문서 | 설명 |
|------|------|
| [AI_CONTEXT.md](../AI_CONTEXT.md) | AI/신규 개발자 빠른 온보딩 |
| [GETTING_STARTED.md](GETTING_STARTED.md) | 설치 및 실행 가이드 |
| [API.md](API.md) | REST API 명세 |
| [ARCHITECTURE.md](ARCHITECTURE.md) | 시스템 아키텍처 |
| [CHANGELOG.md](CHANGELOG.md) | 변경 이력 |

---

## 📚 기능 가이드

| 문서 | 설명 |
|------|------|
| [CLIENT_AUTO_UPDATE.md](CLIENT_AUTO_UPDATE.md) | 클라이언트 자동 업데이트 및 GitHub Actions |
| [DOCKER_CLIENT_SETUP.md](DOCKER_CLIENT_SETUP.md) | Docker 환경에서 클라이언트 테스트 |
| [QUICK_REFERENCE.md](QUICK_REFERENCE.md) | 개발자 빠른 참조 |
| [GIT_COMMIT_GUIDE.md](GIT_COMMIT_GUIDE.md) | Git 커밋 컨벤션 |

---

## 🚀 빠른 시작

```bash
# 서버 시작
python manage.py run

# Docker 테스트
python manage.py docker-test
```

**서버 접속**: `http://localhost:5050` (admin / admin)

---

## 📖 읽는 순서

### 신규 개발자
1. **[AI_CONTEXT.md](../AI_CONTEXT.md)** - 5분 안에 프로젝트 파악
2. **[GETTING_STARTED.md](GETTING_STARTED.md)** - 설치 및 실행
3. **[API.md](API.md)** - API 이해

### 기여자
1. **[ARCHITECTURE.md](ARCHITECTURE.md)** - 시스템 구조 이해
2. **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - 개발 패턴
3. **[CHANGELOG.md](CHANGELOG.md)** - 최근 변경사항

