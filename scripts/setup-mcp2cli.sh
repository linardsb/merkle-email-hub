#!/usr/bin/env bash
# Setup mcp2cli baked configuration for the Email Hub API.
# Prerequisites: uv installed, backend running on port 8891.
set -euo pipefail

PORT="${EMAILHUB_PORT:-8891}"
BASE_URL="http://localhost:${PORT}"
SPEC_URL="${BASE_URL}/openapi.json"
BAKE_NAME="emailhub"

# --check: exit 0 if already baked, exit 1 if not
if [[ "${1:-}" == "--check" ]]; then
  mcp2cli bake show "${BAKE_NAME}" &>/dev/null && exit 0 || exit 1
fi

# Check if mcp2cli is available
if ! command -v mcp2cli &>/dev/null && ! uvx mcp2cli --version &>/dev/null 2>&1; then
  echo "Installing mcp2cli..."
  uv tool install mcp2cli
fi

# Check if backend is reachable
if ! curl -sf "${BASE_URL}/health" >/dev/null 2>&1; then
  echo "Backend not reachable at ${BASE_URL}"
  echo "  Start it first: make dev-be"
  echo ""
  echo "  Baking config anyway (spec URL will be fetched at call time)..."
fi

# Remove existing bake if present
mcp2cli bake remove "${BAKE_NAME}" 2>/dev/null || true

# Bake the config
echo "Baking mcp2cli config as '${BAKE_NAME}'..."
mcp2cli bake create "${BAKE_NAME}" \
  --spec "${SPEC_URL}" \
  --exclude "openapi-json"

echo ""
echo "Done! Usage:"
echo "  mcp2cli @${BAKE_NAME} --list          # list all endpoints"
echo "  mcp2cli @${BAKE_NAME} --search proj   # search for project endpoints"
echo "  mcp2cli @${BAKE_NAME} health          # call the health endpoint"
echo ""
echo "Or use Makefile targets:"
echo "  make cli-list                          # list all CLI commands"
echo "  make cli-search s=project              # search endpoints"
