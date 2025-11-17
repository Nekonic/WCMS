# 프로젝트 진행 상황

최종 업데이트: 2024.11.17

## 📊 전체 진행률: 78%

### Phase 1: 서버 개발 (100%)
- [x] Flask 프로젝트 구조 및 DB 스키마
- [x] 웹 UI (대시보드, 좌석 배치, 모달)
- [x] 관리자 로그인/로그아웃 (세션 기반)
- [x] PC 조회 및 원격 제어 API
- [x] 프로세스 기록 조회 API 및 페이지
- [x] 좌석 배치 저장 시 seat_number 자동 업데이트
- [x] 실습실별 PC 그리드 뷰 및 상태 표시
- [ ] 파일 전송/프로그램 원격 설치 (향후)

### Phase 2: 클라이언트 기초 (100%)
- [x] 프로젝트 구조 및 API 통신
- [x] 정적/동적 정보 수집 분리
- [x] 메인 루프 (최초 등록, 주기적 Heartbeat)
- [x] 실행 중인 프로세스 수집 및 필터링
- [x] 활성 네트워크 인터페이스 IP/MAC 주소 자동 조회
- [x] Machine ID 생성 (MAC 주소 기반)

### Phase 3: 클라이언트 제어 (60%)
- [x] 명령 폴링 및 실행 (Long-polling)
- [x] PC 종료/재시작
- [x] CMD 명령어 실행
- [x] 프로그램 설치 (winget)
- [x] 파일 다운로드
- [ ] Windows 계정 관리 (생성/삭제/비밀번호 변경)
- [ ] 명령 실행 결과 보고 API 구현
- [ ] 파일 업로드 (서버 → 클라이언트)

### Phase 4: 문서화 및 품질 개선 (85%)
- [x] README.md 작성
- [x] DEVELOP.md 개발 가이드 작성
- [x] STATUS.md 진행 상황 관리
- [x] API 명세서 (API.md) 작성 및 개선
  - [x] 목차 및 버전 정보 추가
  - [x] 인증 방식 명시 (세션 기반)
  - [x] 파라미터 표 형식 정리
  - [x] Quick Start 가이드 추가
  - [x] 에러 코드 정리
  - [x] Python/cURL 예제 추가
  - [x] Windows 계정 관리 API 명세 추가
- [ ] 주석 및 코드 품질 개선

### Phase 5: Windows 서비스 & 배포 (15%)
- [x] GitHub Actions 자동 빌드 워크플로우
- [x] PyInstaller 설정 (`build.spec`)
- [ ] Windows 서비스 등록 스크립트
- [ ] 클라이언트 자동 업데이트 기능
- [ ] 실제 환경 배포 및 테스트

---

## 🎯 다음 마일스톤

| 마일스톤 | 목표 일자 | 상태 | 우선순위 |
|---------|----------|------|----------|
| API 명세서 완성 | 2024.11.17 | ✅ 완료 | High |
| Windows 계정 관리 구현 | 2024.11.18 | ⏳ 진행 중 | High |
| 명령 결과 보고 시스템 | 2024.11.19 | 📋 예정 | Medium |
| Windows 서비스화 | 2024.11.22 | 📋 예정 | High |
| 배포 & 최종 테스트 | 2024.11.25 | 📋 예정 | High |

---

## 🐛 해결된 이슈

| 날짜 | 제목 | 해결 방법 |
|------|------|-----------|
| 2024.11.10 | DB 스키마 불일치 오류 | `pc_info` 테이블에 `mac_address` 컬럼 추가 |
| 2024.11.11 | 불필요한 데이터 중복 전송 | 등록(정적)/하트비트(동적) 정보 전송 분리 |
| 2024.11.11 | WMI 스레드 오류 | `CoInitialize` 추가 (경고는 여전히 발생하나 기능 정상) |
| 2024.11.12 | disk_info 직렬화 오류 | JSON 변환 처리 |
| 2024.11.12 | IP/MAC 주소 고정값 문제 | 실제 네트워크 인터페이스 조회 로직 구현 |
| 2024.11.13 | 좌석번호 null 문제 | 좌석 배치 저장 시 `pc_info.seat_number` 자동 업데이트 |
| 2024.11.17 | API 명세서 완성도 부족 | 구조화, 예제 코드, Quick Start 추가 |

---

## 🐛 알려진 이슈

| 우선순위 | 제목 | 상태 | 비고 |
|---------|------|------|------|
| High | 명령 실행 결과 보고 미구현 | 📋 TODO | API 명세는 존재하나 실제 구현 필요 |
| High | Windows 계정 관리 미구현 | 📋 TODO | API 명세 작성 완료, pywin32 활용 구현 예정 |
| Medium | 네트워크 끊김 시 재연결 로직 | 📋 TODO | 하트비트 실패 시 자동 재등록 필요 |
| Medium | 명령 실행 timeout 처리 | 📋 TODO | 장시간 소요 명령에 대한 타임아웃 및 에러 처리 |
| Low | GPU 정보 수집 (선택) | 📋 미정 | 필요시 추가 |
| Low | 클라이언트의 `Win32 exception` 경고 | ℹ️ 정보 | WMI COM 객체 해제 과정에서 발생, 기능에 영향 없음 |

