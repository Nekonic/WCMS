# WCMS 개발자 문서 목록

> 개발자를 위한 상세 문서 모음

---

## 📌 필수 문서 (먼저 읽기)

| 문서 | 설명 |
|------|------|
| [GETTING_STARTED.md](GETTING_STARTED.md) | 프로젝트 시작 및 실행 가이드 |
| [API.md](API.md) | REST API 전체 명세 |
| [ARCHITECTURE.md](ARCHITECTURE.md) | 시스템 아키텍처 설계 |

---

## 📚 전체 문서 목록

### 시작하기
| 문서 | 설명 | 용도 |
|------|------|------|
| [GETTING_STARTED.md](GETTING_STARTED.md) | 통합 시작 가이드 | 설치, 실행, 테스트 방법 |
| [API.md](API.md) | REST API 전체 명세 | API 사용법, 엔드포인트, 예제 |

### 시스템 설계
| 문서 | 설명 |
|------|------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | 시스템 아키텍처 설계 |
| [PROJECT_STATUS.md](PROJECT_STATUS.md) | 프로젝트 개발 상태 |

### 개발 가이드
| 문서 | 설명 |
|------|------|
| [QUICK_REFERENCE.md](QUICK_REFERENCE.md) | 새 모듈 빠른 참조 |
| [GIT_COMMIT_GUIDE.md](GIT_COMMIT_GUIDE.md) | Git 커밋 컨벤션 |

### 자동화 및 업데이트
| 문서 | 설명 |
|------|------|
| [CLIENT_AUTO_UPDATE.md](CLIENT_AUTO_UPDATE.md) | 클라이언트 자동 업데이트 기능 |

### 리팩토링 추적
| 문서 | 설명 |
|------|------|
| [REFACTORING.md](REFACTORING.md) | 리팩토링 전체 계획 (5 Phase) |
| [REFACTORING_STATUS.md](REFACTORING_STATUS.md) | 리팩토링 진행 상황 |

---

## 🚀 빠른 시작 (통합 스크립트)

프로젝트 루트의 `manage.py`를 사용하여 쉽게 시작할 수 있습니다.

```bash
# 서버 실행
python manage.py run

# 테스트 실행
python manage.py test
```

**접속:** `http://localhost:5050` (ID: admin, PW: admin123)

---

## 📖 문서 읽는 순서

### 서버 시작하기 (첫 시작)
1. [GETTING_STARTED.md](GETTING_STARTED.md) - 통합 시작 가이드
2. [API.md](API.md) - API 테스트

### API 개발자
1. [API.md](API.md) - REST API 전체 명세
2. [ARCHITECTURE.md](ARCHITECTURE.md) - 시스템 설계

### 신규 개발자
1. [ARCHITECTURE.md](ARCHITECTURE.md) - 시스템 구조
2. [API.md](API.md) - API 이해
3. [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - 코드 작성
4. [PROJECT_STATUS.md](PROJECT_STATUS.md) - 현재 상태

### 리팩토링 참여
1. [REFACTORING.md](REFACTORING.md) - 계획 (5 Phase)
2. [REFACTORING_STATUS.md](REFACTORING_STATUS.md) - 진행 상황
3. [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - 모듈 사용법

---

## 개발 환경 설정

### 전체 설치
```bash
cd /Users/nekonic/PycharmProjects/WCMS
python manage.py run
```

**상세:** [GETTING_STARTED.md](GETTING_STARTED.md)

---

## 테스트

### 단위 테스트
```bash
python manage.py test
```

### API 테스트
```bash
# 서버가 실행 중일 때 (새 터미널)
curl http://localhost:5050/api/client/version
```

**상세:** [GETTING_STARTED.md](GETTING_STARTED.md)

---

## 유용한 링크

- 🚀 [시작 가이드](GETTING_STARTED.md) - 설치 및 실행
- 📚 [API 문서](API.md) - 엔드포인트 명세
- 🏗️ [아키텍처](ARCHITECTURE.md) - 시스템 설계

---

## 기여하기

1. [REFACTORING_STATUS.md](REFACTORING_STATUS.md)에서 미완료 작업 확인
2. 브랜치 생성: `git checkout -b feature/작업명`
3. 코드 작성 (타입 힌팅 필수)
4. [GIT_COMMIT_GUIDE.md](GIT_COMMIT_GUIDE.md) 참고하여 커밋
5. Pull Request 생성

---

**문의**: 이슈 생성 또는 프로젝트 관리자에게 연락
