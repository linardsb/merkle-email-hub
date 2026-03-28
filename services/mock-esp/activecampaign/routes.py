"""ActiveCampaign Messages API mock routes."""

from datetime import UTC, datetime

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/activecampaign", tags=["ActiveCampaign"])

_messages: dict[str, dict] = {}
_next_id = 1


def _require_auth(api_token: str = Header(..., alias="Api-Token")) -> str:
    if not api_token.strip():
        raise HTTPException(status_code=401, detail="Empty API token")
    return api_token


class ACMessageCreate(BaseModel):
    name: str = Field(..., min_length=1)
    html: str = ""


class ACMessageUpdate(BaseModel):
    name: str | None = None
    html: str | None = None


@router.post("/messages")
async def create_message(
    body: ACMessageCreate,
    api_token: str = Header(..., alias="Api-Token"),
) -> dict:
    _require_auth(api_token)
    global _next_id
    mid = str(_next_id)
    _next_id += 1
    now = datetime.now(UTC).isoformat()
    msg = {
        "message": {
            "id": mid,
            "name": body.name,
            "html": body.html,
            "cdate": now,
            "mdate": now,
        }
    }
    _messages[mid] = msg["message"]
    return msg


@router.get("/messages")
async def list_messages(api_token: str = Header(..., alias="Api-Token")) -> dict:
    _require_auth(api_token)
    return {"messages": list(_messages.values())}


@router.get("/messages/{message_id}")
async def get_message(
    message_id: str,
    api_token: str = Header(..., alias="Api-Token"),
) -> dict:
    _require_auth(api_token)
    msg = _messages.get(message_id)
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    return {"message": msg}


@router.put("/messages/{message_id}")
async def update_message(
    message_id: str,
    body: ACMessageUpdate,
    api_token: str = Header(..., alias="Api-Token"),
) -> dict:
    _require_auth(api_token)
    msg = _messages.get(message_id)
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    if body.name is not None:
        msg["name"] = body.name
    if body.html is not None:
        msg["html"] = body.html
    msg["mdate"] = datetime.now(UTC).isoformat()
    return {"message": msg}


@router.delete("/messages/{message_id}")
async def delete_message(
    message_id: str,
    api_token: str = Header(..., alias="Api-Token"),
) -> dict:
    _require_auth(api_token)
    if message_id not in _messages:
        raise HTTPException(status_code=404, detail="Message not found")
    del _messages[message_id]
    return {"message": "deleted"}
