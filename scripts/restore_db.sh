#!/usr/bin/env bash
# ============================================================
# Local PostgreSQL Database Restore Script
# Restores a SQL dump into local container.
# Requires explicit user confirmation.
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="${SCRIPT_DIR}/../backups"

BACKUP_FILE="${1:-}"
CONTAINER_NAME="enterprise_copilot_postgres"
DB_NAME="${POSTGRES_DB:-aegisdb}"
DB_USER="${POSTGRES_USER:-aegis_readonly}"

echo "============================================================"
echo " 🔄 Local PostgreSQL Database Restore Utility"
echo "============================================================"

if [ -z "${BACKUP_FILE}" ]; then
    if [ -d "${BACKUP_DIR}" ]; then
        LATEST=$(find "${BACKUP_DIR}" -name "*.sql" -type f -printf '%T+ %p\n' 2>/dev/null | sort -r | head -n1 | cut -d' ' -f2- || true)
        if [ -n "${LATEST}" ]; then
            BACKUP_FILE="${LATEST}"
            echo "Auto-selected latest backup: ${BACKUP_FILE}"
        fi
    fi
fi

if [ -z "${BACKUP_FILE}" ] || [ ! -f "${BACKUP_FILE}" ]; then
    echo "❌ Error: Backup file not found: '${BACKUP_FILE}'"
    exit 1
fi

SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)

echo ""
echo "Restore Plan:"
echo "  Source Backup : ${BACKUP_FILE} (${SIZE})"
echo "  Target DB     : ${DB_NAME}"
echo "  Target User   : ${DB_USER}"
echo "  Container     : ${CONTAINER_NAME}"
echo ""
echo "⚠️  DANGER: This action will restore tables and overwrite data in '${DB_NAME}'."
read -rp "Type 'YES' to confirm and proceed with restore: " CONFIRM

if [ "${CONFIRM}" != "YES" ]; then
    echo "Restore cancelled. No changes made."
    exit 0
fi

echo "Restoring into ${CONTAINER_NAME}..."

# Ensure container is running
if ! docker ps --filter "name=${CONTAINER_NAME}" --filter "status=running" -q | grep -q .; then
    echo "Starting container..."
    docker compose up -d postgres
    sleep 3
fi

docker exec -i "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" < "${BACKUP_FILE}"

echo "✅ Database restored successfully!"
python3 "${SCRIPT_DIR}/verify_db.py"
