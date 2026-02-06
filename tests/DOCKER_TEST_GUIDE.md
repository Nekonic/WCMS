# Docker 통합 테스트 가이드

> dockurr/windows 컨테이너를 활용한 WCMS 클라이언트 실제 환경 테스트

---

## 빠른 시작

```bash
# 최초 실행 (이미지 다운로드 + 부팅: 20-30분)
python manage.py docker-test

# 이후 실행 (컨테이너 재사용: 1-2분)
python manage.py docker-test --skip-boot
```

---

## 시스템 요구사항

### 필수
- **Docker Desktop** (Windows/Mac) 또는 **Docker + Docker Compose** (Linux)
- **시스템 메모리**: 최소 16GB (권장 32GB 이상)
- **디스크 공간**: 최소 30GB 여유 공간
- **KVM 지원** (Linux만): `/dev/kvm` 활성화

### 권장
- **CPU**: 4코어 이상
- **네트워크**: 안정적인 인터넷 연결 (최초 이미지 다운로드용)

---

## 주요 기능

### 1. Docker Compose 기반 구성
- **서버 컨테이너** (Flask): 자동 빌드 및 실행
- **자동 DB 초기화**: 최초 실행 시 스키마 적용 및 관리자 계정(admin/admin) 생성
- **Windows 11 컨테이너** (dockurr/windows): 실제 Windows 환경
- **빠른 ISO 다운로드**: massgrave.dev 미러 사용 (5-6GB, 빠른 속도)
- **VNC 접속**: 웹 브라우저 또는 VNC 클라이언트로 GUI 확인

### 2. 자동화
- 시스템 리소스 자동 감지 (RAM, CPU)
- 이미지 및 컨테이너 재사용 (설치 시간 단축)
- Windows 부팅 대기 (로그 기반 감지)
- 서버 헬스체크

### 3. VNC 접속 지원
- **웹 VNC**: http://localhost:8006 (브라우저에서 바로 접속)
- **VNC 포트**: localhost:5900
- **RDP 포트**: localhost:3389
- **로그인 정보**:
  - 사용자: `Administrator`
  - 비밀번호: `Wcms2026!`

---

## 사용 방법

### 기본 실행

```bash
# 전체 프로세스 (서버 시작 + Windows 부팅 + 테스트)
python manage.py docker-test
```

### 옵션

```bash
# 서버 이미지 강제 재빌드
python manage.py docker-test --rebuild

# 빌드 캐시 사용 안 함 (완전 새로 빌드)
python manage.py docker-test --rebuild --no-cache

# Windows 부팅 대기 스킵 (이미 부팅된 경우)
python manage.py docker-test --skip-boot

# 테스트 후 컨테이너 정리
python manage.py docker-test --cleanup
```

### 수동 제어

```bash
# 서비스 시작
docker compose --env-file .env.docker up -d

# 로그 확인
docker compose logs -f

# 특정 컨테이너 로그
docker compose logs -f wcms-server
docker compose logs -f wcms-test-win

# 서비스 중지
docker compose down

# 완전 삭제 (볼륨 포함)
docker compose down -v
```

---

## 접속 정보

테스트가 시작되면 다음 URL로 접속할 수 있습니다:

| 서비스 | URL/포트 | 비고 |
|--------|----------|------|
| WCMS 서버 | http://localhost:5050 | Flask 웹 UI |
| 웹 VNC | http://localhost:8006 | 브라우저에서 Windows GUI |
| VNC | localhost:5900 | VNC 클라이언트 필요 |
| RDP | localhost:3389 | RDP 클라이언트 필요 |

---

## 설정 커스터마이징

### 리소스 할당 변경

`.env.docker` 파일 수정:

```env
# Windows 컨테이너 리소스
DOCKER_WIN_RAM=12G      # 메모리 (기본: 8G)
DOCKER_WIN_CPUS=6       # CPU 코어 (기본: 4)

# VNC/RDP 비밀번호
VNC_PASSWORD=wcms2026
WIN_PASSWORD=Wcms2026!
```

