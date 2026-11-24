<#
.SYNOPSIS
    Restores a PostgreSQL backup into the local container.
.DESCRIPTION
    Prompts for confirmation before executing the restore.
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$BackupFile,

    [Parameter(Mandatory=$false)]
    [string]$ContainerName = "enterprise_copilot_postgres",

    [Parameter(Mandatory=$false)]
    [string]$DbName = $env:POSTGRES_DB,

    [Parameter(Mandatory=$false)]
    [string]$DbUser = $env:POSTGRES_USER
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($DbName)) { $DbName = "aegisdb" }
if ([string]::IsNullOrWhiteSpace($DbUser)) { $DbUser = "aegis_readonly" }

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " 🔄 Local PostgreSQL Database Restore Utility" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$backupDir = Join-Path $PSScriptRoot "..\backups"
if ([string]::IsNullOrWhiteSpace($BackupFile)) {
    if (Test-Path $backupDir) {
        $latest = Get-ChildItem -Path $backupDir -Filter "*.sql" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($latest) {
            $BackupFile = $latest.FullName
            Write-Host "No backup file specified. Auto-selected latest: $($latest.Name)" -ForegroundColor Yellow
        }
    }
}

if ([string]::IsNullOrWhiteSpace($BackupFile) -or -not (Test-Path $BackupFile)) {
    Write-Error "Backup file not found or not provided: '$BackupFile'"
    exit 1
}

$fileInfo = Get-Item $BackupFile
$sizeKb = [math]::Round($fileInfo.Length / 1KB, 2)

Write-Host "`nRestore Plan:" -ForegroundColor Yellow
Write-Host "  Source Backup : $($fileInfo.FullName) ($sizeKb KB)"
Write-Host "  Target DB     : $DbName"
Write-Host "  Target User   : $DbUser"
Write-Host "  Container     : $ContainerName"

Write-Host "`n⚠️  DANGER: This action will restore tables and overwrite data in '$DbName'." -ForegroundColor Red
$confirm = Read-Host "Type 'YES' to confirm and proceed with restoration"

if ($confirm -ne "YES") {
    Write-Host "Restore cancelled. Database remains unchanged." -ForegroundColor Yellow
    exit 0
}

Write-Host "`nRestoring backup into local container..." -ForegroundColor Cyan

# Check container running
$isRunning = (docker ps --filter "name=$ContainerName" --filter "status=running" -q) -ne ""
if (-not $isRunning) {
    Write-Host "Starting PostgreSQL container..." -ForegroundColor Yellow
    & docker compose up -d postgres
    Start-Sleep -Seconds 3
}

Get-Content -Path $BackupFile -Raw | docker exec -i $ContainerName psql -U $DbUser -d $DbName

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ SUCCESS: Database restored successfully!" -ForegroundColor Green
    Write-Host "Running schema and record verification..." -ForegroundColor Cyan
    $venvPy = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"
    $pyCmd = if (Test-Path $venvPy) { $venvPy } else { "python" }
    & $pyCmd (Join-Path $PSScriptRoot "verify_db.py")
} else {
    Write-Error "Restore operation encountered an error during psql execution."
    exit 1
}
