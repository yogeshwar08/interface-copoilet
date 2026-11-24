#!/usr/bin/env bash
# ============================================================
# Local PostgreSQL Automated Backup Script
# Creates a timestamped dump in backups/
# Can be run interactively or configured in cron.
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="${SCRIPT_DIR}/../backups"
mkdir -p "${BACKUP_DIR}"

CONTAINER_NAME="enterprise_copilot_postgres"
DB_NAME="${POSTGRES_DB:-aegisdb}"
DB_USER="${POSTGRES_USER:-aegis_readonly}"

TIMESTAMP=$(date +"%Y-%m-%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/agentic_copilot_${TIMESTAMP}.sql"

echo "============================================================"
echo " 💾 Local PostgreSQL Backup Utility"
echo "============================================================"
echo "Database  : ${DB_NAME}"
echo "User      : ${DB_USER}"
echo "Container : ${CONTAINER_NAME}"
echo "Target    : ${BACKUP_FILE}"
echo ""

# Verify container is running
if ! docker ps --filter "name=${CONTAINER_NAME}" --filter "status=running" -q | grep -q .; then
    echo "❌ Error: Container '${CONTAINER_NAME}' is not running."
    echo "Start it with: docker compose up -d postgres"
    exit 1
fi

echo "Exporting database..."
docker exec "${CONTAINER_NAME}" pg_dump -U "${DB_USER}" -d "${DB_NAME}" --clean --if-exists --no-owner --no-acl > "${BACKUP_FILE}"

if [ -f "${BACKUP_FILE}" ]; then
    SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
    echo "✅ SUCCESS: Database backup created successfully!"
    echo "File : ${BACKUP_FILE} (${SIZE})"
    echo "Time : $(date)"
    echo ""
    echo "To restore this backup, run:"
    echo "  bash scripts/restore_db.sh \"${BACKUP_FILE}\""
else
    echo "❌ Error: Backup failed, file not found."
    exit 1
fi
