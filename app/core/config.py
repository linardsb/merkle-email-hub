"""Application configuration using pydantic-settings.

Nested configuration groups with env_nested_delimiter for logical organization.
Environment variables use double-underscore nesting: DATABASE__URL, AUTH__JWT_SECRET_KEY, etc.
"""

from functools import lru_cache

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseConfig(BaseModel):
    """Database connection settings."""

    url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/merkle_email_hub"
    pool_size: int = 3
    pool_max_overflow: int = 5
    pool_recycle: int = 3600


class RedisConfig(BaseModel):
    """Redis connection settings."""

    url: str = "redis://localhost:6379/0"


class AuthConfig(BaseModel):
    """Authentication and JWT settings."""

    jwt_secret_key: str = "CHANGE-ME-IN-PRODUCTION"  # noqa: S105
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    demo_user_password: str = "admin"  # noqa: S105


class RateLimitConfig(BaseModel):
    """Rate limiting settings (requests per time window per IP)."""

    default: str = "120/minute"
    auth: str = "10/minute"
    health: str = "60/minute"

    chat: str = "10/minute"


class AIConfig(BaseModel):
    """AI provider settings."""

    provider: str = "openai"  # openai, anthropic, ollama, custom
    model: str = "gpt-4o-mini"
    api_key: str | None = None
    base_url: str | None = None  # Custom endpoint (Ollama, vLLM, LiteLLM)
    daily_quota: int = 50  # Per-IP daily request limit

    # Model routing — maps task tiers to model identifiers
    model_complex: str = ""  # Empty = use default model
    model_standard: str = ""  # Empty = use default model
    model_lightweight: str = ""  # Empty = use default model

    # AI-specific rate limits
    rate_limit_chat: str = "20/minute"
    rate_limit_generation: str = "5/minute"


class EmbeddingConfig(BaseModel):
    """Embedding provider settings."""

    provider: str = "openai"  # openai, jina, local
    model: str = "text-embedding-3-small"
    dimension: int = 1536
    api_key: str | None = None
    base_url: str | None = None


class RerankerConfig(BaseModel):
    """Reranker settings."""

    provider: str = "none"  # none, cohere, jina, local
    model: str = ""
    top_k: int = 10


class KnowledgeConfig(BaseModel):
    """Knowledge base / RAG pipeline settings."""

    chunk_size: int = 512
    chunk_overlap: int = 50
    search_limit: int = 50
    document_storage_path: str = "data/documents"
    auto_tag_enabled: bool = False
    auto_tag_max_chars: int = 4000
    auto_tag_model: str = "gpt-4o-mini"
    auto_tag_api_base_url: str = "https://api.openai.com/v1"
    auto_tag_api_key: str = ""


class WebSocketConfig(BaseModel):
    """WebSocket streaming settings."""

    enabled: bool = True
    heartbeat_interval_seconds: int = 30
    max_connections: int = 100


class Settings(BaseSettings):
    """Application-wide configuration.

    All settings can be overridden via environment variables.
    Nested groups use double-underscore delimiter: DATABASE__URL, AUTH__JWT_SECRET_KEY, etc.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    # Application metadata
    app_name: str = "merkle-email-hub"
    version: str = "0.1.0"
    environment: str = "development"
    log_level: str = "INFO"
    api_prefix: str = "/api"

    # CORS
    allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:8891"]

    # Nested configuration groups
    database: DatabaseConfig = DatabaseConfig()
    redis: RedisConfig = RedisConfig()
    auth: AuthConfig = AuthConfig()
    rate_limit: RateLimitConfig = RateLimitConfig()

    ai: AIConfig = AIConfig()

    embedding: EmbeddingConfig = EmbeddingConfig()
    reranker: RerankerConfig = RerankerConfig()
    knowledge: KnowledgeConfig = KnowledgeConfig()

    ws: WebSocketConfig = WebSocketConfig()

    # Service URLs
    maizzle_builder_url: str = "http://localhost:3001"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Returns:
        The application settings instance.
    """
    return Settings()  # pyright: ignore[reportCallIssue]
