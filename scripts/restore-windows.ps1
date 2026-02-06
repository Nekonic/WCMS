# Windows 볼륨 복원 스크립트

param(
    [Parameter(Mandatory=$false)]
    [string]$BackupFile
)

Write-Host "================================"
Write-Host "Windows 볼륨 복원"
Write-Host "================================"
Write-Host ""

# 백업 파일 선택
if (-not $BackupFile) {
    $backups = Get-ChildItem -Path "backups" -Filter "windows-*.tar.gz" | Sort-Object LastWriteTime -Descending

    if ($backups.Count -eq 0) {
        Write-Host "❌ 백업 파일이 없습니다."
        Write-Host "   백업을 먼저 생성하세요: .\scripts\backup-windows.ps1"
        exit 1
    }

    Write-Host "사용 가능한 백업:"
    for ($i = 0; $i -lt $backups.Count; $i++) {
        $backup = $backups[$i]
        $size = $backup.Length / 1GB
        Write-Host "  [$i] $($backup.Name) ($([math]::Round($size, 2)) GB) - $($backup.LastWriteTime)"
    }

    $choice = Read-Host "`n백업 번호 선택 [0]"
    if ([string]::IsNullOrWhiteSpace($choice)) {
        $choice = 0
    }

    $BackupFile = $backups[$choice].Name
}

$backupPath = "backups/$BackupFile"

if (-not (Test-Path $backupPath)) {
    Write-Host "❌ 백업 파일을 찾을 수 없습니다: $backupPath"
    exit 1
}

Write-Host ""
Write-Host "⚠️  경고: 현재 Windows 데이터가 삭제됩니다!"
Write-Host "  복원할 백업: $BackupFile"
$confirm = Read-Host "계속하시겠습니까? (yes/no)"

if ($confirm -ne "yes") {
    Write-Host "복원 취소됨"
    exit 0
}

Write-Host ""
Write-Host "[1/4] 컨테이너 중지..."
docker compose down

Write-Host "[2/4] 기존 볼륨 삭제..."
docker volume rm wcms_wcms-windows-data

Write-Host "[3/4] 새 볼륨 생성..."
docker volume create wcms_wcms-windows-data

Write-Host "[4/4] 백업 복원 중..."
docker run --rm `
    -v wcms_wcms-windows-data:/data `
    -v ${PWD}/backups:/backup `
    alpine tar xzf /backup/$BackupFile -C /data

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ 복원 완료!"
    Write-Host ""
    Write-Host "다음 명령으로 Windows 시작:"
    Write-Host "  python manage.py docker-test --skip-boot"
} else {
    Write-Host ""
    Write-Host "❌ 복원 실패"
    exit 1
}
