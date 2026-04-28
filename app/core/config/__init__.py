"""Application configuration package.

Per-domain settings live in sibling modules; this `__init__.py` is the public
entry point that callers use as `app.core.config`. It re-exports every
sub-Config so existing `from app.core.config import <X>` callsites keep working
after the package split.

Environment variables use double-underscore nesting:
    DATABASE__URL=postgresql+asyncpg://...
    AI__PROVIDER=anthropic
    AUTH__JWT_SECRET_KEY=...
"""

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.config.ai import AIConfig, EmbeddingConfig, RerankerConfig
from app.core.config.auth import AuthConfig
from app.core.config.blueprint import BlueprintConfig, EvalConfig
from app.core.config.connectors import (
    BriefsConfig,
    CredentialsConfig,
    ESPSyncConfig,
    TolgeeConfig,
)
from app.core.config.database import DatabaseConfig, RedisConfig
from app.core.config.design_sync import DesignSyncConfig
from app.core.config.knowledge import CogneeConfig, KnowledgeConfig, MemoryConfig
from app.core.config.misc import (
    CollabWebSocketConfig,
    CorrectionTrackerConfig,
    EmailEngineConfig,
    ExportConfig,
    KestraConfig,
    MCPConfig,
    OntologySyncConfig,
    PluginsConfig,
    ProgressConfig,
    ReportingConfig,
    SkillExtractionConfig,
    TemplatesUploadConfig,
    VariantsConfig,
    VoiceConfig,
    WebSocketConfig,
)
from app.core.config.notifications import NotificationsConfig
from app.core.config.qa import (
    QABIMIConfig,
    QAChaosConfig,
    QADeliverabilityConfig,
    QAGmailPredictorConfig,
    QAMetaEvalConfig,
    QAOutlookAnalyzerConfig,
    QAPropertyTestingConfig,
    QASyntheticConfig,
)
from app.core.config.rendering import (
    CalibrationConfig,
    ChangeDetectionConfig,
    RenderingConfig,
    SandboxConfig,
)
from app.core.config.scheduling import DebounceConfig, SchedulingConfig
from app.core.config.security import SecurityConfig

__all__ = [
    "AIConfig",
    "AuthConfig",
    "BlueprintConfig",
    "BriefsConfig",
    "CalibrationConfig",
    "ChangeDetectionConfig",
    "CogneeConfig",
    "CollabWebSocketConfig",
    "CorrectionTrackerConfig",
    "CredentialsConfig",
    "DatabaseConfig",
    "DebounceConfig",
    "DesignSyncConfig",
    "ESPSyncConfig",
    "EmailEngineConfig",
    "EmbeddingConfig",
    "EvalConfig",
    "ExportConfig",
    "KestraConfig",
    "KnowledgeConfig",
    "MCPConfig",
    "MemoryConfig",
    "NotificationsConfig",
    "OntologySyncConfig",
    "PluginsConfig",
    "ProgressConfig",
    "QABIMIConfig",
    "QAChaosConfig",
    "QADeliverabilityConfig",
    "QAGmailPredictorConfig",
    "QAMetaEvalConfig",
    "QAOutlookAnalyzerConfig",
    "QAPropertyTestingConfig",
    "QASyntheticConfig",
    "RedisConfig",
    "RenderingConfig",
    "ReportingConfig",
    "RerankerConfig",
    "SandboxConfig",
    "SchedulingConfig",
    "SecurityConfig",
    "Settings",
    "SkillExtractionConfig",
    "TemplatesUploadConfig",
    "TolgeeConfig",
    "VariantsConfig",
    "VoiceConfig",
    "WebSocketConfig",
    "get_settings",
]


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
    logging_pii_redaction: bool = True  # LOGGING__PII_REDACTION
    api_prefix: str = "/api"

    # CORS
    allowed_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:8891",
        "http://localhost:8899",
    ]

    # Nested configuration groups
    database: DatabaseConfig = DatabaseConfig()
    redis: RedisConfig = RedisConfig()
    auth: AuthConfig = AuthConfig()

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
    change_detection: ChangeDetectionConfig = ChangeDetectionConfig()
    design_sync: DesignSyncConfig = DesignSyncConfig()
    esp_sync: ESPSyncConfig = ESPSyncConfig()
    eval: EvalConfig = EvalConfig()
    qa_chaos: QAChaosConfig = QAChaosConfig()
    qa_property_testing: QAPropertyTestingConfig = QAPropertyTestingConfig()
    qa_outlook_analyzer: QAOutlookAnalyzerConfig = QAOutlookAnalyzerConfig()
    qa_deliverability: QADeliverabilityConfig = QADeliverabilityConfig()
    mcp: MCPConfig = MCPConfig()
    email_engine: EmailEngineConfig = EmailEngineConfig()
    qa_gmail_predictor: QAGmailPredictorConfig = QAGmailPredictorConfig()
    qa_bimi: QABIMIConfig = QABIMIConfig()
    voice: VoiceConfig = VoiceConfig()
    collab_ws: CollabWebSocketConfig = CollabWebSocketConfig()
    plugins: PluginsConfig = PluginsConfig()
    skill_extraction: SkillExtractionConfig = SkillExtractionConfig()
    templates: TemplatesUploadConfig = TemplatesUploadConfig()
    variants: VariantsConfig = VariantsConfig()
    tolgee: TolgeeConfig = TolgeeConfig()
    kestra: KestraConfig = KestraConfig()
    reporting: ReportingConfig = ReportingConfig()
    briefs: BriefsConfig = BriefsConfig()
    export: ExportConfig = ExportConfig()
    correction_tracker: CorrectionTrackerConfig = CorrectionTrackerConfig()
    progress: ProgressConfig = ProgressConfig()
    scheduling: SchedulingConfig = SchedulingConfig()
    notifications: NotificationsConfig = NotificationsConfig()
    security: SecurityConfig = SecurityConfig()
    debounce: DebounceConfig = DebounceConfig()
    credentials: CredentialsConfig = CredentialsConfig()
    qa_synthetic: QASyntheticConfig = QASyntheticConfig()
    qa_meta_eval: QAMetaEvalConfig = QAMetaEvalConfig()

    # Service URLs
    maizzle_builder_url: str = "http://localhost:3001"

    @model_validator(mode="after")
    def _validate_production_secrets(self) -> "Settings":
        """Refuse default placeholder secrets when running in production."""
        if self.environment == "production":
            if self.auth.jwt_secret_key.startswith("CHANGE-ME-IN-PRODUCTION"):
                msg = "AUTH__JWT_SECRET_KEY must not be the default placeholder in production"
                raise ValueError(msg)
            if self.auth.demo_user_password == "admin":  # noqa: S105
                msg = "AUTH__DEMO_USER_PASSWORD must not be 'admin' in production"
                raise ValueError(msg)
        return self


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Returns:
        The application settings instance.
    """
    return Settings()  # pyright: ignore[reportCallIssue]
