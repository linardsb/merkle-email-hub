"""Mock ESP Server — simulates Braze, SFMC, Adobe Campaign, and Taxi for Email APIs."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from database import DatabaseManager
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from middleware import (
    esp_validation_error_handler,
    latency_simulation_middleware,
    rate_limiter_middleware,
)
from seed import seed_all
from starlette.middleware.base import BaseHTTPMiddleware

db = DatabaseManager()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    await db.init_tables()
    await seed_all(db)
    yield
    await db.close()


app = FastAPI(title="Mock ESP Server", version="1.0.0", lifespan=lifespan)

# Middleware: outermost runs first — latency wraps rate limiter
app.add_middleware(BaseHTTPMiddleware, dispatch=latency_simulation_middleware)
app.add_middleware(BaseHTTPMiddleware, dispatch=rate_limiter_middleware)

# ESP-specific validation error formatting
app.add_exception_handler(RequestValidationError, esp_validation_error_handler)  # type: ignore[arg-type]

from adobe.routes import router as adobe_router  # noqa: E402
from braze.routes import router as braze_router  # noqa: E402
from briefs.routes import router as briefs_router  # noqa: E402
from sfmc.routes import router as sfmc_router  # noqa: E402
from taxi.routes import router as taxi_router  # noqa: E402

app.include_router(braze_router)
app.include_router(sfmc_router)
app.include_router(adobe_router)
app.include_router(taxi_router)
app.include_router(briefs_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy", "service": "mock-esp"}
