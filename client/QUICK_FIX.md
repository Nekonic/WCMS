# WCMS 클라이언트 빠른 진단 가이드

## 현재 상황
서비스는 설치/시작되었으나 웹에서 PC가 보이지 않음

## 즉시 확인할 것

### 1. 서비스 런타임 로그 확인
```
C:\ProgramData\WCMS\logs\service_runtime.log
```

이 로그에서 다음을 확인:
- "main 모듈 임포트 성공" 메시지가 있는지
- 오류 메시지가 있는지 (ImportError, ModuleNotFoundError 등)

### 2. 클라이언트 로그 확인
```
C:\ProgramData\WCMS\logs\client.log
```

이 파일이 **생성조차 안 되었다면**: main.py가 실행되지 않은 것
이 파일이 **있다면**: 내용 확인
- "WCMS 클라이언트 시작..." 메시지
- "서버에 클라이언트 등록 시도..." 메시지
- 오류 메시지

### 3. 포그라운드 모드로 직접 실행 (가장 확실한 방법)

명령 프롬프트(관리자 권한)에서:
```cmd
cd C:\Users\37w\Downloads
WCMS-Client.exe run
```

이 모드는:
- 콘솔 창에 직접 출력되므로 오류를 즉시 볼 수 있음
- 서비스가 아닌 포그라운드로 실행
- Ctrl+C로 중지 가능

**예상되는 출력:**
```
[*] WCMS 클라이언트 포그라운드 실행 중...
[*] 로그 파일 위치: C:\ProgramData\WCMS\logs\client.log
[*] Ctrl+C로 중지
```

그 다음 로그 파일에 뭔가 기록되는지 확인

### 4. 오류별 해결 방법

#### 오류: "Failed to extract Pythonwin#mfc140u.dll: decompression resulted in return code -1!"
**원인:** UPX 압축이 pywin32 DLL과 호환되지 않음
**해결:** build.spec에서 upx=False로 설정 (이미 수정됨) 후 재빌드 필요

#### 오류: "No module named 'collector'" 또는 "No module named 'executor'"
**원인:** PyInstaller가 모듈을 포함하지 못함
**해결:** build.spec 수정 (이미 수정함) 후 재빌드 필요

#### 오류: "No module named 'win32timezone'" (또는 다른 win32*)
**원인:** pywin32 모듈 누락
**해결:** build.spec의 hiddenimports에 추가 (이미 추가됨) 후 재빌드

#### 오류: 네트워크 관련 (Connection refused, timeout 등)
**원인:** 서버에 접속 불가
**해결:**
```cmd
# 서버 연결 테스트 (예시)
ping your-server-hostname
curl http://your-server:5050
```

#### 로그 파일이 아예 없음
**원인:** 
1. main.py가 import조차 안 됨 (모듈 누락)
2. 권한 문제로 로그 폴더 생성 실패

**해결:**
```cmd
mkdir C:\ProgramData\WCMS\logs
icacls C:\ProgramData\WCMS\logs /grant Everyone:(OI)(CI)F
```

### 5. 서비스 재시작
```cmd
sc stop WCMSClient
sc start WCMSClient
```

재시작 후 `service_runtime.log` 다시 확인

## 추가 진단 명령

### 서비스 상태 상세
```cmd
sc query WCMSClient
sc qc WCMSClient
```

### Windows 이벤트 로그 확인
```cmd
eventvwr.msc
```
→ Windows 로그 → 응용 프로그램 → "WCMSClient" 필터

### 프로세스 확인
```cmd
tasklist | findstr WCMS
```

## 가장 가능성 높은 문제

현재 상황으로 봐서는:
1. **PyInstaller 빌드 이슈**: collector.py, executor.py가 EXE에 제대로 포함되지 않음
2. **임포트 오류**: service.py에서 `from main import run_client` 실패

→ **해결책**: 수정된 build.spec으로 재빌드 필요

## 임시 해결책 (재빌드 전)

현재 빌드된 EXE로는 작동 안 할 가능성이 높습니다.

다음 빌드 시 적용된 수정사항:
1. build.spec에 main.py, collector.py, executor.py 명시적 포함
2. service_runtime.log 추가로 상세한 오류 로깅
3. 포그라운드 모드 (`run` 인자) 지원

## 다음 단계

1. `WCMS-Client.exe run` 실행 후 오류 확인
2. `service_runtime.log` 확인
3. 새 태그 푸시하여 재빌드 (예: client-v1.0.1)
4. 새 EXE로 재설치

