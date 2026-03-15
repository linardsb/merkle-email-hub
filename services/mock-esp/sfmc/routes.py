"""SFMC Content Builder Asset API routes."""

import uuid
from datetime import UTC, datetime

from auth import issue_token, require_sfmc_auth
from database import DatabaseManager
from fastapi import APIRouter, Depends, HTTPException

from sfmc.schemas import (
    AssetCreate,
    AssetListResponse,
    AssetResponse,
    AssetUpdate,
    TokenRequest,
    TokenResponse,
)

router = APIRouter(prefix="/sfmc", tags=["SFMC"])


def _get_db() -> DatabaseManager:
    from main import db

    return db


@router.post("/v2/token", response_model=TokenResponse)
async def token_exchange(body: TokenRequest) -> TokenResponse:
    if body.grant_type != "client_credentials":
        raise HTTPException(status_code=400, detail={"message": "Unsupported grant_type"})
    if not body.client_id or not body.client_secret:
        raise HTTPException(
            status_code=400, detail={"message": "Missing client_id or client_secret"}
        )
    access_token = issue_token(body.client_id)
    return TokenResponse(access_token=access_token)


@router.get(
    "/asset/v1/content/assets",
    response_model=AssetListResponse,
    dependencies=[Depends(require_sfmc_auth)],
)
async def list_assets() -> AssetListResponse:
    db = _get_db()
    rows = await db.fetchall("SELECT * FROM sfmc_assets ORDER BY created_at DESC")
    items = [
        AssetResponse(
            id=r["id"],
            name=r["name"],
            content=r["content"],
            category_id=r["category_id"],
            customer_key=r["customer_key"],
            created_at=r["created_at"],
            updated_at=r["updated_at"],
        )
        for r in rows
    ]
    return AssetListResponse(count=len(items), items=items)


@router.get(
    "/asset/v1/content/assets/{asset_id}",
    response_model=AssetResponse,
    dependencies=[Depends(require_sfmc_auth)],
)
async def get_asset(asset_id: str) -> AssetResponse:
    db = _get_db()
    row = await db.fetchone("SELECT * FROM sfmc_assets WHERE id = ?", (asset_id,))
    if not row:
        raise HTTPException(status_code=404, detail={"message": "Asset not found"})
    return AssetResponse(
        id=row["id"],
        name=row["name"],
        content=row["content"],
        category_id=row["category_id"],
        customer_key=row["customer_key"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.post(
    "/asset/v1/content/assets",
    response_model=AssetResponse,
    status_code=201,
    dependencies=[Depends(require_sfmc_auth)],
)
async def create_asset(body: AssetCreate) -> AssetResponse:
    db = _get_db()
    asset_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()
    customer_key = body.customer_key or str(uuid.uuid4())

    await db.execute(
        "INSERT INTO sfmc_assets (id, name, content, category_id, customer_key, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (asset_id, body.name, body.content, body.category_id, customer_key, now, now),
    )
    await db.commit()

    return AssetResponse(
        id=asset_id,
        name=body.name,
        content=body.content,
        category_id=body.category_id,
        customer_key=customer_key,
        created_at=now,
        updated_at=now,
    )


@router.patch(
    "/asset/v1/content/assets/{asset_id}",
    response_model=AssetResponse,
    dependencies=[Depends(require_sfmc_auth)],
)
async def update_asset(asset_id: str, body: AssetUpdate) -> AssetResponse:
    db = _get_db()
    row = await db.fetchone("SELECT * FROM sfmc_assets WHERE id = ?", (asset_id,))
    if not row:
        raise HTTPException(status_code=404, detail={"message": "Asset not found"})

    now = datetime.now(UTC).isoformat()
    name = body.name if body.name is not None else row["name"]
    content = body.content if body.content is not None else row["content"]
    category_id = body.category_id if body.category_id is not None else row["category_id"]

    await db.execute(
        "UPDATE sfmc_assets SET name = ?, content = ?, category_id = ?, updated_at = ? WHERE id = ?",
        (name, content, category_id, now, asset_id),
    )
    await db.commit()

    return AssetResponse(
        id=asset_id,
        name=name,
        content=content,
        category_id=category_id,
        customer_key=row["customer_key"],
        created_at=row["created_at"],
        updated_at=now,
    )


@router.delete("/asset/v1/content/assets/{asset_id}", dependencies=[Depends(require_sfmc_auth)])
async def delete_asset(asset_id: str) -> dict:
    db = _get_db()
    row = await db.fetchone("SELECT id FROM sfmc_assets WHERE id = ?", (asset_id,))
    if not row:
        raise HTTPException(status_code=404, detail={"message": "Asset not found"})
    await db.execute("DELETE FROM sfmc_assets WHERE id = ?", (asset_id,))
    await db.commit()
    return {"message": "success"}