---

## 📝 주요 결정사항

### 아키텍처
1. **정적/동적 정보 분리**: 클라이언트의 부하를 줄이기 위해 등록 시에만 정적 정보를, 하트비트 시에는 동적 정보만 전송
2. **Long-polling**: WebSocket 대신 간단한 30초 폴링으로 명령 시스템 구현 (방화벽 호환성 우수)
3. **세션 기반 인증**: 웹 UI는 Flask 세션 쿠키 사용, 클라이언트는 machine_id로 식별
4. **DB 선택**: SQLite (경량, 로컬 테스트 용이, 40대 PC 규모에 적합)

### 데이터 수집
5. **프로세스 로깅**: 사용자가 직접 설치한 프로그램 위주로 필터링하여 `heartbeat`에 포함
   - Windows 시스템 프로세스 제외
   - C:\Windows 폴더 외부 실행 파일만 수집
6. **네트워크 정보**: 활성 인터페이스에서 자동으로 IP/MAC 추출

### 보안
7. **비밀번호 전송**: HTTPS 사용 권장 (현재 HTTP는 개발 환경용)
8. **명령 권한**: 관리자 로그인 필요, 세션 확인 후 명령 전송

### 배포
9. **빌드 자동화**: PyInstaller + GitHub Actions로 Windows 실행 파일 자동 생성
10. **Windows 서비스**: nssm 또는 pywin32를 활용하여 백그라운드 서비스로 실행 예정

---

## 📌 다음 작업 (우선순위 순)

### 🔴 High Priority

1. **Windows 계정 관리 기능 구현** (`executor.py`)
   - `win32net` 또는 `win32security` API 활용
   - 계정 생성: `win32net.NetUserAdd()`
   - 계정 삭제: `win32net.NetUserDel()`
   - 비밀번호 변경: `win32net.NetUserSetInfo()`
   - 테스트 및 에러 처리

2. **명령 실행 결과 보고 시스템**
   - `pc_command` 테이블에 `result`, `executed_at` 컬럼 추가
   - `/api/client/command/result` 엔드포인트 구현
   - 클라이언트에서 명령 실행 후 결과 전송 로직 추가

3. **Windows 서비스 등록**
   - `pywin32` 활용 서비스 스크립트 작성
   - 자동 시작 설정
   - 서비스 재시작 시 자동 복구

### 🟡 Medium Priority

4. **에러 처리 강화**
   - 네트워크 끊김 시 자동 재등록
   - 명령 실행 타임아웃 처리
   - 로그 파일 생성 및 로테이션

5. **관리자 UI 개선**
   - 실시간 PC 상태 업데이트 (AJAX polling)
   - 명령 실행 진행 상황 표시
   - 일괄 명령 전송 기능

### 🟢 Low Priority

6. **추가 기능**
   - 파일 업로드 (서버 → 클라이언트)
   - 클라이언트 자동 업데이트
   - GPU 정보 수집
   - 사용 통계 및 리포트 기능

---

## 📊 Phase별 세부 진행률

```
Phase 1 (서버):     ████████████████████ 100%
Phase 2 (클라이언트): ████████████████████ 100%
Phase 3 (제어):     ████████████░░░░░░░░  60%
Phase 4 (문서화):   █████████████████░░░  85%
Phase 5 (배포):     ███░░░░░░░░░░░░░░░░░  15%
```

---

## 🎓 학습 및 개선 사항

### 배운 점
- Flask의 세션 관리 및 SQLite 연동
- WMI를 활용한 Windows 시스템 정보 수집
- Long-polling 방식의 실시간 통신 구현
- psutil을 통한 크로스 플랫폼 시스템 모니터링
- PyInstaller를 활용한 Python 실행 파일 배포

### 개선할 점
- 에러 로깅 시스템 체계화
- 단위 테스트 작성 (pytest)
- 코드 주석 및 docstring 보완
- 설정 파일 분리 (config.py)
- 환경 변수 활용 (보안 정보 분리)

---

## 📞 참고 자료

- [Flask 공식 문서](https://flask.palletsprojects.com/)
- [psutil 문서](https://psutil.readthedocs.io/)
- [PyWin32 문서](https://pypi.org/project/pywin32/)
- [SQLite 문서](https://www.sqlite.org/docs.html)
- [Windows Net Management Functions](https://docs.microsoft.com/en-us/windows/win32/api/lmaccess/)