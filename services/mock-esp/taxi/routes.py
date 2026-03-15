"""Taxi for Email API routes."""

import uuid
from datetime import UTC, datetime

from auth import require_taxi_auth
from database import DatabaseManager
from fastapi import APIRouter, Depends, HTTPException

from taxi.schemas import (
    TemplateCreate,
    TemplateListResponse,
    TemplateResponse,
    TemplateUpdate,
)

router = APIRouter(prefix="/taxi", tags=["Taxi for Email"])


def _get_db() -> DatabaseManager:
    from main import db

    return db


@router.get(
    "/api/v1/templates",
    response_model=TemplateListResponse,
    dependencies=[Depends(require_taxi_auth)],
)
async def list_templates() -> TemplateListResponse:
    db = _get_db()
    rows = await db.fetchall("SELECT * FROM taxi_templates ORDER BY created_at DESC")
    items = [
        TemplateResponse(
            id=r["id"],
            name=r["name"],
            content=r["content"],
            syntax_version=r["syntax_version"],
            created_at=r["created_at"],
            updated_at=r["updated_at"],
        )
        for r in rows
    ]
    return TemplateListResponse(count=len(items), templates=items)


@router.get(
    "/api/v1/templates/{template_id}",
    response_model=TemplateResponse,
    dependencies=[Depends(require_taxi_auth)],
)
async def get_template(template_id: str) -> TemplateResponse:
    db = _get_db()
    row = await db.fetchone("SELECT * FROM taxi_templates WHERE id = ?", (template_id,))
    if not row:
        raise HTTPException(status_code=404, detail={"message": "Template not found"})
    return TemplateResponse(
        id=row["id"],
        name=row["name"],
        content=row["content"],
        syntax_version=row["syntax_version"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.post(
    "/api/v1/templates",
    response_model=TemplateResponse,
    status_code=201,
    dependencies=[Depends(require_taxi_auth)],
)
async def create_template(body: TemplateCreate) -> TemplateResponse:
    db = _get_db()
    template_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()

    await db.execute(
        "INSERT INTO taxi_templates (id, name, content, syntax_version, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        (template_id, body.name, body.content, body.syntax_version, now, now),
    )
    await db.commit()

    return TemplateResponse(
        id=template_id,
        name=body.name,
        content=body.content,
        syntax_version=body.syntax_version,
        created_at=now,
        updated_at=now,
    )


@router.put(
    "/api/v1/templates/{template_id}",
    response_model=TemplateResponse,
    dependencies=[Depends(require_taxi_auth)],
)
async def update_template(template_id: str, body: TemplateUpdate) -> TemplateResponse:
    db = _get_db()
    row = await db.fetchone("SELECT * FROM taxi_templates WHERE id = ?", (template_id,))
    if not row:
        raise HTTPException(status_code=404, detail={"message": "Template not found"})

    now = datetime.now(UTC).isoformat()
    name = body.name if body.name is not None else row["name"]
    content = body.content if body.content is not None else row["content"]
    syntax_version = (
        body.syntax_version if body.syntax_version is not None else row["syntax_version"]
    )

    await db.execute(
        "UPDATE taxi_templates SET name = ?, content = ?, syntax_version = ?, updated_at = ? WHERE id = ?",
        (name, content, syntax_version, now, template_id),
    )
    await db.commit()

    return TemplateResponse(
        id=template_id,
        name=name,
        content=content,
        syntax_version=syntax_version,
        created_at=row["created_at"],
        updated_at=now,
    )


@router.delete("/api/v1/templates/{template_id}", dependencies=[Depends(require_taxi_auth)])
async def delete_template(template_id: str) -> dict:
    db = _get_db()
    row = await db.fetchone("SELECT id FROM taxi_templates WHERE id = ?", (template_id,))
    if not row:
        raise HTTPException(status_code=404, detail={"message": "Template not found"})
    await db.execute("DELETE FROM taxi_templates WHERE id = ?", (template_id,))
    await db.commit()
    return {"message": "success"}
