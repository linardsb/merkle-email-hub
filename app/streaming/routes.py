# pyright: reportUnknownMemberType=false
"""WebSocket endpoint for real-time data streaming.

Authentication is via JWT query parameter since the browser WebSocket API
does not support custom headers. The token is validated using the same
decode_token + is_token_revoked logic as HTTP endpoints.
"""

import asyncio
import json

from fastapi import APIRouter, Query, WebSocket
from starlette.websockets import WebSocketDisconnect

from app.auth.repository import UserRepository
from app.auth.token import decode_token, is_token_revoked
from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.core.logging import get_logger
from app.streaming.manager import ConnectionManager
from app.streaming.schemas import WsAck, WsError, WsSubscribeMessage

logger = get_logger(__name__)

ws_router = APIRouter()

# Module-level singleton
_ws_manager: ConnectionManager | None = None


def get_ws_manager() -> ConnectionManager:
    """Get or create the WebSocket ConnectionManager singleton."""
    global _ws_manager
    if _ws_manager is None:
        settings = get_settings()
        _ws_manager = ConnectionManager(max_connections=settings.ws.max_connections)
    return _ws_manager


def close_ws_manager() -> None:
    """Reset the ConnectionManager singleton on shutdown."""
    global _ws_manager
    _ws_manager = None


async def _send_heartbeats(websocket: WebSocket, interval: int) -> None:
    """Send periodic application-level ping messages.

    Clients should respond with {"action": "pong"} to keep the connection alive.

    Args:
        websocket: The WebSocket connection to send pings to.
        interval: Seconds between heartbeat pings.
    """
    try:
        while True:
            await asyncio.sleep(interval)
            await websocket.send_json({"type": "ping"})
    except (WebSocketDisconnect, asyncio.CancelledError):
        return
    except Exception:
        # Heartbeat send failed -- connection is broken, task exits
        return


@ws_router.websocket("/ws/stream")
async def ws_stream(
    websocket: WebSocket,
    token: str | None = Query(None),
) -> None:
    """WebSocket endpoint for live data streaming.

    Authentication: JWT token via ?token= query parameter.
    Protocol: JSON text messages for subscribe/unsubscribe/pong.
    """
    settings = get_settings()

    # --- Feature flag check ---
    if not settings.ws.enabled:
        await websocket.close(code=1013, reason="WebSocket streaming disabled")
        return

    # --- Authentication (manual, not via Depends) ---
    if token is None:
        await websocket.close(code=4001, reason="Authentication failed")
        logger.info("streaming.ws.auth_failed", reason="missing_token")
        return

    payload = decode_token(token)
    if payload is None or payload.type != "access":
        await websocket.close(code=4001, reason="Authentication failed")
        logger.info("streaming.ws.auth_failed", reason="invalid_token")
        return

    if await is_token_revoked(payload.jti):
        await websocket.close(code=4001, reason="Authentication failed")
        logger.info(
            "streaming.ws.auth_failed",
            reason="token_revoked",
            user_id=payload.sub,
        )
        return

    # --- Connection setup (accept before registering to avoid broadcast to un-accepted socket) ---
    await websocket.accept()

    manager = get_ws_manager()
    if not await manager.connect(websocket):
        await websocket.close(code=1013, reason="Try again later")
        return

    user_id = payload.sub

    # Resolve User object for BOLA authorization checks
    async with AsyncSessionLocal() as auth_db:
        user_repo = UserRepository(auth_db)
        ws_user = await user_repo.find_by_id(int(user_id))
    if not ws_user:
        await websocket.close(code=4001, reason="Authentication failed")
        logger.warning("streaming.ws.auth_failed", reason="user_not_found", user_id=user_id)
        manager.disconnect(websocket)
        return

    logger.info(
        "streaming.ws.connected",
        user_id=user_id,
        active_count=manager.active_count,
    )

    # Send initial ack
    ack = WsAck(action="connected", filters={})
    await websocket.send_json(ack.model_dump())

    # Start heartbeat task
    heartbeat_task = asyncio.create_task(
        _send_heartbeats(websocket, settings.ws.heartbeat_interval_seconds)
    )

    # --- Message loop ---
    try:
        while True:
            raw = await websocket.receive_text()

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                error_msg = WsError(code="parse_error", message="Invalid JSON")
                await websocket.send_json(error_msg.model_dump())
                continue

            action = data.get("action")

            if action == "subscribe":
                try:
                    msg = WsSubscribeMessage.model_validate(data)
                    # Convert filters to the format expected by the manager
                    # (None values mean "all" for that dimension)
                    new_filters: dict[str, str | None] = {}
                    if msg.filters:
                        for key, value in msg.filters.items():
                            new_filters[key] = value

                    # BOLA: validate project_id filter against user membership
                    filter_project_id = new_filters.get("project_id")
                    if filter_project_id is not None:
                        from app.projects.service import ProjectService

                        try:
                            async with AsyncSessionLocal() as project_db:
                                project_service = ProjectService(project_db)
                                await project_service.verify_project_access(
                                    int(filter_project_id), ws_user
                                )
                        except Exception:
                            denied_msg = WsError(
                                code="access_denied",
                                message="Access denied to project",
                            )
                            await websocket.send_json(denied_msg.model_dump())
                            logger.warning(
                                "streaming.ws.project_access_denied",
                                user_id=user_id,
                                project_id=filter_project_id,
                            )
                            continue

                    manager.update_filters(websocket, new_filters)
                    sub_ack = WsAck(
                        action="subscribe",
                        filters=new_filters,
                    )
                    await websocket.send_json(sub_ack.model_dump())
                    logger.info(
                        "streaming.ws.subscribe_updated",
                        user_id=user_id,
                        filters=new_filters,
                    )
                except Exception as e:
                    logger.warning(
                        "streaming.ws.subscribe_validation_failed",
                        user_id=user_id,
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                    error_msg = WsError(
                        code="invalid_subscribe",
                        message="Invalid subscribe message",
                    )
                    await websocket.send_json(error_msg.model_dump())

            elif action == "unsubscribe":
                manager.update_filters(websocket, filters={})
                unsub_ack = WsAck(
                    action="unsubscribe",
                    filters={},
                )
                await websocket.send_json(unsub_ack.model_dump())
                logger.info(
                    "streaming.ws.subscribe_updated",
                    user_id=user_id,
                    filters={},
                )

            elif action == "pong":
                # Client keepalive response to server ping -- no action needed
                pass

            else:
                error_msg = WsError(
                    code="unknown_action",
                    message=f"Unknown action: {str(action)[:50]}",
                )
                await websocket.send_json(error_msg.model_dump())

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning(
            "streaming.ws.unexpected_error",
            user_id=user_id,
            error=str(e),
            error_type=type(e).__name__,
        )
    finally:
        heartbeat_task.cancel()
        manager.disconnect(websocket)
        logger.info(
            "streaming.ws.disconnected",
            user_id=user_id,
            active_count=manager.active_count,
        )
