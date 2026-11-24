<#
.SYNOPSIS
    Automated Backup Script for Local PostgreSQL Container.
.DESCRIPTION
    Creates a timestamped SQL backup in the backups/ directory.
    Can be run manually or scheduled via Windows Task Scheduler.
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$ContainerName = "enterprise_copilot_postgres",

    [Parameter(Mandatory=$false)]
    [string]$DbName = $env:POSTGRES_DB,

    [Parameter(Mandatory=$false)]
    [string]$DbUser = $env:POSTGRES_USER,

    [Parameter(Mandatory=$false)]
    [string]$BackupDir
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($DbName)) { $DbName = "aegisdb" }
if ([string]::IsNullOrWhiteSpace($DbUser)) { $DbUser = "aegis_readonly" }

if ([string]::IsNullOrWhiteSpace($BackupDir)) {
    $BackupDir = Join-Path $PSScriptRoot "..\backups"
}

if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir | Out-Null
}

$timestamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$filename = "agentic_copilot_$timestamp.sql"
$targetPath = Join-Path $BackupDir $filename

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " 💾 Local PostgreSQL Backup Utility" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Database  : $DbName"
Write-Host "User      : $DbUser"
Write-Host "Container : $ContainerName"
Write-Host "Target    : $targetPath"
Write-Host "`nRunning pg_dump via Docker container..." -ForegroundColor Cyan

# Verify container is running
$isRunning = (docker ps --filter "name=$ContainerName" --filter "status=running" -q) -ne ""
if (-not $isRunning) {
    Write-Error "PostgreSQL container '$ContainerName' is not running. Start it with: docker compose up -d postgres"
    exit 1
}

# Run pg_dump from inside container
& docker exec $ContainerName pg_dump -U $DbUser -d $DbName --clean --if-exists --no-owner --no-acl | Set-Content -Path $targetPath -Encoding UTF8

if (Test-Path $targetPath) {
    $sizeKb = [math]::Round((Get-Item $targetPath).Length / 1KB, 2)
    Write-Host "`n✅ SUCCESS: Database backup created successfully!" -ForegroundColor Green
    Write-Host "File : $targetPath ($sizeKb KB)" -ForegroundColor Green
    Write-Host "Time : $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Green
    Write-Host "`nTo restore this backup at any time, run:" -ForegroundColor Cyan
    Write-Host "  powershell -File scripts/restore_db.ps1 -BackupFile `"$targetPath`"" -ForegroundColor White
} else {
    Write-Error "Backup creation failed: file not generated."
    exit 1
}
