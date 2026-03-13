#!/usr/bin/env bash
# Block dangerous commands that could cause irreversible damage.
# Called as a PreToolUse hook on Bash — receives tool input via stdin.
#
# Exit codes:
#   0 — allow the command
#   2 — block the command (hard block, cannot be overridden)

set -euo pipefail

# Read the tool input JSON from stdin
INPUT=$(cat)

# Extract the command from the JSON input
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)

if [[ -z "$COMMAND" ]]; then
  exit 0
fi

# --- Force push protection ---
# Allow --force-with-lease (safe) but block bare --force and -f
if echo "$COMMAND" | grep -qE 'git\s+push\s+.*--force-with-lease'; then
  : # safe — allow --force-with-lease
elif echo "$COMMAND" | grep -qE 'git\s+push\s+.*--force|git\s+push\s+-f\b'; then
  echo "BLOCKED: Force push is not allowed. Use --force-with-lease if you must." >&2
  exit 2
fi

# --- Git destructive operations ---
if echo "$COMMAND" | grep -qE 'git\s+reset\s+--hard'; then
  echo "BLOCKED: git reset --hard discards uncommitted work. Stash or commit first." >&2
  exit 2
fi

if echo "$COMMAND" | grep -qE 'git\s+clean\s+-[a-zA-Z]*f'; then
  echo "BLOCKED: git clean -f permanently deletes untracked files." >&2
  exit 2
fi

if echo "$COMMAND" | grep -qE 'git\s+checkout\s+--\s+\.'; then
  echo "BLOCKED: git checkout -- . discards all unstaged changes." >&2
  exit 2
fi

# --- rm -rf on protected paths ---
PROTECTED_PATHS=(
  "alembic/"
  "alembic"
  ".env"
  "traces/baseline.json"
  "app/"
  "cms/"
  "services/"
  ".claude/"
  "pyproject.toml"
  "package.json"
)

if echo "$COMMAND" | grep -qE 'rm\s+-[a-zA-Z]*r[a-zA-Z]*f|rm\s+-[a-zA-Z]*f[a-zA-Z]*r'; then
  for path in "${PROTECTED_PATHS[@]}"; do
    if echo "$COMMAND" | grep -qF "$path"; then
      echo "BLOCKED: rm -rf on protected path '$path' is not allowed." >&2
      exit 2
    fi
  done
fi

# --- Broad rm -rf (root-level or wildcard) ---
if echo "$COMMAND" | grep -qE 'rm\s+-rf\s+(/|\.|\*|\.\.)'; then
  echo "BLOCKED: rm -rf on root/current/parent directory or wildcard is not allowed." >&2
  exit 2
fi

# --- Drop database ---
if echo "$COMMAND" | grep -qiE 'drop\s+(database|table|schema)'; then
  echo "BLOCKED: DROP DATABASE/TABLE/SCHEMA requires manual confirmation." >&2
  exit 2
fi

# --- .env file deletion ---
if echo "$COMMAND" | grep -qE 'rm\s+.*\.env'; then
  echo "BLOCKED: Deleting .env files is not allowed." >&2
  exit 2
fi

# Command is safe
exit 0
