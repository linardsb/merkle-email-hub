"""Database connection settings."""

from pydantic import BaseModel, Field


class DatabaseConfig(BaseModel):
    """Database connection settings."""

    url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/email_hub"
    pool_size: int = Field(default=20, ge=1)
    pool_max_overflow: int = Field(default=20, ge=0)
    pool_recycle: int = 1800


class RedisConfig(BaseModel):
    """Redis connection settings."""

    url: str = "redis://localhost:6379/0"
