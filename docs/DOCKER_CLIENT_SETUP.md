# Windows Docker 컨테이너에 WCMS 클라이언트 설치 가이드

> dockurr/windows 컨테이너에 WCMS 클라이언트를 설치하는 방법

---

## 준비 사항

1. **Windows 컨테이너 실행 중**
2. **VNC 접속**: http://localhost:8006
3. **클라이언트 EXE 빌드 완료**

---

## 방법 1: 공유 폴더 사용

dockurr/windows는 `/shared` 폴더를 통해 호스트와 파일을 공유할 수 있습니다.

### 1단계: 클라이언트 빌드 및 복사

Windows 호스트에서:

```powershell
# 클라이언트 EXE 빌드
python manage.py build

# 공유 폴더에 복사
Copy-Item client/dist/WCMS-Client.exe shared/WCMS-Client.exe
```

### 2단계: Windows 컨테이너에서 접근

VNC 접속 (http://localhost:8006) → 파일 탐색기:

```
\\host.lan\Data
```

또는 PowerShell:

```powershell
# 공유 폴더 매핑
net use Z: \\host.lan\Data

# 바탕화면에 복사
Copy-Item Z:\WCMS-Client.exe C:\Users\Administrator\Desktop\
```

### 3단계: 설치 및 실행

1. 바탕화면의 `WCMS-Client.exe` 실행
2. 서버 주소: `http://wcms-server:5050`
3. 서비스 설치 (선택):
   ```powershell
   C:\Users\Administrator\Desktop\WCMS-Client.exe install
   Start-Service WCMS-Client
   ```

---

## 방법 2: Docker cp 명령 사용

### 1단계: 클라이언트 빌드

```powershell
python manage.py build
```

### 2단계: 컨테이너에 복사

```powershell
# 파일을 컨테이너에 직접 복사
docker cp client/dist/WCMS-Client.exe wcms-test-win:C:/Users/Administrator/Desktop/
```

### 3단계: VNC로 설치

1. http://localhost:8006 접속
2. 바탕화면의 `WCMS-Client.exe` 실행

---

## 방법 3: 네트워크로 다운로드

### 1단계: 호스트에서 간이 웹 서버 실행

Windows 호스트에서:

```powershell
# Python 웹 서버 실행 (client/dist 디렉토리에서)
cd client/dist
python -m http.server 8000
```

### 2단계: Windows 컨테이너에서 다운로드

VNC 접속 → PowerShell 실행:

```powershell
# 호스트 IP 확인 (Docker 네트워크)
# host.docker.internal:8000 사용

# Edge 브라우저로 다운로드
Start-Process "http://host.docker.internal:8000/WCMS-Client.exe"

# 또는 PowerShell로 다운로드
Invoke-WebRequest -Uri "http://host.docker.internal:8000/WCMS-Client.exe" `
    -OutFile "C:\Users\Administrator\Desktop\WCMS-Client.exe"
```

---

## 방법 3: 네트워크로 다운로드

### 1단계: 호스트에서 간이 웹 서버 실행

Windows 호스트에서:

```powershell
# Python 웹 서버 실행 (client/dist 디렉토리에서)
cd client/dist
python -m http.server 8000
```

### 2단계: Windows 컨테이너에서 다운로드

VNC 접속 → PowerShell 실행:

```powershell
# 호스트 IP 확인 (Docker 네트워크)
# host.docker.internal:8000 사용

# Edge 브라우저로 다운로드
Start-Process "http://host.docker.internal:8000/WCMS-Client.exe"

# 또는 PowerShell로 다운로드
Invoke-WebRequest -Uri "http://host.docker.internal:8000/WCMS-Client.exe" `
    -OutFile "C:\Users\Administrator\Desktop\WCMS-Client.exe"
```

---

## 방법 4: 서버의 자동 업데이트 기능 사용

### 1단계: 서버에 클라이언트 등록

```powershell
# 클라이언트를 서버의 static/client 폴더에 복사
Copy-Item client/dist/WCMS-Client.exe server/static/client/WCMS-Client.exe
```

### 2단계: Windows 컨테이너에서 다운로드

VNC 접속 → Edge 브라우저:

```
http://wcms-server:5050/static/client/WCMS-Client.exe
```

---

## 클라이언트 설정

### config.json 생성

`C:\ProgramData\WCMS\config.json` 생성:

```json
{
  "SERVER_URL": "http://wcms-server:5050",
  "HEARTBEAT_INTERVAL": 10,
  "POLL_TIMEOUT": 10
}
```

### 서비스 설치

관리자 권한 PowerShell:

```powershell
# 서비스 설치
C:\Users\Administrator\Desktop\WCMS-Client.exe install

# 서비스 시작
Start-Service WCMS-Client

# 상태 확인
Get-Service WCMS-Client
```

---

## 자동화 스크립트

### setup-client.ps1

```powershell
# WCMS 클라이언트 자동 설치 스크립트
param(
    [string]$ServerUrl = "http://wcms-server:5050"
)

Write-Host "WCMS 클라이언트 설치 시작..."

# 1. 다운로드
$DownloadUrl = "$ServerUrl/static/client/WCMS-Client.exe"
$DestPath = "C:\Users\Administrator\Desktop\WCMS-Client.exe"

Write-Host "다운로드 중: $DownloadUrl"
Invoke-WebRequest -Uri $DownloadUrl -OutFile $DestPath

# 2. 설정 디렉토리 생성
$ConfigDir = "C:\ProgramData\WCMS"
if (-not (Test-Path $ConfigDir)) {
    New-Item -ItemType Directory -Path $ConfigDir -Force | Out-Null
}

# 3. config.json 생성
$Config = @{
    SERVER_URL = $ServerUrl
    HEARTBEAT_INTERVAL = 10
    POLL_TIMEOUT = 10
} | ConvertTo-Json

Set-Content -Path "$ConfigDir\config.json" -Value $Config

# 4. 서비스 설치
Write-Host "서비스 설치 중..."
& $DestPath install

# 5. 서비스 시작
Write-Host "서비스 시작 중..."
Start-Service WCMS-Client

# 6. 상태 확인
$Service = Get-Service WCMS-Client
Write-Host "클라이언트 상태: $($Service.Status)"

Write-Host "✅ 설치 완료!"
```

---

## 테스트

### 1. 클라이언트 등록 확인

서버 웹 UI: http://localhost:5050

### 2. Heartbeat 확인

서버 로그:

```powershell
docker logs wcms-server -f | Select-String "heartbeat"
```

### 3. 명령 전송 테스트

웹 UI에서:
- PC 선택
- "정보 확인" 클릭
- 시스템 정보가 표시되면 성공

---

## 트러블슈팅

### 클라이언트가 서버에 연결 안 됨

**증상:**
- 서버 로그에 heartbeat 없음
- 클라이언트 오프라인 상태

**해결:**
1. 네트워크 연결 확인:
   ```powershell
   Test-NetConnection wcms-server -Port 5050
   ```

2. 서비스 로그 확인:
   ```powershell
   Get-EventLog -LogName Application -Source WCMS-Client -Newest 10
   ```

3. 수동 실행 테스트:
   ```powershell
   C:\Users\Administrator\Desktop\WCMS-Client.exe
   ```

### 서비스 설치 실패

**증상:**
```
Access Denied
```

**해결:**
- 관리자 권한 PowerShell 실행

### config.json 인식 안 됨

**증상:**
- 기본 서버 주소(localhost) 사용

**해결:**
- 경로 확인: `C:\ProgramData\WCMS\config.json`
- JSON 형식 확인

---

## 백업에 클라이언트 포함하기

클라이언트 설치 완료 후:

```powershell
# 1. 컨테이너 중지
docker compose down

# 2. 백업 생성
.\scripts\backup-windows.ps1

# 결과: backups/windows-with-client-{timestamp}.tar.gz
```

이후 이 백업을 복원하면 클라이언트가 이미 설치된 상태로 시작됩니다!

---

## 참고

- 클라이언트 빌드: `python manage.py build`
- 서버 자동 업데이트: [CLIENT_AUTO_UPDATE.md](CLIENT_AUTO_UPDATE.md)
- Docker 백업: [DOCKER_WINDOWS_BACKUP.md](DOCKER_WINDOWS_BACKUP.md)
