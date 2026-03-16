"""Application configuration using pydantic-settings.

Nested configuration groups with env_nested_delimiter for logical organization.
Environment variables use double-underscore nesting: DATABASE__URL, AUTH__JWT_SECRET_KEY, etc.
"""

from functools import lru_cache

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseConfig(BaseModel):
    """Database connection settings."""

    url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/email_hub"
    pool_size: int = 3
    pool_max_overflow: int = 5
    pool_recycle: int = 3600


class RedisConfig(BaseModel):
    """Redis connection settings."""

    url: str = "redis://localhost:6379/0"


class AuthConfig(BaseModel):
    """Authentication and JWT settings."""

    jwt_secret_key: str = "CHANGE-ME-IN-PRODUCTION"  # noqa: S105
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
    daily_quota: int = 50  # Per-user daily request limit (Redis-backed)
    stream_timeout_seconds: int = 120  # Max duration for a streaming response

    # Model routing — maps task tiers to model identifiers
    model_complex: str = ""  # Empty = use default model
    model_standard: str = ""  # Empty = use default model
    model_lightweight: str = ""  # Empty = use default model

    # Adaptive model tier routing — tracks per-agent success rates and auto-adjusts tier
    adaptive_routing_enabled: bool = False  # AI__ADAPTIVE_ROUTING_ENABLED

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
    # HTML chunking (Phase 16.3)
    html_chunk_size: int = 1024
    html_chunk_overlap: int = 100
    html_chunking_enabled: bool = True
    # CRAG validation loop (Phase 16.5)
    crag_enabled: bool = False
    crag_min_severity: str = "error"
    # Query router (Phase 16.1)
    router_enabled: bool = False
    router_llm_fallback: bool = False
    router_llm_model: str = "gpt-4o-mini"
    # Multi-representation indexing (Phase 16.6)
    multi_rep_enabled: bool = False
    multi_rep_model: str = "gpt-4o-mini"
    multi_rep_api_base_url: str = "https://api.openai.com/v1"
    multi_rep_api_key: str = ""
    multi_rep_max_concurrency: int = 5


class RenderingConfig(BaseModel):
    """Cross-client rendering test settings."""

    provider: str = "litmus"  # litmus, eoa, mock
    litmus_api_key: str = ""
    eoa_api_key: str = ""
    poll_interval_seconds: int = 10
    poll_timeout_seconds: int = 300
    max_concurrent_tests: int = 5
    screenshot_storage_path: str = "data/screenshots"


class MemoryConfig(BaseModel):
    """Agent memory system settings."""

    enabled: bool = True
    embedding_dimension: int = 1024
    default_decay_half_life_days: int = 30
    decay_active_days: int = 60
    decay_maintenance_days: int = 14
    decay_archived_days: int = 3
    compaction_interval_hours: int = 24
    compaction_similarity_threshold: float = 0.92
    intent_similarity_threshold: float = 0.85
    max_memories_per_project: int = 5000
    context_injection_limit: int = 10
    dcg_promotion_min_frequency: int = 3


class CogneeConfig(BaseModel):
    """Cognee knowledge graph configuration."""

    enabled: bool = False
    llm_provider: str = ""  # empty = inherit from AI config
    llm_model: str = ""  # empty = inherit from AI config
    llm_api_key: str = ""  # empty = inherit from AI config
    graph_db_provider: str = "kuzu"  # kuzu | neo4j
    neo4j_url: str = ""
    neo4j_user: str = ""
    neo4j_password: str = ""
    vector_db_provider: str = "pgvector"
    chunk_size: int = 512
    chunk_overlap: int = 50
    data_directory: str = "data/cognee"
    system_directory: str = "data/cognee/system"
    background_cognify: bool = True
    prefetch_enabled: bool = False  # Enable knowledge graph pre-query for agents
    prefetch_ttl_seconds: int = 300  # Redis cache TTL (5 min)
    prefetch_top_k: int = 3  # Max similar outcomes to return
    prefetch_min_score: float = 0.3  # Minimum similarity score to include


class OntologySyncConfig(BaseModel):
    """Can I Email ontology sync settings."""

    enabled: bool = False
    interval_hours: int = 168  # Weekly default
    github_repo: str = "hteumeuleu/caniemail"
    github_branch: str = "main"
    github_token: str = ""  # Optional — increases rate limit from 60/hr to 5000/hr
    request_timeout_seconds: int = 30
    max_features_per_sync: int = 500  # Safety cap


class DesignSyncConfig(BaseModel):
    """Design tool sync settings."""

    encryption_key: str = ""  # If empty, derived from jwt_secret_key via PBKDF2
    asset_storage_path: str = "data/design-assets"
    asset_max_width: int = 1200  # Max width for email images; 1200 = 2x retina for 600px containers


class ESPSyncConfig(BaseModel):
    """ESP bidirectional sync settings — base URLs for mock or production ESPs."""

    braze_base_url: str = "http://mock-esp:3002/braze"
    sfmc_base_url: str = "http://mock-esp:3002/sfmc"
    adobe_base_url: str = "http://mock-esp:3002/adobe"
    taxi_base_url: str = "http://mock-esp:3002/taxi"


class BlueprintConfig(BaseModel):
    """Blueprint execution settings."""

    daily_token_cap: int = 500_000  # Max tokens per user per day across all blueprint runs
    judge_on_retry: bool = False  # When True, run LLM judge on recovery retries (iteration > 0)
    checkpoints_enabled: bool = False  # Opt-in checkpoint persistence (backward compatible)
    checkpoint_retention_days: int = 7  # Auto-cleanup age limit for old checkpoints


class EvalConfig(BaseModel):
    """Eval and production sampling settings."""

    production_sample_rate: float = 0.0  # 0.0 = disabled; 1.0 = 100%
    production_queue_key: str = "eval:production_judge_queue"
    worker_interval_seconds: int = 300  # 5 min polling
    verdicts_path: str = "traces/production_verdicts.jsonl"


class WebSocketConfig(BaseModel):
    """WebSocket streaming settings."""

    enabled: bool = True
    heartbeat_interval_seconds: int = 30
    max_connections: int = 100
    max_connections_per_user: int = 5


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
    app_name: str = "email-hub"
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

    memory: MemoryConfig = MemoryConfig()
    cognee: CogneeConfig = CogneeConfig()
    blueprint: BlueprintConfig = BlueprintConfig()
    ws: WebSocketConfig = WebSocketConfig()
    rendering: RenderingConfig = RenderingConfig()
    ontology_sync: OntologySyncConfig = OntologySyncConfig()
    design_sync: DesignSyncConfig = DesignSyncConfig()
    esp_sync: ESPSyncConfig = ESPSyncConfig()
    eval: EvalConfig = EvalConfig()

    # Service URLs
    maizzle_builder_url: str = "http://localhost:3001"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Returns:
        The application settings instance.
    """
    return Settings()  # pyright: ignore[reportCallIssue]
