#!/usr/bin/env bash
# ==============================================================================
# WeatherGPT PostgreSQL + PostGIS Backup & Recovery Automation Script
# ==============================================================================
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/weathergpt}"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_NAME="${POSTGRES_DB:-weathergpt}"
DB_USER="${POSTGRES_USER:-weathergpt}"
TIMESTAMP="$(date +'%Y%m%d_%H%M%S')"
BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.dump"

mkdir -p "${BACKUP_DIR}"

usage() {
    echo "Usage: $0 {backup|restore <file>|list}"
    exit 1
}

do_backup() {
    echo "[INFO] Starting PostgreSQL/PostGIS binary backup for ${DB_NAME}..."
    PGPASSWORD="${POSTGRES_PASSWORD:-}" pg_dump \
        -h "${DB_HOST}" \
        -p "${DB_PORT}" \
        -U "${DB_USER}" \
        -F c \
        -b \
        -v \
        -f "${BACKUP_FILE}" \
        "${DB_NAME}"
    echo "[SUCCESS] Backup completed: ${BACKUP_FILE} ($(du -h "${BACKUP_FILE}" | cut -f1))"
}

do_restore() {
    local target_dump="$1"
    if [[ ! -f "${target_dump}" ]]; then
        echo "[ERROR] Dump file not found: ${target_dump}"
        exit 1
    fi
    echo "[WARNING] Restoring database '${DB_NAME}' from ${target_dump}..."
    PGPASSWORD="${POSTGRES_PASSWORD:-}" pg_restore \
        -h "${DB_HOST}" \
        -p "${DB_PORT}" \
        -U "${DB_USER}" \
        -d "${DB_NAME}" \
        --clean \
        --if-exists \
        -v \
        "${target_dump}"
    echo "[SUCCESS] Database restore complete. Verifying migrations..."
    alembic upgrade head
    echo "[SUCCESS] Alembic head verified."
}

do_list() {
    echo "[INFO] Available database backups in ${BACKUP_DIR}:"
    ls -lh "${BACKUP_DIR}"/*.dump 2>/dev/null || echo "No dumps found."
}

case "${1:-}" in
    backup)
        do_backup
        ;;
    restore)
        if [[ -z "${2:-}" ]]; then
            usage
        fi
        do_restore "$2"
        ;;
    list)
        do_list
        ;;
    *)
        usage
        ;;
esac
