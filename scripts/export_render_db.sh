#!/usr/bin/env bash
# ============================================================
# Render PostgreSQL Recovery & Export Tool
# Accepts RENDER_DATABASE_URL via environment variable or argument.
# Exports database safely to backups/ without hardcoding secrets.
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="${SCRIPT_DIR}/../backups"
mkdir -p "${BACKUP_DIR}"

RENDER_URL="${1:-${RENDER_DATABASE_URL:-}}"

echo "============================================================"
echo " 📦 Render PostgreSQL Recovery & Export Tool"
echo "============================================================"

if [ -z "${RENDER_URL}" ]; then
    echo "RENDER_DATABASE_URL is not set."
    read -rp "Please enter Render PostgreSQL connection string (postgresql://...): " RENDER_URL
fi

if [ -z "${RENDER_URL}" ]; then
    echo "❌ Error: No connection URL provided. Aborting."
    exit 1
fi

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/render_backup_${TIMESTAMP}.sql"

echo "Output target: ${BACKUP_FILE}"
echo "Exporting database..."

if command -v pg_dump &> /dev/null; then
    echo "Using host pg_dump utility..."
    pg_dump "${RENDER_URL}" --no-owner --no-acl --clean --if-exists -f "${BACKUP_FILE}"
elif command -v docker &> /dev/null; then
    echo "Host pg_dump not found. Using Docker postgres:16-alpine..."
    docker run --rm \
        -v "${BACKUP_DIR}:/backups" \
        postgres:16-alpine \
        pg_dump "${RENDER_URL}" --no-owner --no-acl --clean --if-exists -f "/backups/render_backup_${TIMESTAMP}.sql"
else
    echo "❌ Neither pg_dump nor docker is available in PATH. Please install PostgreSQL client tools or Docker."
    exit 1
fi

if [ -f "${BACKUP_FILE}" ]; then
    SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
    echo "✅ SUCCESS: Render database exported successfully!"
    echo "Backup file: ${BACKUP_FILE} (${SIZE})"
    echo ""
    echo "To import this into your local PostgreSQL container, run:"
    echo "  bash scripts/import_local_db.sh \"${BACKUP_FILE}\""
else
    echo "❌ Export failed: backup file was not created."
    exit 1
fi
