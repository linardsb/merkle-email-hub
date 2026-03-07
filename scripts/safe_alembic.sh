#!/usr/bin/env bash
# Safe Alembic wrapper that blocks accidental downgrades.
# Usage: ./scripts/safe_alembic.sh <alembic args...>
#
# Allows: upgrade, current, history, heads, branches, show, stamp
# Blocks: downgrade (unless --i-know-what-i-am-doing is passed)

set -euo pipefail

FORCE_FLAG="--i-know-what-i-am-doing"

# Check if any argument is "downgrade"
for arg in "$@"; do
    if [ "$arg" = "downgrade" ]; then
        # Check for force flag
        for flag in "$@"; do
            if [ "$flag" = "$FORCE_FLAG" ]; then
                echo "WARNING: Running Alembic downgrade with force flag."
                echo "Creating pre-downgrade backup..."
                if [ -f "scripts/backup_db.sh" ]; then
                    bash scripts/backup_db.sh ./backups/pre-downgrade
                fi
                # Remove the force flag and pass remaining args to alembic
                ARGS=()
                for a in "$@"; do
                    if [ "$a" != "$FORCE_FLAG" ]; then
                        ARGS+=("$a")
                    fi
                done
                exec alembic "${ARGS[@]}"
            fi
        done

        echo "ERROR: 'alembic downgrade' is blocked by safe_alembic.sh"
        echo ""
        echo "Downgrades can DROP TABLES and permanently destroy data."
        echo "If you really need to downgrade, use:"
        echo ""
        echo "  ./scripts/safe_alembic.sh downgrade <revision> $FORCE_FLAG"
        echo ""
        echo "A backup will be created automatically before the downgrade runs."
        exit 1
    fi
done

# Safe commands pass through directly
exec alembic "$@"
