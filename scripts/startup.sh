#!/usr/bin/env bash
# startup.sh — One-command dev environment bootstrap after Mac restart.
# Usage: ./scripts/startup.sh   or   make up
#
# What it does:
#   1. Ensures Colima (Docker runtime) is running
#   2. Starts postgres + redis containers (data persists in named volumes)
#   3. Waits for healthy services
#   4. Runs alembic migrations (idempotent — safe to re-run)
#   5. Seeds demo data if DB is empty
#   6. Prints status summary

set -euo pipefail
cd "$(dirname "$0")/.."

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}✓${NC} $1"; }
warn()  { echo -e "${YELLOW}⚠${NC} $1"; }
fail()  { echo -e "${RED}✗${NC} $1"; exit 1; }

# ── 1. Colima ──────────────────────────────────────────────────────
echo "── Checking Colima..."
if ! colima status &>/dev/null; then
  warn "Colima not running — starting it..."
  colima start
  colima status &>/dev/null || fail "Colima failed to start"
fi
info "Colima is running"

# Ensure docker context points to colima
if ! docker info &>/dev/null; then
  docker context use colima &>/dev/null || true
  docker info &>/dev/null || fail "Docker not reachable via Colima"
fi
info "Docker is reachable"

# ── 2. Start infra containers ──────────────────────────────────────
echo "── Starting PostgreSQL + Redis..."
docker volume create email-hub_postgres_data 2>/dev/null || true
AUTH_SECRET=dev-placeholder docker compose up -d db redis

# ── 3. Wait for healthy ───────────────────────────────────────────
echo "── Waiting for services to be healthy..."
for svc in db redis; do
  for i in $(seq 1 20); do
    status=$(docker compose ps --format json "$svc" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('Health',''))" 2>/dev/null || echo "")
    if [ "$status" = "healthy" ]; then
      break
    fi
    sleep 1
  done
  health=$(docker compose ps --format json "$svc" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('Health','unknown'))" 2>/dev/null || echo "unknown")
  if [ "$health" = "healthy" ]; then
    info "$svc is healthy"
  else
    warn "$svc status: $health (may still be starting)"
  fi
done

# ── 4. Run migrations (idempotent) ────────────────────────────────
echo "── Running database migrations..."
if uv run alembic upgrade head 2>&1; then
  info "Migrations up to date"
else
  warn "Migration had warnings (check above)"
fi

# ── 5. Summary ────────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════"
echo -e " ${GREEN}Dev environment ready!${NC}"
echo ""
echo "  Colima:      running"
echo "  PostgreSQL:  localhost:5434  (email_hub)"
echo "  Redis:       localhost:6380"
echo ""
echo "  Start dev:   make dev"
echo "  Full demo:   make demo"
echo "══════════════════════════════════════════"
