#!/usr/bin/env bash
# Verify every var marked required (${VAR:?...}) in docker-compose.yml is
# documented in .env.example. Exit non-zero if any are missing so devs can
# catch undocumented credentials before they hit CI or prod.
set -euo pipefail

cd "$(dirname "$0")/.."

required=$(grep -oE '\$\{[A-Z_][A-Z0-9_]*:\?' docker-compose.yml | tr -d '${:?' | sort -u)
documented=$(grep -oE '^[A-Z_][A-Z0-9_]*=' .env.example | tr -d '=' | sort -u)
missing=$(comm -23 <(echo "$required") <(echo "$documented"))

if [ -n "$missing" ]; then
  echo "Missing from .env.example:" >&2
  echo "$missing" >&2
  exit 1
fi

echo "All required docker-compose vars are documented in .env.example."
