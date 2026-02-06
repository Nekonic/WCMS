# Windows 볼륨 백업 스크립트

Write-Host "================================"
Write-Host "Windows 볼륨 백업"
Write-Host "================================"
Write-Host ""

# 백업 디렉토리 생성
$backupDir = "backups"
if (-not (Test-Path $backupDir)) {
    New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
    Write-Host "✓ backups 디렉토리 생성"
}

# 타임스탬프
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupFile = "windows-clean-$timestamp.tar.gz"
$backupPath = "$backupDir/$backupFile"

Write-Host "[시작] Windows 볼륨 백업 중..."
Write-Host "  볼륨: wcms_wcms-windows-data"
Write-Host "  저장: $backupPath"
Write-Host "  예상 시간: 1-5분"
Write-Host ""

# 백업 실행
docker run --rm `
    -v wcms_wcms-windows-data:/data `
    -v ${PWD}/backups:/backup `
    alpine tar czf /backup/$backupFile -C /data .

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ 백업 완료!"
    Write-Host "  파일: $backupPath"

    # 파일 크기 확인
    if (Test-Path $backupPath) {
        $size = (Get-Item $backupPath).Length / 1GB
        Write-Host "  크기: $([math]::Round($size, 2)) GB"
    }
} else {
    Write-Host ""
    Write-Host "❌ 백업 실패"
    exit 1
}
