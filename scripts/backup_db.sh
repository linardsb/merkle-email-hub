#!/usr/bin/env bash
# Database backup script for merkle-email-hub.
# Usage: ./scripts/backup_db.sh [backup_dir]
#
# Requires: pg_dump, gzip
# Env vars: DATABASE__URL (or defaults to local dev DB)

set -euo pipefail

BACKUP_DIR="${1:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/merkle_email_hub_${TIMESTAMP}.sql.gz"

# Parse DATABASE__URL or fall back to default
DB_URL="${DATABASE__URL:-postgresql://postgres:postgres@localhost:5432/merkle_email_hub}"

# Extract connection parts from URL
# Format: postgresql://user:pass@host:port/dbname
DB_USER=$(echo "$DB_URL" | sed -n 's|.*://\([^:]*\):.*|\1|p')
DB_PASS=$(echo "$DB_URL" | sed -n 's|.*://[^:]*:\([^@]*\)@.*|\1|p')
DB_HOST=$(echo "$DB_URL" | sed -n 's|.*@\([^:]*\):.*|\1|p')
DB_PORT=$(echo "$DB_URL" | sed -n 's|.*:\([0-9]*\)/.*|\1|p')
DB_NAME=$(echo "$DB_URL" | sed -n 's|.*/\([^?]*\).*|\1|p')

# Strip asyncpg driver prefix if present
DB_NAME=$(echo "$DB_NAME" | sed 's/+asyncpg//')

mkdir -p "$BACKUP_DIR"

echo "Backing up database '${DB_NAME}' to ${BACKUP_FILE}..."

PGPASSWORD="$DB_PASS" pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --no-owner \
    --no-privileges \
    --format=plain \
    | gzip > "$BACKUP_FILE"

echo "Backup complete: ${BACKUP_FILE} ($(du -h "$BACKUP_FILE" | cut -f1))"

# Retention: keep last 30 backups, remove older ones
KEEP=30
BACKUP_COUNT=$(find "$BACKUP_DIR" -name "merkle_email_hub_*.sql.gz" | wc -l | tr -d ' ')
if [ "$BACKUP_COUNT" -gt "$KEEP" ]; then
    REMOVE_COUNT=$((BACKUP_COUNT - KEEP))
    echo "Pruning ${REMOVE_COUNT} old backup(s)..."
    find "$BACKUP_DIR" -name "merkle_email_hub_*.sql.gz" -type f \
        | sort | head -n "$REMOVE_COUNT" | xargs rm -f
fi

echo "Done. ${BACKUP_COUNT} backup(s) in ${BACKUP_DIR}."
