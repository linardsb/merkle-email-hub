"""Braze Content Blocks API routes."""

import json
import uuid
from datetime import UTC, datetime

from auth import require_braze_auth
from database import DatabaseManager
from fastapi import APIRouter, Depends, HTTPException, Query

from braze.schemas import (
    ContentBlockCreate,
    ContentBlockListResponse,
    ContentBlockResponse,
    ContentBlockSummary,
    ContentBlockUpdate,
)

router = APIRouter(prefix="/braze", tags=["Braze"])


def _get_db() -> DatabaseManager:
    from main import db

    return db


@router.post(
    "/content_blocks/create",
    response_model=ContentBlockResponse,
    dependencies=[Depends(require_braze_auth)],
)
async def create_content_block(body: ContentBlockCreate) -> ContentBlockResponse:
    db = _get_db()
    block_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()
    tags_json = json.dumps(body.tags)

    await db.execute(
        "INSERT INTO braze_content_blocks (id, name, content, tags, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        (block_id, body.name, body.content, tags_json, now, now),
    )
    await db.commit()

    return ContentBlockResponse(
        content_block_id=block_id,
        name=body.name,
        content=body.content,
        tags=body.tags,
        created_at=now,
        updated_at=now,
    )


@router.get(
    "/content_blocks/list",
    response_model=ContentBlockListResponse,
    dependencies=[Depends(require_braze_auth)],
)
async def list_content_blocks() -> ContentBlockListResponse:
    db = _get_db()
    rows = await db.fetchall("SELECT * FROM braze_content_blocks ORDER BY created_at DESC")
    blocks = [
        ContentBlockSummary(
            content_block_id=r["id"],
            name=r["name"],
            tags=json.loads(r["tags"]),
            created_at=r["created_at"],
            updated_at=r["updated_at"],
        )
        for r in rows
    ]
    return ContentBlockListResponse(content_blocks=blocks, count=len(blocks))


@router.get(
    "/content_blocks/info",
    response_model=ContentBlockResponse,
    dependencies=[Depends(require_braze_auth)],
)
async def get_content_block(content_block_id: str = Query(...)) -> ContentBlockResponse:
    db = _get_db()
    row = await db.fetchone("SELECT * FROM braze_content_blocks WHERE id = ?", (content_block_id,))
    if not row:
        raise HTTPException(status_code=404, detail={"message": "Content block not found"})
    return ContentBlockResponse(
        content_block_id=row["id"],
        name=row["name"],
        content=row["content"],
        tags=json.loads(row["tags"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.post(
    "/content_blocks/update",
    response_model=ContentBlockResponse,
    dependencies=[Depends(require_braze_auth)],
)
async def update_content_block(body: ContentBlockUpdate) -> ContentBlockResponse:
    db = _get_db()
    row = await db.fetchone(
        "SELECT * FROM braze_content_blocks WHERE id = ?", (body.content_block_id,)
    )
    if not row:
        raise HTTPException(status_code=404, detail={"message": "Content block not found"})

    now = datetime.now(UTC).isoformat()
    tags = json.dumps(body.tags) if body.tags is not None else row["tags"]

    await db.execute(
        "UPDATE braze_content_blocks SET content = ?, tags = ?, updated_at = ? WHERE id = ?",
        (body.content, tags, now, body.content_block_id),
    )
    await db.commit()

    return ContentBlockResponse(
        content_block_id=row["id"],
        name=row["name"],
        content=body.content,
        tags=json.loads(tags) if isinstance(tags, str) else tags,
        created_at=row["created_at"],
        updated_at=now,
    )


@router.delete("/content_blocks/{block_id}", dependencies=[Depends(require_braze_auth)])
async def delete_content_block(block_id: str) -> dict:
    db = _get_db()
    row = await db.fetchone("SELECT id FROM braze_content_blocks WHERE id = ?", (block_id,))
    if not row:
        raise HTTPException(status_code=404, detail={"message": "Content block not found"})
    await db.execute("DELETE FROM braze_content_blocks WHERE id = ?", (block_id,))
    await db.commit()
    return {"message": "success"}
