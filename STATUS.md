# 프로젝트 진행 상황

최종 업데이트: 2025.11.04 (3주 경과)

## 📊 전체 진행률: 50%

### Phase 1: 서버 개발 (90%)
- [x] Flask 프로젝트 구조
- [x] SQLite 스키마 설계
- [x] 웹 UI 
  - [x] 대시보드
  - [x] 좌석 배치도
  - [x] 드래그&드롭 편집기
- [x] 관리자 로그인
- [x] PC 조회 API
- [x] PC 명령 보내기(shutdown, reboot, cmd)
- [ ] PC 파일 보내기
- [ ] PC 프로그램 원격 설치

### Phase 2: 클라이언트 기초 (90%)
- [x] 프로젝트 구조 설정
- [x] API 통신 테스트 (register, heartbeat)
- [x] 시스템 정보 수집 (실제 IP/MAC 조회)
- [x] 메인 루프 (threading, long-polling)
- [x] 명령 폴링 및 실행

### Phase 3: 클라이언트 제어 (0% 📋)
- [x] 명령 폴링 기능
- [x] 종료/재시작 실행
- [x] CMD 명령 실행
- [ ] 파일 받기
- [ ] 프로그램 원격 설치

### Phase 4: Windows 서비스 & 배포 (0% 📋)
- [x] GitHub Actions 자동 빌드 워크플로우 추가
- [x] PyInstaller 설정 (build.spec)
- [ ] Windows 서비스 등록
- [ ] 40대 PC 배포

---

## 🎯 다음 마일스톤

| 마일스톤     | 목표 일자      | 상태 |
|----------|------------|----|
| 클라이언트 상태 관리 | 2025.11.05 | 완료 |
| 원격 제어 기능 | 2025.11.10 | ⏳ 예정 |
| Windows 서비스화 | 2025.11.12 | ⏳ 예정 |
| 배포 & 테스트 | 2025.11.15 | ⏳ 예정 |

---

## 🐛 해결된 이슈

| 제목 | 해결 |
|------|------|
| WMI 스레드 오류 | CoInitialize 추가 |
| 무한 요청 루프 | Long-polling 타임아웃 추가 |
| disk_info 직렬화 오류 | JSON 변환 |
| IP/MAC 주소 고정값 | 실제 값 조회 |
| DB 스키마 오류 | FOREIGN KEY, 인덱싱 추가 |

---

## 🐛 알려진 이슈

| 우선순위 | 제목 | 상태 |
|---------|------|------|
| High | `pc_status` 테이블 인덱싱 필요 | 📋 미정 |
| Medium | 네트워크 끊김 시 재연결 로직 | 📋 미정 |
| Low | GPU 정보 수집 (선택) | 📋 미정 |

---

## 📝 주요 결정사항

1. **JSON 기반 명령 시스템**: command_type + command_data로 범용화
2. **Long-polling**: WebSocket 대신 간단한 30초 폴링
3. **배포**: PyInstaller + GitHub Actions
4. **DB**: SQLite (경량, 로컬 테스트 용이)

---
