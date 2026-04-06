#!/usr/bin/env bash
# Migration squash script — consolidates all Alembic migrations into a single baseline.
# Usage: ./scripts/squash-migrations.sh [--i-know-what-i-am-doing]
#
# Requires: pg_dump, uv, running PostgreSQL
# Env vars: DATABASE__URL (or defaults to local dev DB)

set -euo pipefail
cd "$(dirname "$0")/.."

# ── Colors ──
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}✓${NC} $1"; }
warn()  { echo -e "${YELLOW}⚠${NC} $1"; }
fail()  { echo -e "${RED}✗${NC} $1"; exit 1; }

# ── Safety gate ──
FORCE_FLAG="--i-know-what-i-am-doing"
FORCE=false

for arg in "$@"; do
    if [ "$arg" = "$FORCE_FLAG" ]; then
        FORCE=true
    fi
done

if [ "$FORCE" = false ]; then
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║  MIGRATION SQUASH — DESTRUCTIVE OPERATION                   ║"
    echo "║                                                              ║"
    echo "║  This will:                                                  ║"
    echo "║    1. Archive all current migrations to alembic/archive/     ║"
    echo "║    2. Create a single baseline migration                     ║"
    echo "║    3. Stamp the DB with the new head                        ║"
    echo "║                                                              ║"
    echo "║  All active branches must rebase after this operation.       ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
    read -p "Continue? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 0
    fi
fi

# ── Pre-flight checks ──
DATESTAMP=$(date +%Y%m%d)

# 1. Verify alembic is current (no pending migrations)
info "Checking migration state..."
if ! uv run alembic check 2>&1; then
    fail "Database is not up-to-date. Run 'make db-migrate' first."
fi

# 2. Count existing migrations
MIGRATION_COUNT=$(find alembic/versions -name "*.py" -not -name "__pycache__" -not -name "__init__.py" | wc -l | tr -d ' ')
if [ "$MIGRATION_COUNT" -lt 2 ]; then
    fail "Only ${MIGRATION_COUNT} migration(s) found — nothing to squash."
fi
info "Found ${MIGRATION_COUNT} migrations to squash."

# 3. Create backup
info "Creating pre-squash database backup..."
if [ -f "scripts/backup_db.sh" ]; then
    bash scripts/backup_db.sh ./backups/pre-squash
else
    warn "backup_db.sh not found — skipping backup."
fi

# ── Squash ──

# 4. Dump current schema as baseline SQL (for reference/audit)
DB_URL="${DATABASE__URL:-postgresql://postgres:postgres@localhost:5432/email_hub}"
# Strip asyncpg driver prefix
PLAIN_URL=$(echo "$DB_URL" | sed 's|+asyncpg||')

DB_USER=$(echo "$PLAIN_URL" | sed -n 's|.*://\([^:]*\):.*|\1|p')
DB_PASS=$(echo "$PLAIN_URL" | sed -n 's|.*://[^:]*:\([^@]*\)@.*|\1|p')
DB_HOST=$(echo "$PLAIN_URL" | sed -n 's|.*@\([^:]*\):.*|\1|p')
DB_PORT=$(echo "$PLAIN_URL" | sed -n 's|.*:\([0-9]*\)/.*|\1|p')
DB_NAME=$(echo "$PLAIN_URL" | sed -n 's|.*/\([^?]*\).*|\1|p')

info "Dumping schema baseline..."
PGPASSWORD="$DB_PASS" pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --schema-only \
    --no-owner \
    --no-privileges \
    --exclude-table=alembic_version \
    > "alembic/baseline_schema_${DATESTAMP}.sql"
info "Schema saved to alembic/baseline_schema_${DATESTAMP}.sql"

# 5. Archive old migrations
ARCHIVE_DIR="alembic/archive/${DATESTAMP}"
mkdir -p "$ARCHIVE_DIR"
info "Archiving ${MIGRATION_COUNT} migrations to ${ARCHIVE_DIR}/..."
mv alembic/versions/*.py "$ARCHIVE_DIR/"

# 6. Create baseline migration via autogenerate
info "Generating baseline migration..."
uv run alembic revision --autogenerate -m "baseline_squash_${DATESTAMP}"

# 7. Stamp DB with new head (schema already matches — skip running the migration)
info "Stamping database with new baseline head..."
uv run alembic stamp head

# ── Verify ──
info "Verifying..."
uv run alembic check 2>&1 || fail "Post-squash alembic check failed!"

NEW_COUNT=$(find alembic/versions -name "*.py" -not -name "__init__.py" -not -name "__pycache__" | wc -l | tr -d ' ')

echo ""
info "Squash complete!"
echo "  Archived: ${MIGRATION_COUNT} migrations → ${ARCHIVE_DIR}/"
echo "  Baseline: ${NEW_COUNT} migration(s) in alembic/versions/"
echo "  Schema:   alembic/baseline_schema_${DATESTAMP}.sql"
echo ""
warn "ACTION REQUIRED: All active branches must rebase onto this commit."
echo "  Verify with: uv run alembic check"
echo "  Fresh DB test: uv run alembic upgrade head"
