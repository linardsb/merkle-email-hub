"""Seed the knowledge base with email development content.

Usage:
    uv run python -m app.knowledge.seed          # Skip existing
    uv run python -m app.knowledge.seed --force   # Re-ingest all

Requires:
    - Database running (make db)
    - EMBEDDING configuration in environment
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

from app.core.database import get_db_context
from app.core.logging import get_logger
from app.knowledge.data.seed_manifest import SEED_MANIFEST, SeedEntry
from app.knowledge.schemas import DocumentTagRequest, DocumentUpload
from app.knowledge.service import KnowledgeService

SEED_DIR = Path(__file__).parent / "data" / "seeds"

logger = get_logger(__name__)


async def _get_existing_filenames(service: KnowledgeService) -> set[str]:
    """Collect all filenames already in the knowledge base."""
    filenames: set[str] = set()
    offset = 0
    batch_size = 100
    while True:
        docs = await service.repository.list_documents(offset=offset, limit=batch_size)
        if not docs:
            break
        for doc in docs:
            filenames.add(doc.filename)
        if len(docs) < batch_size:
            break
        offset += batch_size
    return filenames


async def _ensure_tags(service: KnowledgeService) -> dict[str, int]:
    """Pre-create all tags from the manifest and return name->id mapping."""
    all_tags: set[str] = set()
    for entry in SEED_MANIFEST:
        all_tags.update(entry.tags)

    tag_map: dict[str, int] = {}
    for tag_name in sorted(all_tags):
        tag = await service.repository.get_or_create_tag(tag_name)
        tag_map[tag_name] = tag.id
    return tag_map


async def _ingest_entry(
    service: KnowledgeService,
    entry: SeedEntry,
    tag_map: dict[str, int],
) -> int:
    """Ingest a single seed entry and tag it. Returns chunk count."""
    file_path = SEED_DIR / entry.filename

    upload = DocumentUpload(
        domain=entry.domain,
        title=entry.title,
        description=entry.description,
        metadata_json=None,
    )
    doc = await service.ingest_document(
        file_path=str(file_path),
        upload=upload,
        filename=file_path.name,
        source_type="text",
        file_size=file_path.stat().st_size,
    )

    # Tag the document
    tag_ids = [tag_map[t] for t in entry.tags]
    if tag_ids:
        await service.add_tags_to_document(doc.id, DocumentTagRequest(tag_ids=tag_ids))

    return doc.chunk_count


async def seed_knowledge_base(*, force: bool = False) -> None:
    """Seed the knowledge base with email development content.

    Args:
        force: If True, skip idempotency checks and re-ingest all documents.
    """
    start = time.monotonic()
    print(f"\n  Seeding knowledge base ({len(SEED_MANIFEST)} documents)...")
    print(f"  Source: {SEED_DIR}")
    print(f"  Force: {force}\n")

    async with get_db_context() as db:
        service = KnowledgeService(db)

        # Check existing documents for idempotency
        existing = await _get_existing_filenames(service) if not force else set[str]()

        # Pre-create tags
        tag_map = await _ensure_tags(service)
        print(f"  Tags ready: {len(tag_map)}\n")

        seeded = 0
        skipped = 0
        failed = 0
        total_chunks = 0

        for entry in SEED_MANIFEST:
            file_path = SEED_DIR / entry.filename

            # Validate file exists
            if not file_path.is_file():
                print(f"  MISS {entry.filename} (file not found)")
                failed += 1
                continue

            # Idempotency: skip if filename already exists
            if file_path.name in existing:
                print(f"  SKIP {entry.filename} (already seeded)")
                skipped += 1
                continue

            try:
                chunks = await _ingest_entry(service, entry, tag_map)
                total_chunks += chunks
                seeded += 1
                print(f"  OK   {entry.filename} -> {chunks} chunks")
            except Exception as e:
                failed += 1
                print(f"  FAIL {entry.filename}: {e}")
                logger.error(
                    "knowledge.seed.entry_failed",
                    filename=entry.filename,
                    error=str(e),
                    error_type=type(e).__name__,
                )

    duration = time.monotonic() - start
    print(f"\n  Done in {duration:.1f}s: {seeded} seeded, {skipped} skipped, {failed} failed")
    print(f"  Total chunks: {total_chunks}\n")

    if failed > 0:
        sys.exit(1)


def main() -> None:
    """CLI entry point."""
    force = "--force" in sys.argv
    asyncio.run(seed_knowledge_base(force=force))


if __name__ == "__main__":
    main()
