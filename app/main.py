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

# AI agents
from app.ai.agents.content.routes import router as content_router
from app.ai.agents.dark_mode.routes import router as dark_mode_router
from app.ai.agents.scaffolder.routes import router as scaffolder_router
from app.ai.agents.skills_routes import router as skills_router
from app.ai.blueprints.routes import router as blueprint_router
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
from app.core.redis import close_redis, redis_available
from app.design_sync.routes import router as design_sync_router
from app.email_engine.routes import router as email_engine_router
from app.example.routes import router as example_router
from app.knowledge.ontology.routes import router as ontology_router
from app.knowledge.routes import router as knowledge_router
from app.memory.routes import router as memory_router
from app.personas.routes import router as personas_router

# Email Hub modules
from app.projects.routes import router as projects_router
from app.qa_engine.routes import router as qa_router
from app.rendering.routes import router as rendering_router
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

    # SECURITY: Block default database credentials in non-development environments
    if settings.environment != "development" and "postgres:postgres@" in settings.database.url:
        msg = "DATABASE__URL must not use default credentials (postgres:postgres) in non-development environments"
        raise RuntimeError(msg)

    logger.info(
        "application.lifecycle_started",
        app_name=settings.app_name,
        version=settings.version,
        environment=settings.environment,
    )
    logger.info("database.connection_initialized")

    # Start WebSocket subscriber (only if Redis is reachable)
    if settings.ws.enabled and await redis_available():
        ws_manager = get_ws_manager()
        await start_ws_subscriber(ws_manager)
        logger.info("streaming.ws.subscriber_started")
    elif settings.ws.enabled:
        logger.warning(
            "streaming.ws.subscriber_skipped",
            detail="Redis unavailable, WebSocket streaming disabled",
        )

    # Start outcome graph poller (feeds blueprint outcomes into Cognee)
    outcome_poller = None
    if getattr(settings, "cognee", None) and settings.cognee.enabled:
        try:
            from app.ai.blueprints.outcome_poller import OutcomeGraphPoller

            outcome_poller = OutcomeGraphPoller()
            await outcome_poller.start()
            logger.info("blueprint.outcome_poller_started")
        except Exception:
            logger.warning("blueprint.outcome_poller_start_failed", exc_info=True)

    # Start Can I Email ontology sync poller
    caniemail_poller = None
    if settings.ontology_sync.enabled:
        try:
            from app.knowledge.ontology.sync.poller import CanIEmailSyncPoller

            caniemail_poller = CanIEmailSyncPoller()
            await caniemail_poller.start()
            logger.info("ontology.sync.poller_started")
        except Exception:
            logger.warning("ontology.sync.poller_start_failed", exc_info=True)

    # Start production judge worker (samples successful runs for offline LLM judging)
    judge_worker = None
    if settings.eval.production_sample_rate > 0.0 and await redis_available():
        try:
            from app.ai.agents.evals.production_sampler import ProductionJudgeWorker

            judge_worker = ProductionJudgeWorker()
            await judge_worker.start()
            logger.info("eval.production_judge_worker_started")
        except Exception:
            logger.warning("eval.production_judge_worker_start_failed", exc_info=True)

    yield

    # Shutdown

    if judge_worker is not None:
        await judge_worker.stop()
        logger.info("eval.production_judge_worker_stopped")

    if caniemail_poller is not None:
        await caniemail_poller.stop()
        logger.info("ontology.sync.poller_stopped")

    if outcome_poller is not None:
        await outcome_poller.stop()
        logger.info("blueprint.outcome_poller_stopped")

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
app.include_router(ontology_router)


app.include_router(ws_router)

# Email Hub routers
app.include_router(projects_router)
app.include_router(email_engine_router)
app.include_router(components_router)
app.include_router(qa_router)
app.include_router(connectors_router)
app.include_router(design_sync_router)
app.include_router(approval_router)
app.include_router(personas_router)
app.include_router(templates_router)
app.include_router(rendering_router)
app.include_router(memory_router)

# AI agents
app.include_router(scaffolder_router)
app.include_router(dark_mode_router)
app.include_router(content_router)
app.include_router(blueprint_router)

app.include_router(skills_router)


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