### 서버 설정 변경

`docker-compose.yml`의 `wcms-server` 섹션:

```yaml
environment:
  - WCMS_ENV=development
  - WCMS_SECRET_KEY=your-secret-key
  - WCMS_LOG_LEVEL=DEBUG  # INFO, WARNING, ERROR
```

---

## 문제 해결

### 1. 이미지 다운로드 실패

```bash
# 네트워크 확인 후 재시도
docker pull dockurr/windows:latest
```

### 2. 포트 충돌

```bash
# 포트 사용 중인 프로세스 확인
netstat -ano | findstr :8006
netstat -ano | findstr :5050

# 해당 프로세스 종료 또는 docker-compose.yml에서 포트 변경
```

### 3. KVM 권한 오류 (Linux)

```bash
# KVM 권한 추가
sudo usermod -aG kvm $USER
# 재로그인 필요
```

### 4. Windows 부팅 실패

```bash
# 로그 확인
docker logs wcms-test-win

# 컨테이너 재시작
docker restart wcms-test-win

# 웹 VNC로 수동 확인
# http://localhost:8006
```

### 5. 메모리 부족

시스템 메모리가 부족한 경우 `.env.docker` 수정:

```env
DOCKER_WIN_RAM=6G       # 8G → 6G로 감소
DOCKER_WIN_CPUS=2       # 4 → 2로 감소
```

---

## 아키텍처

```
호스트 (Windows/Linux/Mac)
├── Docker Compose
│   ├── wcms-server (Flask)
│   │   ├── 포트: 5050
│   │   ├── DB 자동 초기화 (schema.sql)
│   │   └── 기본 계정: admin/admin
│   │
│   └── wcms-test-win (Windows 11)
│       ├── 포트: 8006 (웹 VNC)
│       ├── 포트: 5900 (VNC)
│       ├── 포트: 3389 (RDP)
│       ├── ISO: massgrave.dev (빠른 다운로드)
│       └── host.docker.internal → 호스트 서버 접근
│
└── 네트워크: wcms-network (172.28.0.0/16)
```

---

## 개발 워크플로우

### 1. 초기 설정 (최초 1회)

```bash
# 1. 의존성 설치
python manage.py install

# 2. Docker 테스트 (이미지 다운로드 + 부팅)
python manage.py docker-test
# → 약 20-30분 소요
```

### 2. 반복 테스트

```bash
# 서버 코드 수정 후 재테스트
python manage.py docker-test --rebuild --skip-boot
# → 약 1-2분 소요
```

### 3. 클라이언트 설치 (향후 구현)

```bash
# 컨테이너 내부에서 클라이언트 설치
docker exec wcms-test-win powershell -Command "Invoke-WebRequest -Uri 'http://host.docker.internal:5050/download/wcms-client.exe' -OutFile 'C:\wcms-client.exe'"
```

---

## 다음 단계 (TODO)

현재 Phase 1 (네트워크 설정 및 서버 연동) 진행 중입니다.

- [ ] Phase 1: 컨테이너 ↔ 호스트 서버 통신 검증
- [ ] Phase 2: 클라이언트 자동 설치
- [ ] Phase 3: Windows 서비스 테스트
- [ ] Phase 4: 명령 실행 테스트
- [ ] Phase 5: E2E 시나리오

자세한 계획은 `plan.md` 참조.

---

## 참고 문서

- **plan.md**: 전체 구현 계획 및 진행 상황
- **AI_CONTEXT.md**: 프로젝트 전체 구조
- **docs/ARCHITECTURE.md**: 시스템 아키텍처
- **docs/API.md**: REST API 명세
- **dockurr/windows**: https://hub.docker.com/r/dockurr/windows

---

**작성일**: 2026-02-07  
**업데이트**: Phase 1 진행 중
