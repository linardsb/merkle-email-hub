#!/usr/bin/env bash
# Automated database backup for production server
# Run via cron: 0 */6 * * * /data/scripts/backup-db.sh
#
# Keeps last 10 backups (60 hours of history)
set -euo pipefail

BACKUP_DIR="/data/backups/email-hub"
CONTAINER="$(docker ps --format '{{.Names}}' | grep -m1 'db-1' | grep i7kcm)"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/email_hub_${TIMESTAMP}.sql.gz"
MAX_BACKUPS=10

if [ -z "$CONTAINER" ]; then
    echo "ERROR: DB container not found" >&2
    exit 1
fi

# Dump and compress
docker exec "$CONTAINER" pg_dump -U emailhub email_hub --no-owner --no-acl \
    | gzip > "$BACKUP_FILE"

SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "Backup created: ${BACKUP_FILE} (${SIZE})"

# Rotate old backups
cd "$BACKUP_DIR"
ls -t email_hub_*.sql.gz 2>/dev/null | tail -n +$((MAX_BACKUPS + 1)) | xargs -r rm -f

echo "Backups on disk: $(ls email_hub_*.sql.gz | wc -l)"
