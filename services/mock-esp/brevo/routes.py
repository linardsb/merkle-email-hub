"""Brevo SMTP Templates API mock routes."""

from datetime import UTC, datetime

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/brevo", tags=["Brevo"])

_templates: dict[str, dict] = {}
_next_id = 1


def _require_auth(api_key: str = Header(..., alias="api-key")) -> str:
    if not api_key.strip():
        raise HTTPException(status_code=401, detail="Empty API key")
    return api_key


class BrevoTemplateCreate(BaseModel):
    templateName: str = Field(..., min_length=1)
    htmlContent: str = ""
    subject: str = ""
    sender: dict | None = None


class BrevoTemplateUpdate(BaseModel):
    templateName: str | None = None
    htmlContent: str | None = None
    subject: str | None = None


@router.post("/smtp/templates", status_code=201)
async def create_template(
    body: BrevoTemplateCreate,
    api_key: str = Header(..., alias="api-key"),
) -> dict:
    _require_auth(api_key)
    global _next_id
    tid = str(_next_id)
    _next_id += 1
    now = datetime.now(UTC).isoformat()
    _templates[tid] = {
        "id": int(tid),
        "name": body.templateName,
        "htmlContent": body.htmlContent,
        "subject": body.subject,
        "createdAt": now,
        "modifiedAt": now,
    }
    return {"id": int(tid)}


@router.get("/smtp/templates")
async def list_templates(api_key: str = Header(..., alias="api-key")) -> dict:
    _require_auth(api_key)
    return {"templates": list(_templates.values()), "count": len(_templates)}


@router.get("/smtp/templates/{template_id}")
async def get_template(
    template_id: str,
    api_key: str = Header(..., alias="api-key"),
) -> dict:
    _require_auth(api_key)
    tpl = _templates.get(template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    return tpl


@router.put("/smtp/templates/{template_id}", status_code=204)
async def update_template(
    template_id: str,
    body: BrevoTemplateUpdate,
    api_key: str = Header(..., alias="api-key"),
) -> None:
    _require_auth(api_key)
    tpl = _templates.get(template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    if body.templateName is not None:
        tpl["name"] = body.templateName
    if body.htmlContent is not None:
        tpl["htmlContent"] = body.htmlContent
    if body.subject is not None:
        tpl["subject"] = body.subject
    tpl["modifiedAt"] = datetime.now(UTC).isoformat()


@router.delete("/smtp/templates/{template_id}", status_code=204)
async def delete_template(
    template_id: str,
    api_key: str = Header(..., alias="api-key"),
) -> None:
    _require_auth(api_key)
    if template_id not in _templates:
        raise HTTPException(status_code=404, detail="Template not found")
    del _templates[template_id]
