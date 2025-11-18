# 아카이브

이 디렉토리에는 통폐합 이전의 문서와 테스트 파일이 보관되어 있습니다.

## 📁 구조

```
archive/
├── docs/                # 구 문서 파일
│   ├── TESTING.md
│   ├── TESTING_GUIDE.md
│   ├── IMPLEMENTATION_SUMMARY.md
│   └── COMMAND_IMPLEMENTATION.md
│
└── tests/              # 구 테스트 파일
    ├── test_integration.py
    ├── test_bulk_commands.py
    └── test_commands.py
```

## 🔄 통폐합 내역

### 문서 통폐합 (2025.11.18)

**이전**: 9개의 분산된 문서
- README.md
- API.md
- DEVELOP.md
- STATUS.md
- TESTING.md
- TESTING_GUIDE.md
- IMPLEMENTATION_SUMMARY.md
- COMMAND_IMPLEMENTATION.md
- TEST_REPORT.md

**이후**: 3개의 핵심 문서
- **GUIDE.md** ⭐ - 통합 가이드 (설치, API, 테스트, 문제 해결)
- **README.md** - 프로젝트 개요 (간소화)
- **STATUS.md** - 진행 상황

**변경 이유**:
- 중복 내용 제거
- 사용자 편의성 향상
- 유지보수 부담 감소

### 테스트 통폐합 (2025.11.18)

**이전**: 6개의 개별 테스트
- server/test_web_access.py
- client/test_client.py
- client/test_api.py
- test_integration.py
- test_bulk_commands.py
- test_commands.py

**이후**: 2개의 테스트
- **test_all.py** ⭐ - 통합 테스트 (서버 + 클라이언트 + 일괄)
- server/test_web_access.py - 서버 API 단독 테스트

**변경 이유**:
- 한 번에 모든 테스트 실행 가능
- 테스트 중복 제거
- 일관된 테스트 결과 출력

## 📌 참고

기존 문서와 테스트는 필요시 참고할 수 있도록 보관되어 있습니다.  
새로운 프로젝트 문서는 루트 디렉토리의 **GUIDE.md**를 참조하세요.

---

**보관일**: 2025.11.18

