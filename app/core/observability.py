"""Sentry + OpenTelemetry initialisation.

Both subsystems are optional and lazily imported so production-only deps stay
out of test/dev startup paths. Call :func:`init_observability` once during
app lifespan startup.
"""
# pyright: reportMissingImports=false, reportUnknownMemberType=false, reportUnknownVariableType=false

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.logging import get_logger

if TYPE_CHECKING:
    from fastapi import FastAPI

    from app.core.config import Settings

logger = get_logger(__name__)


def init_sentry(settings: Settings) -> bool:
    """Initialise the Sentry SDK if ``SENTRY__DSN`` is configured.

    Returns ``True`` when Sentry was initialised, ``False`` otherwise. Import
    of ``sentry_sdk`` is deferred so dev/test runs without the dep installed
    do not fail at startup.
    """
    dsn = settings.sentry.dsn
    if not dsn:
        return False
    try:
        import sentry_sdk  # type: ignore[import-not-found]
        from sentry_sdk.integrations.fastapi import (  # type: ignore[import-not-found]
            FastApiIntegration,
        )
        from sentry_sdk.integrations.starlette import (  # type: ignore[import-not-found]
            StarletteIntegration,
        )
    except ImportError:
        logger.warning("observability.sentry_sdk_missing", dsn_set=True)
        return False

    sentry_sdk.init(
        dsn=dsn,
        environment=settings.sentry.environment,
        release=settings.sentry.release or None,
        traces_sample_rate=settings.sentry.traces_sample_rate,
        profiles_sample_rate=settings.sentry.profiles_sample_rate,
        send_default_pii=settings.sentry.send_default_pii,
        integrations=[
            StarletteIntegration(),
            FastApiIntegration(),
        ],
    )
    logger.info(
        "observability.sentry_initialized",
        environment=settings.sentry.environment,
        traces_sample_rate=settings.sentry.traces_sample_rate,
    )
    return True


def init_otel(app: FastAPI, settings: Settings) -> bool:
    """Wire OpenTelemetry tracing onto the FastAPI app + asyncpg.

    Returns ``True`` when OTEL was wired. Imports are deferred for the same
    reason as :func:`init_sentry`.
    """
    if not settings.otel.enabled:
        return False
    try:
        from opentelemetry import trace  # type: ignore[import-not-found]
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (  # type: ignore[import-not-found]
            OTLPSpanExporter,
        )
        from opentelemetry.instrumentation.asyncpg import (  # type: ignore[import-not-found]
            AsyncPGInstrumentor,
        )
        from opentelemetry.instrumentation.fastapi import (  # type: ignore[import-not-found]
            FastAPIInstrumentor,
        )
        from opentelemetry.sdk.resources import Resource  # type: ignore[import-not-found]
        from opentelemetry.sdk.trace import TracerProvider  # type: ignore[import-not-found]
        from opentelemetry.sdk.trace.export import (  # type: ignore[import-not-found]
            BatchSpanProcessor,
        )
        from opentelemetry.sdk.trace.sampling import (  # type: ignore[import-not-found]
            TraceIdRatioBased,
        )
    except ImportError:
        logger.warning("observability.otel_missing", enabled=True)
        return False

    resource = Resource.create({"service.name": settings.otel.service_name})
    provider = TracerProvider(
        resource=resource,
        sampler=TraceIdRatioBased(settings.otel.sample_rate),
    )
    exporter = OTLPSpanExporter(endpoint=settings.otel.exporter_endpoint)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app)
    AsyncPGInstrumentor().instrument()
    logger.info(
        "observability.otel_initialized",
        endpoint=settings.otel.exporter_endpoint,
        sample_rate=settings.otel.sample_rate,
    )
    return True


def init_observability(app: FastAPI, settings: Settings) -> None:
    """Initialise Sentry + OTEL during app lifespan startup."""
    init_sentry(settings)
    init_otel(app, settings)
