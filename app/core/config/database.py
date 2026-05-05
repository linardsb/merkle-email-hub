"""Database connection settings."""

from pydantic import BaseModel, Field


class DatabaseConfig(BaseModel):
    """Database connection settings."""

    url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/email_hub"
    pool_size: int = Field(default=20, ge=1)
    pool_max_overflow: int = Field(default=20, ge=0)
    pool_recycle: int = 1800
    # SQLAlchemy SQL echo emits through the stdlib `sqlalchemy.engine` logger,
    # which bypasses structlog's redact_event_dict. Keep off in shared logs;
    # opt-in only for local debugging where exposure is acceptable.
    echo: bool = False


class RedisConfig(BaseModel):
    """Redis connection settings."""

    url: str = "redis://localhost:6379/0"
