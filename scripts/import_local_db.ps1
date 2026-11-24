<#
.SYNOPSIS
    Imports a SQL backup file into the local PostgreSQL database.
.DESCRIPTION
    Safely imports database tables and records into the local PostgreSQL container.
    Requires explicit typing of "YES" before running destructive or overwrite operations.
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
Write-Host " 📥 PostgreSQL Local Database Import Tool" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# If no backup file specified, look for newest in backups/
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
    Write-Error "Backup file not found or not specified: '$BackupFile'"
    exit 1
}

$fileInfo = Get-Item $BackupFile
$sizeKb = [math]::Round($fileInfo.Length / 1KB, 2)

Write-Host "`nImport Plan:" -ForegroundColor Yellow
Write-Host "  Source File : $($fileInfo.FullName) ($sizeKb KB)"
Write-Host "  Target DB   : $DbName"
Write-Host "  Target User : $DbUser"
Write-Host "  Container   : $ContainerName"

Write-Host "`n⚠️  WARNING: Importing may overwrite existing records in database '$DbName'." -ForegroundColor Red
$confirm = Read-Host "Type 'YES' to proceed with importing into local PostgreSQL"

if ($confirm -ne "YES") {
    Write-Host "Import cancelled by user. No modifications were made." -ForegroundColor Yellow
    exit 0
}

Write-Host "`nExecuting import..." -ForegroundColor Cyan

# Verify container is running
$containerRunning = (docker ps --filter "name=$ContainerName" --filter "status=running" -q) -ne ""
if (-not $containerRunning) {
    Write-Host "Container '$ContainerName' is not running. Starting it with docker compose..." -ForegroundColor Yellow
    & docker compose up -d postgres
    Start-Sleep -Seconds 3
}

# Perform import via docker exec streaming stdin
Get-Content -Path $BackupFile -Raw | docker exec -i $ContainerName psql -U $DbUser -d $DbName

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ SUCCESS: Database import completed successfully!" -ForegroundColor Green
    Write-Host "Verifying imported schema and row counts..." -ForegroundColor Cyan
    $venvPy = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"
    $pyCmd = if (Test-Path $venvPy) { $venvPy } else { "python" }
    & $pyCmd (Join-Path $PSScriptRoot "verify_db.py")
} else {
    Write-Error "❌ Database import encountered an error during psql execution."
    exit 1
}
