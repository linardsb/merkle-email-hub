"""Mailchimp Templates API mock routes."""

from datetime import UTC, datetime

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/mailchimp", tags=["Mailchimp"])

# In-memory store
_templates: dict[str, dict] = {}
_next_id = 1


def _require_auth(authorization: str = Header(...)) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization")
    token = authorization[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Empty bearer token")
    return token


class MailchimpTemplateCreate(BaseModel):
    name: str = Field(..., min_length=1)
    html: str = ""


class MailchimpTemplateUpdate(BaseModel):
    name: str | None = None
    html: str | None = None


@router.post("/templates")
async def create_template(
    body: MailchimpTemplateCreate,
    authorization: str = Header(...),
) -> dict:
    _require_auth(authorization)
    global _next_id
    tid = str(_next_id)
    _next_id += 1
    now = datetime.now(UTC).isoformat()
    _templates[tid] = {
        "id": tid,
        "name": body.name,
        "html": body.html,
        "date_created": now,
        "date_edited": now,
    }
    return _templates[tid]


@router.get("/templates")
async def list_templates(authorization: str = Header(...)) -> dict:
    _require_auth(authorization)
    items = list(_templates.values())
    return {"templates": items, "total_items": len(items)}


@router.get("/templates/{template_id}")
async def get_template(template_id: str, authorization: str = Header(...)) -> dict:
    _require_auth(authorization)
    tpl = _templates.get(template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    return tpl


@router.patch("/templates/{template_id}")
async def update_template(
    template_id: str,
    body: MailchimpTemplateUpdate,
    authorization: str = Header(...),
) -> dict:
    _require_auth(authorization)
    tpl = _templates.get(template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    if body.name is not None:
        tpl["name"] = body.name
    if body.html is not None:
        tpl["html"] = body.html
    tpl["date_edited"] = datetime.now(UTC).isoformat()
    return tpl


@router.delete("/templates/{template_id}")
async def delete_template(template_id: str, authorization: str = Header(...)) -> dict:
    _require_auth(authorization)
    if template_id not in _templates:
        raise HTTPException(status_code=404, detail="Template not found")
    del _templates[template_id]
    return {"message": "deleted"}
