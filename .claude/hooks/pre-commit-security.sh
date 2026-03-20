#!/usr/bin/env bash
# Pre-commit security check — scans staged files for secrets before allowing git commit.
# Called as a PreToolUse hook on Bash — receives tool input via stdin.
#
# Exit codes:
#   0 — allow (not a commit command, or no secrets found)
#   2 — block (secrets detected in staged files)

set -euo pipefail

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)

if [[ -z "$COMMAND" ]]; then
  exit 0
fi

# Only intercept git commit commands
if ! echo "$COMMAND" | grep -qE 'git\s+commit'; then
  exit 0
fi

# Get list of staged files
STAGED_FILES=$(git diff --cached --name-only 2>/dev/null || true)

if [[ -z "$STAGED_FILES" ]]; then
  exit 0
fi

FOUND_SECRETS=0

# Check for .env files being committed (allow .env.example — it's a template)
if echo "$STAGED_FILES" | grep -E '\.env($|\.)' | grep -vq '\.env\.example$'; then
  echo "BLOCKED: Staged .env file detected — never commit environment files." >&2
  FOUND_SECRETS=1
fi

# Check for common credential files
if echo "$STAGED_FILES" | grep -qiE '(credentials|secrets|private.key|\.pem|\.p12|\.pfx|id_rsa|id_ed25519)'; then
  echo "BLOCKED: Staged file looks like a credential/key file." >&2
  FOUND_SECRETS=1
fi

# Scan staged file contents for secret patterns
PATTERNS=(
  'AKIA[0-9A-Z]{16}'                          # AWS Access Key
  'sk-[a-zA-Z0-9]{20,}'                       # OpenAI / Stripe secret key
  'sk-ant-[a-zA-Z0-9-]{20,}'                  # Anthropic API key
  'ghp_[a-zA-Z0-9]{36}'                       # GitHub personal access token
  'gho_[a-zA-Z0-9]{36}'                       # GitHub OAuth token
  'github_pat_[a-zA-Z0-9_]{22,}'              # GitHub fine-grained PAT
  'xox[bposa]-[a-zA-Z0-9-]+'                  # Slack tokens
  'hooks\.slack\.com/services/T[A-Z0-9]+/'    # Slack webhook
  'sq0atp-[a-zA-Z0-9_-]{22}'                  # Square access token
  'AIza[0-9A-Za-z_-]{35}'                     # Google API key
  'ya29\.[0-9A-Za-z_-]+'                      # Google OAuth token
  'eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.'   # JWT tokens (long ones)
  '-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----' # Private keys
  'password\s*[:=]\s*["\x27][^"\x27]{8,}'     # Hardcoded passwords
  'api[_-]?key\s*[:=]\s*["\x27][a-zA-Z0-9]{16,}' # Generic API keys
  'secret[_-]?key\s*[:=]\s*["\x27][a-zA-Z0-9]{16,}' # Generic secret keys
)

# Build a combined regex for efficiency
COMBINED_PATTERN=$(IFS='|'; echo "${PATTERNS[*]}")

# Scan staged content (not working tree) for secrets
MATCHES=$(git diff --cached -U0 --diff-filter=ACM 2>/dev/null | grep -E "^\+" | grep -v "^+++" | grep -oE "$COMBINED_PATTERN" 2>/dev/null || true)

if [[ -n "$MATCHES" ]]; then
  echo "BLOCKED: Potential secrets detected in staged changes:" >&2
  echo "$MATCHES" | head -5 | while read -r match; do
    # Truncate the match to avoid leaking the full secret
    TRUNCATED="${match:0:20}..."
    echo "  → $TRUNCATED" >&2
  done
  FOUND_SECRETS=1
fi

if [[ "$FOUND_SECRETS" -eq 1 ]]; then
  echo "" >&2
  echo "Remove secrets from staged files before committing." >&2
  exit 2
fi

exit 0
