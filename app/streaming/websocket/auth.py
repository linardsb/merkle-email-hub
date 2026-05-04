"""WebSocket authentication for collaboration rooms."""

from __future__ import annotations

from app.auth.models import User
from app.auth.repository import UserRepository
from app.auth.token import decode_token, is_token_revoked
from app.core.logging import get_logger
from app.core.scoped_db import get_scoped_db_context, get_system_db_context
from app.projects.service import ProjectService

logger = get_logger(__name__)

EDIT_ROLES = frozenset({"admin", "developer"})


class AuthResult:
    """Result of WebSocket authentication."""

    __slots__ = ("can_edit", "user")

    def __init__(self, user: User, can_edit: bool) -> None:
        self.user = user
        self.can_edit = can_edit


async def authenticate_websocket(
    token: str | None,
) -> AuthResult | None:
    """Authenticate a WebSocket connection via JWT query param.

    Returns AuthResult on success, None on failure.
    """
    if token is None:
        logger.info("collab.ws.auth_failed", reason="missing_token")
        return None

    payload = decode_token(token)
    if payload is None or payload.type != "access":
        logger.info("collab.ws.auth_failed", reason="invalid_token")
        return None

    if await is_token_revoked(payload.jti):
        logger.info("collab.ws.auth_failed", reason="token_revoked", user_id=payload.sub)
        return None

    # System-scoped: pre-auth resolver, no user yet. UserRepository is tenant-exempt.
    async with get_system_db_context() as db:
        user_repo = UserRepository(db)
        user = await user_repo.find_by_id(payload.sub)

    if user is None:
        logger.warning("collab.ws.auth_failed", reason="user_not_found", user_id=payload.sub)
        return None

    can_edit = user.role in EDIT_ROLES
    return AuthResult(user=user, can_edit=can_edit)


async def verify_room_access(user: User, room_id: str) -> bool:
    """Verify user has access to the project owning the room.

    Room ID format: "project:{project_id}:template:{template_id}"
    """
    try:
        parts = room_id.split(":")
        if len(parts) < 2 or parts[0] != "project":
            logger.warning("collab.ws.invalid_room_id", room_id=room_id)
            return False
        project_id = int(parts[1])
    except (ValueError, IndexError):
        logger.warning("collab.ws.invalid_room_id", room_id=room_id)
        return False

    try:
        async with get_scoped_db_context(user) as db:
            project_service = ProjectService(db)
            await project_service.verify_project_access(project_id, user)
        return True
    except Exception:
        logger.warning(
            "collab.ws.room_access_denied",
            user_id=user.id,
            room_id=room_id,
        )
        return False
