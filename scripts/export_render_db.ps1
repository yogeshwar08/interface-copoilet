<#
.SYNOPSIS
    Exports data from a remote Render PostgreSQL database if access is restored.
.DESCRIPTION
    Accepts RENDER_DATABASE_URL via environment variable, CLI parameter, or interactive prompt.
    Uses either local pg_dump or the local postgres Docker container to export the database.
    Stores the backup in the backups/ directory with a timestamp.
    NEVER hardcodes credentials.
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$RenderDatabaseUrl = $env:RENDER_DATABASE_URL
)

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " 📦 Render PostgreSQL Recovery & Export Tool" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

if ([string]::IsNullOrWhiteSpace($RenderDatabaseUrl)) {
    Write-Host "`nRENDER_DATABASE_URL environment variable is not set." -ForegroundColor Yellow
    $RenderDatabaseUrl = Read-Host "Please enter your Render PostgreSQL connection string (postgresql://...)"
}

if ([string]::IsNullOrWhiteSpace($RenderDatabaseUrl)) {
    Write-Error "Error: No database connection URL provided. Aborting export."
    exit 1
}

# Create backups directory
$backupDir = Join-Path $PSScriptRoot "..\backups"
if (-not (Test-Path $backupDir)) {
    New-Item -ItemType Directory -Path $backupDir | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupFilename = "render_backup_$timestamp.sql"
$backupFilePath = Join-Path $backupDir $backupFilename

Write-Host "`nTarget Output: $backupFilePath" -ForegroundColor Green
Write-Host "Starting export from remote database..." -ForegroundColor Yellow

# Check for local pg_dump, otherwise fallback to docker container
$hasLocalPgDump = (Get-Command pg_dump -ErrorAction SilentlyContinue) -ne $null
$dockerAvailable = (Get-Command docker -ErrorAction SilentlyContinue) -ne $null

if ($hasLocalPgDump) {
    Write-Host "Executing export using host pg_dump utility..." -ForegroundColor Cyan
    & pg_dump "$RenderDatabaseUrl" --no-owner --no-acl --clean --if-exists -f "$backupFilePath"
} elseif ($dockerAvailable) {
    Write-Host "Host pg_dump not found in PATH. Using Docker postgres:16-alpine container..." -ForegroundColor Cyan
    # Convert path to posix for docker mount
    $resolvedDir = (Resolve-Path $backupDir).Path
    $containerOutFile = "/backups/$backupFilename"
    & docker run --rm `
        -v "${resolvedDir}:/backups" `
        postgres:16-alpine `
        pg_dump "$RenderDatabaseUrl" --no-owner --no-acl --clean --if-exists -f "$containerOutFile"
} else {
    Write-Error "Neither 'pg_dump' nor 'docker' was found in system PATH. Please install PostgreSQL client tools or start Docker."
    exit 1
}

if (Test-Path $backupFilePath) {
    $fileSize = (Get-Item $backupFilePath).Length / 1KB
    Write-Host "`n✅ SUCCESS: Render database exported successfully!" -ForegroundColor Green
    Write-Host "Backup File: $backupFilePath ($([math]::Round($fileSize, 2)) KB)" -ForegroundColor Green
    Write-Host "`nTo import this data into your local database, run:" -ForegroundColor Cyan
    Write-Host "  powershell -File scripts/import_local_db.ps1 -BackupFile `"$backupFilePath`"" -ForegroundColor White
} else {
    Write-Error "Export completed without errors, but backup file was not created."
    exit 1
}
