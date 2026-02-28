"""FastAPI application entry point.

Configures the application with:
- Lifespan event management for startup/shutdown
- Structured logging setup
- Request/response middleware
- CORS support
- Health check endpoints
- Global exception handlers
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, cast

import uvicorn
from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler  # pyright: ignore[reportMissingTypeStubs]
from slowapi.errors import RateLimitExceeded  # pyright: ignore[reportMissingTypeStubs]

from app.ai.exceptions import setup_ai_exception_handlers
from app.ai.routes import router as ai_router
from app.approval.routes import router as approval_router
from app.auth.routes import router as auth_router
from app.components.routes import router as components_router
from app.connectors.routes import router as connectors_router
from app.core.config import get_settings
from app.core.database import engine
from app.core.exceptions import setup_exception_handlers
from app.core.health import router as health_router
from app.core.logging import get_logger, setup_logging
from app.core.middleware import setup_middleware
from app.core.rate_limit import limiter
from app.core.redis import close_redis
from app.email_engine.routes import router as email_engine_router
from app.example.routes import router as example_router
from app.knowledge.routes import router as knowledge_router
from app.personas.routes import router as personas_router

# Email Hub modules
from app.projects.routes import router as projects_router
from app.qa_engine.routes import router as qa_router
from app.streaming.routes import close_ws_manager, get_ws_manager, ws_router
from app.streaming.subscriber import start_ws_subscriber, stop_ws_subscriber
from app.templates.routes import router as templates_router

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan event handler."""
    # Startup
    setup_logging(log_level=settings.log_level)
    logger = get_logger(__name__)

    # SECURITY: Fail hard if JWT secret is weak in non-development environments
    _insecure_defaults = {"CHANGE-ME-IN-PRODUCTION", "", "secret", "changeme"}
    if settings.environment != "development" and (
        settings.auth.jwt_secret_key in _insecure_defaults or len(settings.auth.jwt_secret_key) < 32
    ):
        msg = "AUTH__JWT_SECRET_KEY must be a strong secret (min 32 chars) in non-development environments"
        raise RuntimeError(msg)

    logger.info(
        "application.lifecycle_started",
        app_name=settings.app_name,
        version=settings.version,
        environment=settings.environment,
    )
    logger.info("database.connection_initialized")

    # Start WebSocket subscriber
    if settings.ws.enabled:
        ws_manager = get_ws_manager()
        await start_ws_subscriber(ws_manager)
        logger.info("streaming.ws.subscriber_started")

    yield

    # Shutdown

    await stop_ws_subscriber()
    close_ws_manager()
    logger.info("streaming.ws.lifecycle_stopped")

    await close_redis()
    await engine.dispose()
    logger.info("database.connection_closed")
    logger.info("application.lifecycle_stopped", app_name=settings.app_name)


# Create FastAPI application
_is_dev = settings.environment == "development"

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    lifespan=lifespan,
    docs_url="/docs" if _is_dev else None,
    openapi_url="/openapi.json" if _is_dev else None,
    redoc_url="/redoc" if _is_dev else None,
)

# Setup rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, cast(Any, _rate_limit_exceeded_handler))

# Setup middleware
setup_middleware(app)

# Setup exception handlers
setup_exception_handlers(app)

setup_ai_exception_handlers(app)


# Include routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(example_router)

app.include_router(ai_router)


app.include_router(knowledge_router)


app.include_router(ws_router)

# Email Hub routers
app.include_router(projects_router)
app.include_router(email_engine_router)
app.include_router(components_router)
app.include_router(qa_router)
app.include_router(connectors_router)
app.include_router(approval_router)
app.include_router(personas_router)
app.include_router(templates_router)


@app.get("/")
def read_root() -> dict[str, str]:
    """Root endpoint providing API information."""
    response: dict[str, str] = {"message": settings.app_name}
    if settings.environment == "development":
        response["version"] = settings.version
        response["docs"] = "/docs"
    return response


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",  # noqa: S104
        port=8891,
        reload=True,
    )
