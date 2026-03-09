#!/usr/bin/env bash
# Restore agent context after compaction.
# Called as a SessionStart hook with matcher "compact".
#
# Reads from .claude/state/agent-context.json if it exists and outputs
# critical context that should be re-injected into the conversation.

set -euo pipefail

STATE_FILE=".claude/state/agent-context.json"

# If no state file exists, provide minimal context
if [[ ! -f "$STATE_FILE" ]]; then
  echo "No agent context state file found at $STATE_FILE."
  echo "If you were working with an agent, the context may have been lost during compaction."
  echo ""
  echo "To restore context manually:"
  echo "  - Check TODO.md for current task status"
  echo "  - Check traces/ for recent eval results"
  echo "  - Check git log for recent changes"
  exit 0
fi

# Validate JSON
if ! jq empty "$STATE_FILE" 2>/dev/null; then
  echo "Warning: $STATE_FILE contains invalid JSON. Skipping context restoration."
  exit 0
fi

echo "=== Agent Context Restored ==="
echo ""

# Extract and display active agent
ACTIVE_AGENT=$(jq -r '.active_agent // "none"' "$STATE_FILE")
echo "Active agent: $ACTIVE_AGENT"

# Extract blueprint run state
BLUEPRINT_STATE=$(jq -r '.blueprint_state // "none"' "$STATE_FILE")
if [[ "$BLUEPRINT_STATE" != "none" ]]; then
  echo "Blueprint state: $BLUEPRINT_STATE"
fi

# Extract current node
CURRENT_NODE=$(jq -r '.current_node // empty' "$STATE_FILE")
if [[ -n "$CURRENT_NODE" ]]; then
  echo "Current node: $CURRENT_NODE"
fi

# Extract QA failures
QA_FAILURES=$(jq -r '.qa_failures // [] | length' "$STATE_FILE")
if [[ "$QA_FAILURES" -gt 0 ]]; then
  echo ""
  echo "QA Failures ($QA_FAILURES):"
  jq -r '.qa_failures[] | "  - \(.check): \(.message)"' "$STATE_FILE" 2>/dev/null
fi

# Extract loaded skill files
SKILLS=$(jq -r '.loaded_skills // [] | .[]' "$STATE_FILE" 2>/dev/null)
if [[ -n "$SKILLS" ]]; then
  echo ""
  echo "Loaded skill files:"
  echo "$SKILLS" | while read -r skill; do
    echo "  - $skill"
  done
fi

# Extract confidence score
CONFIDENCE=$(jq -r '.last_confidence // empty' "$STATE_FILE")
if [[ -n "$CONFIDENCE" ]]; then
  echo "Last confidence: $CONFIDENCE"
fi

# Extract any custom notes
NOTES=$(jq -r '.notes // empty' "$STATE_FILE")
if [[ -n "$NOTES" ]]; then
  echo ""
  echo "Notes: $NOTES"
fi

echo ""
echo "=== End Context ==="
exit 0
