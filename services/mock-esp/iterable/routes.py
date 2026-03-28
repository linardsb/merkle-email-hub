"""Iterable Templates API mock routes."""

from datetime import UTC, datetime

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/iterable", tags=["Iterable"])

_templates: dict[str, dict] = {}
_next_id = 1


def _require_auth(api_key: str = Header(..., alias="Api-Key")) -> str:
    if not api_key.strip():
        raise HTTPException(status_code=401, detail="Empty API key")
    return api_key


class IterableTemplateCreate(BaseModel):
    name: str = Field(..., min_length=1)
    html: str = ""
    templateType: str = "Email"


@router.post("/templates/email/upsert")
async def upsert_template(
    body: IterableTemplateCreate,
    api_key: str = Header(..., alias="Api-Key"),
) -> dict:
    _require_auth(api_key)
    global _next_id
    tid = str(_next_id)
    _next_id += 1
    now = datetime.now(UTC).isoformat()
    _templates[tid] = {
        "templateId": int(tid),
        "name": body.name,
        "html": body.html,
        "templateType": body.templateType,
        "createdAt": now,
        "updatedAt": now,
    }
    return {"msg": "success", "code": "Success", "params": {"templateId": int(tid)}}


@router.get("/templates")
async def list_templates(api_key: str = Header(..., alias="Api-Key")) -> dict:
    _require_auth(api_key)
    return {"templates": list(_templates.values())}


@router.get("/templates/email/get")
async def get_template(
    templateId: int,
    api_key: str = Header(..., alias="Api-Key"),
) -> dict:
    _require_auth(api_key)
    tid = str(templateId)
    tpl = _templates.get(tid)
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"template": tpl}
