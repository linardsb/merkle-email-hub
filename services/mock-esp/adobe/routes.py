"""Adobe Campaign Standard API routes."""

import uuid
from datetime import UTC, datetime

from auth import get_token_ttl, issue_token, require_adobe_auth
from database import DatabaseManager
from fastapi import APIRouter, Depends, Form, HTTPException, Query

from adobe.schemas import (
    DeliveryCreate,
    DeliveryListResponse,
    DeliveryResponse,
    DeliveryUpdate,
    TokenResponse,
)

router = APIRouter(prefix="/adobe", tags=["Adobe Campaign"])


def _get_db() -> DatabaseManager:
    from main import db

    return db


@router.post("/ims/token/v3", response_model=TokenResponse)
async def ims_token_exchange(
    client_id: str = Form(...),
    client_secret: str = Form(...),  # noqa: ARG001
    grant_type: str = Form(default="client_credentials"),
) -> TokenResponse:
    if grant_type != "client_credentials":
        raise HTTPException(status_code=400, detail={"message": "Unsupported grant_type"})
    access_token = issue_token(client_id)
    return TokenResponse(access_token=access_token, expires_in=get_token_ttl())


@router.get(
    "/profileAndServicesExt/delivery",
    response_model=DeliveryListResponse,
    dependencies=[Depends(require_adobe_auth)],
)
async def list_deliveries(
    line_start: int = Query(0, alias="_lineStart", ge=0),
    line_count: int = Query(10, alias="_lineCount", ge=1, le=100),
) -> DeliveryListResponse:
    db = _get_db()
    count_row = await db.fetchone("SELECT COUNT(*) as total FROM adobe_deliveries")
    total = count_row["total"] if count_row else 0
    rows = await db.fetchall(
        "SELECT * FROM adobe_deliveries ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (line_count, line_start),
    )
    items = [
        DeliveryResponse(
            PKey=r["id"],
            name=r["name"],
            content=r["content"],
            label=r["label"],
            folder_id=r["folder_id"],
            created_at=r["created_at"],
            updated_at=r["updated_at"],
        )
        for r in rows
    ]
    next_start = line_start + line_count
    next_hint = {"_lineStart": next_start, "_lineCount": line_count} if next_start < total else None
    return DeliveryListResponse(count=total, content=items, next=next_hint)


@router.get(
    "/profileAndServicesExt/delivery/{pkey}",
    response_model=DeliveryResponse,
    dependencies=[Depends(require_adobe_auth)],
)
async def get_delivery(pkey: str) -> DeliveryResponse:
    db = _get_db()
    row = await db.fetchone("SELECT * FROM adobe_deliveries WHERE id = ?", (pkey,))
    if not row:
        raise HTTPException(status_code=404, detail={"message": "Delivery not found"})
    return DeliveryResponse(
        PKey=row["id"],
        name=row["name"],
        content=row["content"],
        label=row["label"],
        folder_id=row["folder_id"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.post(
    "/profileAndServicesExt/delivery",
    response_model=DeliveryResponse,
    status_code=201,
    dependencies=[Depends(require_adobe_auth)],
)
async def create_delivery(body: DeliveryCreate) -> DeliveryResponse:
    db = _get_db()
    existing = await db.fetchone("SELECT id FROM adobe_deliveries WHERE name = ?", (body.name,))
    if existing:
        from fastapi.responses import JSONResponse

        return JSONResponse(  # type: ignore[return-value]
            status_code=409,
            content={
                "error_code": "DUP-100",
                "title": "Duplicate delivery",
                "detail": f"A delivery with name '{body.name}' already exists",
            },
        )
    delivery_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()

    await db.execute(
        "INSERT INTO adobe_deliveries (id, name, content, label, folder_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (delivery_id, body.name, body.content, body.label, body.folder_id, now, now),
    )
    await db.commit()

    return DeliveryResponse(
        PKey=delivery_id,
        name=body.name,
        content=body.content,
        label=body.label,
        folder_id=body.folder_id,
        created_at=now,
        updated_at=now,
    )


@router.patch(
    "/profileAndServicesExt/delivery/{pkey}",
    response_model=DeliveryResponse,
    dependencies=[Depends(require_adobe_auth)],
)
async def update_delivery(pkey: str, body: DeliveryUpdate) -> DeliveryResponse:
    db = _get_db()
    row = await db.fetchone("SELECT * FROM adobe_deliveries WHERE id = ?", (pkey,))
    if not row:
        raise HTTPException(status_code=404, detail={"message": "Delivery not found"})

    now = datetime.now(UTC).isoformat()
    name = body.name if body.name is not None else row["name"]
    content = body.content if body.content is not None else row["content"]
    label = body.label if body.label is not None else row["label"]

    await db.execute(
        "UPDATE adobe_deliveries SET name = ?, content = ?, label = ?, updated_at = ? WHERE id = ?",
        (name, content, label, now, pkey),
    )
    await db.commit()

    return DeliveryResponse(
        PKey=pkey,
        name=name,
        content=content,
        label=label,
        folder_id=row["folder_id"],
        created_at=row["created_at"],
        updated_at=now,
    )


@router.delete(
    "/profileAndServicesExt/delivery/{pkey}",
    dependencies=[Depends(require_adobe_auth)],
)
async def delete_delivery(pkey: str) -> dict:
    db = _get_db()
    row = await db.fetchone("SELECT id FROM adobe_deliveries WHERE id = ?", (pkey,))
    if not row:
        raise HTTPException(status_code=404, detail={"message": "Delivery not found"})
    await db.execute("DELETE FROM adobe_deliveries WHERE id = ?", (pkey,))
    await db.commit()
    return {"message": "success"}
