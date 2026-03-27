#!/usr/bin/env bash
# Restore database from backup on production server
# Usage: ./restore-db.sh [backup_file]
#   No args = restores latest backup
#   With arg = restores specified file
set -euo pipefail

BACKUP_DIR="/data/backups/email-hub"
CONTAINER="$(docker ps --format '{{.Names}}' | grep -m1 'db-1' | grep i7kcm)"

if [ -z "$CONTAINER" ]; then
    echo "ERROR: DB container not found" >&2
    exit 1
fi

# Select backup file
if [ -n "${1:-}" ]; then
    BACKUP_FILE="$1"
else
    BACKUP_FILE=$(ls -t "${BACKUP_DIR}"/email_hub_*.sql.gz 2>/dev/null | head -1)
fi

if [ -z "$BACKUP_FILE" ] || [ ! -f "$BACKUP_FILE" ]; then
    echo "ERROR: No backup file found" >&2
    echo "Available backups:"
    ls -lh "${BACKUP_DIR}"/email_hub_*.sql.gz 2>/dev/null || echo "  (none)"
    exit 1
fi

echo "Restoring from: ${BACKUP_FILE}"
echo "Target: ${CONTAINER} / email_hub"
read -p "This will OVERWRITE the current database. Continue? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

# Truncate all tables (preserves schema + alembic_version)
TABLES=$(docker exec "$CONTAINER" psql -U emailhub email_hub -tAc \
    "SELECT string_agg('\"' || tablename || '\"', ',') FROM pg_tables WHERE schemaname='public' AND tablename != 'alembic_version';")

if [ -n "$TABLES" ]; then
    docker exec "$CONTAINER" psql -U emailhub email_hub -c "TRUNCATE ${TABLES} CASCADE;"
    echo "Tables truncated."
fi

# Restore data
gunzip -c "$BACKUP_FILE" | docker exec -i "$CONTAINER" psql -U emailhub email_hub --quiet 2>&1 \
    | grep -v "already exists" || true

echo "Restore complete. Verifying..."
docker exec "$CONTAINER" psql -U emailhub email_hub -c \
    "SELECT 'components' as tbl, COUNT(*) FROM components UNION ALL SELECT 'projects', COUNT(*) FROM projects UNION ALL SELECT 'users', COUNT(*) FROM users;"
