"""SendGrid Templates API mock routes."""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/sendgrid", tags=["SendGrid"])

_templates: dict[str, dict] = {}
_versions: dict[str, list[dict]] = {}


def _require_auth(authorization: str = Header(...)) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization")
    token = authorization[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Empty bearer token")
    return token


class SGTemplateCreate(BaseModel):
    name: str = Field(..., min_length=1)
    generation: str = "dynamic"


class SGTemplateUpdate(BaseModel):
    name: str | None = None


class SGVersionCreate(BaseModel):
    name: str = "Untitled Version"
    html_content: str = ""
    subject: str = ""


@router.post("/templates")
async def create_template(
    body: SGTemplateCreate,
    authorization: str = Header(...),
) -> dict:
    _require_auth(authorization)
    tid = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()
    _templates[tid] = {
        "id": tid,
        "name": body.name,
        "generation": body.generation,
        "updated_at": now,
        "versions": [],
    }
    _versions[tid] = []
    return _templates[tid]


@router.get("/templates")
async def list_templates(authorization: str = Header(...)) -> dict:
    _require_auth(authorization)
    return {"result": list(_templates.values())}


@router.get("/templates/{template_id}")
async def get_template(template_id: str, authorization: str = Header(...)) -> dict:
    _require_auth(authorization)
    tpl = _templates.get(template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    tpl_copy = dict(tpl)
    tpl_copy["versions"] = _versions.get(template_id, [])
    return tpl_copy


@router.patch("/templates/{template_id}")
async def update_template(
    template_id: str,
    body: SGTemplateUpdate,
    authorization: str = Header(...),
) -> dict:
    _require_auth(authorization)
    tpl = _templates.get(template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    if body.name is not None:
        tpl["name"] = body.name
    tpl["updated_at"] = datetime.now(UTC).isoformat()
    return tpl


@router.delete("/templates/{template_id}", status_code=204)
async def delete_template(template_id: str, authorization: str = Header(...)) -> None:
    _require_auth(authorization)
    if template_id not in _templates:
        raise HTTPException(status_code=404, detail="Template not found")
    del _templates[template_id]
    _versions.pop(template_id, None)


@router.post("/templates/{template_id}/versions")
async def create_version(
    template_id: str,
    body: SGVersionCreate,
    authorization: str = Header(...),
) -> dict:
    _require_auth(authorization)
    if template_id not in _templates:
        raise HTTPException(status_code=404, detail="Template not found")
    vid = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()
    version = {
        "id": vid,
        "template_id": template_id,
        "name": body.name,
        "html_content": body.html_content,
        "subject": body.subject,
        "updated_at": now,
    }
    _versions.setdefault(template_id, []).append(version)
    return version


@router.get("/templates/{template_id}/versions")
async def list_versions(template_id: str, authorization: str = Header(...)) -> list[dict]:
    _require_auth(authorization)
    if template_id not in _templates:
        raise HTTPException(status_code=404, detail="Template not found")
    return _versions.get(template_id, [])
