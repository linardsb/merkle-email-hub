"""Observability configuration: Sentry error tracking + OpenTelemetry tracing.

Both subsystems are opt-in. Sentry initialises only when ``SENTRY__DSN`` is
set; OTEL initialises only when ``OTEL__ENABLED`` is true. Tests run without
either touching the runtime.
"""

from pydantic import BaseModel, Field


class SentryConfig(BaseModel):
    """Sentry SDK settings.

    Initialisation is gated on a non-empty ``dsn``; when unset the SDK is
    never imported, so dev/test runs incur zero cost.
    """

    dsn: str = ""  # SENTRY__DSN — empty disables Sentry entirely
    environment: str = "development"  # SENTRY__ENVIRONMENT — tag attached to events
    release: str = ""  # SENTRY__RELEASE — git sha or version tag (optional)
    traces_sample_rate: float = Field(default=0.1, ge=0.0, le=1.0)
    profiles_sample_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    send_default_pii: bool = False  # PII redaction in app/core/redaction.py runs first


class OtelConfig(BaseModel):
    """OpenTelemetry tracing settings.

    Exports OTLP/HTTP traces (default) or OTLP/gRPC to a collector. When
    ``enabled`` is false no instrumentors are loaded.
    """

    enabled: bool = False  # OTEL__ENABLED
    service_name: str = "email-hub"  # OTEL__SERVICE_NAME
    exporter_endpoint: str = "http://localhost:4318/v1/traces"  # OTEL__EXPORTER_ENDPOINT
    exporter_protocol: str = "http/protobuf"  # OTEL__EXPORTER_PROTOCOL — "http/protobuf" or "grpc"
    sample_rate: float = Field(default=0.1, ge=0.0, le=1.0)  # OTEL__SAMPLE_RATE
