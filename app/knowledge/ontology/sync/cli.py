"""CLI entrypoint for ontology sync — manual trigger for CanIEmail data refresh."""

from __future__ import annotations

import argparse
import asyncio
import sys

from app.core.logging import get_logger

logger = get_logger(__name__)


async def main(dry_run: bool = False) -> None:
    """Run the CanIEmail sync pipeline.

    Args:
        dry_run: If True, compute diff and report but do NOT write changes.
    """
    from app.knowledge.ontology.sync.service import CanIEmailSyncService

    service = CanIEmailSyncService()
    report = await service.sync(dry_run=dry_run)

    print(f"\n{'DRY RUN — ' if dry_run else ''}Sync Report:")
    print(f"  Commit SHA: {report.commit_sha or 'unknown'}")
    print(f"  New properties: {report.new_properties}")
    print(f"  Updated levels: {report.updated_levels}")
    print(f"  New clients: {report.new_clients}")
    print(f"  Changelog entries: {len(report.changelog)}")

    if report.errors:
        print(f"\n  Errors ({len(report.errors)}):")
        for err in report.errors:
            print(f"    - {err}")

    if report.changelog:
        print(f"\n  Changes ({len(report.changelog)}):")
        for entry in report.changelog[:20]:
            old = entry.old_level or "new"
            print(f"    {entry.property_id} @ {entry.client_id}: {old} -> {entry.new_level}")
        if len(report.changelog) > 20:
            print(f"    ... and {len(report.changelog) - 20} more")

    if report.errors:
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync ontology from Can I Email")
    parser.add_argument("--dry-run", action="store_true", help="Show diff without writing changes")
    args = parser.parse_args()
    asyncio.run(main(dry_run=args.dry_run))
