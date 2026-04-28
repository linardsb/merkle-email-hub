"""Application configuration using pydantic-settings.

Nested configuration groups with env_nested_delimiter for logical organization.
Environment variables use double-underscore nesting: DATABASE__URL, AUTH__JWT_SECRET_KEY, etc.
"""

from functools import lru_cache
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseConfig(BaseModel):
    """Database connection settings."""

    url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/email_hub"
    pool_size: int = Field(default=20, ge=1)
    pool_max_overflow: int = Field(default=20, ge=0)
    pool_recycle: int = 1800


class RedisConfig(BaseModel):
    """Redis connection settings."""

    url: str = "redis://localhost:6379/0"


class AuthConfig(BaseModel):
    """Authentication and JWT settings."""

    jwt_secret_key: str = Field(
        default="CHANGE-ME-IN-PRODUCTION-this-is-not-a-real-secret",  # 49 chars; passes min_length, trips prod sentinel
        min_length=32,
        description="HS256 signing key; must be >=32 chars (256 bits). Production refuses the default placeholder.",
    )
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    demo_user_email: str = "demo@example.com"
    demo_user_password: str = "admin"  # noqa: S105


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

    # Visual QA agent (Phase 17.3)
    visual_qa_enabled: bool = False  # AI__VISUAL_QA_ENABLED
    visual_qa_model: str = ""  # AI__VISUAL_QA_MODEL — empty = use default model routing
    visual_qa_clients: list[str] = [
        "gmail_web",
        "outlook_2019",
        "apple_mail",
    ]  # AI__VISUAL_QA_CLIENTS

    # Visual QA auto-fix (Phase 17.4)
    visual_qa_autofix_enabled: bool = False  # AI__VISUAL_QA_AUTOFIX_ENABLED
    visual_qa_autofix_max_rounds: int = 1  # AI__VISUAL_QA_AUTOFIX_MAX_ROUNDS

    # Token budget management (Phase 22.3)
    token_budget_enabled: bool = False  # AI__TOKEN_BUDGET_ENABLED
    token_budget_reserve: int = 4096  # AI__TOKEN_BUDGET_RESERVE — tokens reserved for response
    token_budget_max: int = 0  # AI__TOKEN_BUDGET_MAX — 0 = auto-detect from model name

    # Prompt template store (Phase 22.2)
    prompt_store_enabled: bool = False  # AI__PROMPT_STORE_ENABLED

    # Model capability registry (Phase 22.1)
    model_specs: list[dict[str, Any]] = []  # AI__MODEL_SPECS — JSON array of model specs

    # Fallback chains — ordered model fallbacks per tier (Phase 22.4)
    # JSON: {"complex": ["anthropic:claude-opus-4-6", "openai:gpt-4o"], ...}
    fallback_chains: dict[str, list[str]] = {}  # AI__FALLBACK_CHAINS

    # Cost governor (Phase 22.5)
    cost_governor_enabled: bool = False  # AI__COST_GOVERNOR_ENABLED
    monthly_budget_gbp: float = 600.0  # AI__MONTHLY_BUDGET_GBP — 0 = unlimited
    budget_warning_threshold: float = 0.8  # AI__BUDGET_WARNING_THRESHOLD — warn at 80%

    # Multimodal protocol (Phase 23.1)
    max_image_size_mb: int = 20  # AI__MAX_IMAGE_SIZE_MB
    max_audio_duration_s: int = 300  # AI__MAX_AUDIO_DURATION_S
    supported_image_types: list[str] = [
        "image/png",
        "image/jpeg",
        "image/gif",
        "image/webp",
    ]  # AI__SUPPORTED_IMAGE_TYPES

    # Multimodal agent context (Phase 23.3)
    multimodal_context_enabled: bool = False  # AI__MULTIMODAL_CONTEXT_ENABLED

    # Scaffolder tree mode (Phase 48.7)
    scaffolder_tree_mode: bool = False  # AI__SCAFFOLDER_TREE_MODE
    scaffolder_tree_manifest_budget: int = 8000  # AI__SCAFFOLDER_TREE_MANIFEST_BUDGET (tokens)


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
    # Proactive QA warnings (Phase 48.12)
    proactive_qa_enabled: bool = False  # KNOWLEDGE__PROACTIVE_QA_ENABLED
    proactive_max_warnings: int = 10  # KNOWLEDGE__PROACTIVE_MAX_WARNINGS
    failure_min_occurrences: int = 2  # KNOWLEDGE__FAILURE_MIN_OCCURRENCES


class QAChaosConfig(BaseModel):
    """Chaos testing configuration."""

    enabled: bool = False  # QA_CHAOS__ENABLED
    default_profiles: list[str] = [
        "gmail_style_strip",
        "image_blocked",
        "dark_mode_inversion",
        "gmail_clipping",
    ]  # QA_CHAOS__DEFAULT_PROFILES
    resilience_check_enabled: bool = False  # QA_CHAOS__RESILIENCE_CHECK_ENABLED
    resilience_threshold: float = 0.7  # QA_CHAOS__RESILIENCE_THRESHOLD
    auto_document: bool = False  # QA_CHAOS__AUTO_DOCUMENT


class QAPropertyTestingConfig(BaseModel):
    """Property-based testing configuration."""

    enabled: bool = False  # QA_PROPERTY_TESTING__ENABLED
    default_cases: int = 100  # QA_PROPERTY_TESTING__DEFAULT_CASES
    seed: int | None = None  # QA_PROPERTY_TESTING__SEED (fixed seed for CI)


class QAOutlookAnalyzerConfig(BaseModel):
    """Outlook Word-engine dependency analyzer configuration."""

    enabled: bool = False  # QA_OUTLOOK_ANALYZER__ENABLED
    default_target: str = "dual_support"  # new_outlook | dual_support | audit_only


class QADeliverabilityConfig(BaseModel):
    """Deliverability prediction scoring. Env prefix: QA_DELIVERABILITY__."""

    enabled: bool = False
    threshold: int = 70  # 0-100 score, pass if >= threshold


class SandboxConfig(BaseModel):
    """Headless email sandbox settings."""

    enabled: bool = False
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    mailpit_url: str = "http://localhost:8025"
    roundcube_url: str = "http://localhost:9080"
    playwright_timeout_ms: int = 15000
    from_addr: str = "sandbox@test.local"
    to_addr: str = "inbox@test.local"


class CalibrationConfig(BaseModel):
    """Emulator calibration loop settings."""

    enabled: bool = False
    rate_per_client_per_day: int = 3
    monthly_budget: float = 0.0  # 0 = disabled
    regression_threshold: float = 10.0  # % drop that triggers warning
    ema_alpha: float = 0.3
    max_history: int = 100


class RenderingConfig(BaseModel):
    """Cross-client rendering test settings."""

    provider: str = "litmus"  # litmus, eoa, mock
    litmus_api_key: str = ""
    eoa_api_key: str = ""
    poll_interval_seconds: int = 10
    poll_timeout_seconds: int = 300
    max_concurrent_tests: int = 5
    screenshot_storage_path: str = "data/screenshots"
    screenshots_enabled: bool = False
    screenshot_max_clients: int = 5
    screenshot_timeout_ms: int = 15000
    screenshot_npx_path: str = "npx"
    visual_diff_enabled: bool = False
    visual_diff_threshold: float = 0.01  # 1% pixel diff triggers regression
    visual_regression_threshold: float = 0.5  # % pixel diff that flags regression
    confidence_enabled: bool = True
    sandbox: SandboxConfig = SandboxConfig()
    calibration: CalibrationConfig = CalibrationConfig()
    # Gate settings (Phase 27.3)
    gate_mode: str = "warn"  # enforce | warn | skip
    gate_tier1_threshold: float = 85.0
    gate_tier2_threshold: float = 70.0
    gate_tier3_threshold: float = 60.0


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
    dry_run: bool = True  # Dry run by default until manually verified


class ChangeDetectionConfig(BaseModel):
    """Email client rendering change detection settings."""

    enabled: bool = False  # CHANGE_DETECTION__ENABLED
    interval_hours: int = 168  # Weekly default — CHANGE_DETECTION__INTERVAL_HOURS
    diff_threshold: float = 0.02  # 2% pixel diff = rendering change
    clients: list[str] = [
        "gmail_web",
        "outlook_2019",
        "apple_mail",
        "outlook_dark",
        "mobile_ios",
    ]


class DesignSyncConfig(BaseModel):
    """Design tool sync settings."""

    encryption_key: str = ""  # If empty, derived from jwt_secret_key via PBKDF2
    asset_storage_path: str = "data/design-assets"
    asset_max_width: int = 1200  # Max width for email images; 1200 = 2x retina for 600px containers
    # Penpot integration (self-hosted design tool)
    penpot_enabled: bool = False
    penpot_base_url: str = "http://localhost:9001"
    penpot_request_timeout: float = 30.0
    converter_enabled: bool = True  # DESIGN_SYNC__CONVERTER_ENABLED (provider-agnostic)
    figma_variables_enabled: bool = True  # DESIGN_SYNC__FIGMA_VARIABLES_ENABLED
    opacity_composite_bg: str = "#FFFFFF"  # Background hex for alpha compositing
    ai_layout_enabled: bool = True  # DESIGN_SYNC__AI_LAYOUT_ENABLED
    # Visual fidelity scoring (SSIM comparison of Figma frames vs rendered HTML)
    fidelity_enabled: bool = False  # DESIGN_SYNC__FIDELITY_ENABLED
    fidelity_ssim_window: int = 7  # SSIM Gaussian window (odd, ≤ min image dim)
    fidelity_blur_sigma: float = 1.0  # Gaussian blur before SSIM (anti-aliasing tolerance)
    fidelity_critical_threshold: float = 0.70  # SSIM < 0.70 = critical
    fidelity_warning_threshold: float = 0.85  # SSIM < 0.85 = warning
    fidelity_figma_scale: float = 2.0  # Figma export scale factor
    # W3C Design Tokens & caniemail.com
    w3c_tokens_enabled: bool = True  # DESIGN_SYNC__W3C_TOKENS_ENABLED
    # Figma webhooks (live preview sync)
    figma_webhook_enabled: bool = False  # DESIGN_SYNC__FIGMA_WEBHOOK_ENABLED
    figma_webhook_passcode: str = ""  # DESIGN_SYNC__FIGMA_WEBHOOK_PASSCODE (HMAC secret)
    figma_webhook_callback_url: str = ""  # DESIGN_SYNC__FIGMA_WEBHOOK_CALLBACK_URL
    webhook_debounce_seconds: int = 5  # DESIGN_SYNC__WEBHOOK_DEBOUNCE_SECONDS
    # Section cache (35.10 — incremental conversion)
    section_cache_enabled: bool = True  # DESIGN_SYNC__SECTION_CACHE_ENABLED
    section_cache_memory_max: int = 500  # DESIGN_SYNC__SECTION_CACHE_MEMORY_MAX
    section_cache_redis_ttl: int = 3600  # DESIGN_SYNC__SECTION_CACHE_REDIS_TTL (seconds)
    # MJML import (36.4)
    mjml_import_enabled: bool = True  # DESIGN_SYNC__MJML_IMPORT_ENABLED
    # HTML reverse-engineering import (36.5)
    html_import_ai_enabled: bool = True  # DESIGN_SYNC__HTML_IMPORT_AI_ENABLED
    html_import_max_size_bytes: int = 2_097_152  # DESIGN_SYNC__HTML_IMPORT_MAX_SIZE_BYTES (2 MB)
    # Converter learning loop (Phase 48)
    conversion_memory_enabled: bool = True  # DESIGN_SYNC__CONVERSION_MEMORY_ENABLED
    conversion_traces_enabled: bool = True  # DESIGN_SYNC__CONVERSION_TRACES_ENABLED
    conversion_traces_path: str = (
        "traces/converter_traces.jsonl"  # DESIGN_SYNC__CONVERSION_TRACES_PATH
    )
    low_match_confidence_threshold: float = 0.6  # DESIGN_SYNC__LOW_MATCH_CONFIDENCE_THRESHOLD
    # Adjacent-section background color propagation (Phase 41.2)
    bgcolor_propagation_enabled: bool = True  # DESIGN_SYNC__BGCOLOR_PROPAGATION_ENABLED
    # VLM-assisted section classification fallback (Phase 41.5)
    vlm_fallback_enabled: bool = False  # DESIGN_SYNC__VLM_FALLBACK_ENABLED
    # VLM-assisted section type classification in layout analysis (Phase 41.7)
    vlm_classification_enabled: bool = False  # DESIGN_SYNC__VLM_CLASSIFICATION_ENABLED
    vlm_classification_model: str = (
        ""  # DESIGN_SYNC__VLM_CLASSIFICATION_MODEL (empty = default routing)
    )
    vlm_classification_confidence_threshold: float = (
        0.7  # DESIGN_SYNC__VLM_CLASSIFICATION_CONFIDENCE_THRESHOLD
    )
    vlm_classification_timeout: float = 15.0  # DESIGN_SYNC__VLM_CLASSIFICATION_TIMEOUT (seconds)
    # VLM visual verification loop (Phase 47.2)
    vlm_verify_enabled: bool = False  # DESIGN_SYNC__VLM_VERIFY_ENABLED
    vlm_verify_model: str = ""  # DESIGN_SYNC__VLM_VERIFY_MODEL (empty = auto-resolve vision)
    vlm_verify_timeout: float = 30.0  # DESIGN_SYNC__VLM_VERIFY_TIMEOUT (seconds)
    vlm_verify_diff_skip_threshold: float = 2.0  # DESIGN_SYNC__VLM_VERIFY_DIFF_SKIP_THRESHOLD (%)
    vlm_verify_max_sections: int = 20  # DESIGN_SYNC__VLM_VERIFY_MAX_SECTIONS
    # Verification loop parameters (Phase 47.4)
    vlm_verify_max_iterations: int = 3  # DESIGN_SYNC__VLM_VERIFY_MAX_ITERATIONS
    vlm_verify_target_fidelity: float = 0.97  # DESIGN_SYNC__VLM_VERIFY_TARGET_FIDELITY
    vlm_verify_confidence_threshold: float = 0.7  # DESIGN_SYNC__VLM_VERIFY_CONFIDENCE_THRESHOLD
    # Pipeline integration (Phase 47.5)
    vlm_verify_correction_confidence: float = 0.6  # DESIGN_SYNC__VLM_VERIFY_CORRECTION_CONFIDENCE
    vlm_verify_client: str = "gmail_web"  # DESIGN_SYNC__VLM_VERIFY_CLIENT (rendering target)
    # Custom component generation via Scaffolder for low-confidence matches (Phase 47.8)
    custom_component_enabled: bool = False  # DESIGN_SYNC__CUSTOM_COMPONENT_ENABLED
    custom_component_confidence_threshold: float = (
        # Raised from 0.6 → 0.85 because observed matcher scores are 0.85+ for
        # every real case, so the previous default guaranteed the AI fallback
        # never fired even with custom_component_enabled=true.
        0.85  # DESIGN_SYNC__CUSTOM_COMPONENT_CONFIDENCE_THRESHOLD
    )
    custom_component_model: str = ""  # DESIGN_SYNC__CUSTOM_COMPONENT_MODEL (empty = default)
    custom_component_max_per_email: int = 3  # DESIGN_SYNC__CUSTOM_COMPONENT_MAX_PER_EMAIL
    # Data-driven converter regression (Phase 49.9)
    regression_dir: str = "data/debug"  # DESIGN_SYNC__REGRESSION_DIR
    regression_strict: bool = False  # DESIGN_SYNC__REGRESSION_STRICT
    # Sibling pattern detection — repeated-content grouping (Phase 49.1)
    sibling_detection_enabled: bool = True  # DESIGN_SYNC__SIBLING_DETECTION_ENABLED
    sibling_min_group: int = 2  # DESIGN_SYNC__SIBLING_MIN_GROUP
    sibling_similarity_threshold: float = 0.8  # DESIGN_SYNC__SIBLING_SIMILARITY_THRESHOLD
    # Per-email token scoping — scope to target frame subtree (Phase 49.6)
    token_scoping_enabled: bool = True  # DESIGN_SYNC__TOKEN_SCOPING_ENABLED
    # Design-sync → EmailTree bridge (Phase 49.8)
    tree_bridge_enabled: bool = False  # DESIGN_SYNC__TREE_BRIDGE_ENABLED


class ESPSyncConfig(BaseModel):
    """ESP bidirectional sync settings — base URLs for mock or production ESPs."""

    braze_base_url: str = "http://mock-esp:3002/braze"
    sfmc_base_url: str = "http://mock-esp:3002/sfmc"
    adobe_base_url: str = "http://mock-esp:3002/adobe"
    taxi_base_url: str = "http://mock-esp:3002/taxi"
    klaviyo_base_url: str = "http://mock-esp:3002/klaviyo"
    hubspot_base_url: str = "http://mock-esp:3002/hubspot"
    mailchimp_base_url: str = "http://mock-esp:3002/mailchimp"
    sendgrid_base_url: str = "http://mock-esp:3002/sendgrid"
    activecampaign_base_url: str = "http://mock-esp:3002/activecampaign"
    iterable_base_url: str = "http://mock-esp:3002/iterable"
    brevo_base_url: str = "http://mock-esp:3002/brevo"


class QAGmailPredictorConfig(BaseModel):
    """Gmail AI summary prediction configuration."""

    enabled: bool = False
    model: str = "gpt-4o-mini"
    api_base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    max_html_chars: int = 8000
    timeout_seconds: float = 30.0


class QABIMIConfig(BaseModel):
    """BIMI readiness check configuration."""

    enabled: bool = False  # QA_BIMI__ENABLED
    svg_fetch_timeout_seconds: float = 10.0  # QA_BIMI__SVG_FETCH_TIMEOUT_SECONDS
    svg_max_size_bytes: int = 32_768  # QA_BIMI__SVG_MAX_SIZE_BYTES (32KB)
    dns_timeout_seconds: float = 5.0  # QA_BIMI__DNS_TIMEOUT_SECONDS


class QASyntheticConfig(BaseModel):
    """Synthetic adversarial email generator configuration."""

    count_per_check: int = 5  # QA_SYNTHETIC__COUNT_PER_CHECK
    output_dir: str = "data/synthetic-adversarial"  # QA_SYNTHETIC__OUTPUT_DIR


class QAMetaEvalConfig(BaseModel):
    """QA check meta-evaluation configuration."""

    enabled: bool = True  # QA_META_EVAL__ENABLED
    fp_threshold: float = 0.10  # QA_META_EVAL__FP_THRESHOLD
    fn_threshold: float = 0.05  # QA_META_EVAL__FN_THRESHOLD


class VoiceConfig(BaseModel):
    """Voice brief input pipeline settings."""

    enabled: bool = False  # VOICE__ENABLED — master toggle
    transcriber: str = "whisper_api"  # VOICE__TRANSCRIBER — "whisper_api" or "whisper_local"
    whisper_model: str = "whisper-1"  # VOICE__WHISPER_MODEL — API model name
    whisper_local_model: str = "base"  # VOICE__WHISPER_LOCAL_MODEL — local model size
    extraction_model: str = ""  # VOICE__EXTRACTION_MODEL — empty = use default AI model
    max_duration_s: int = 300  # VOICE__MAX_DURATION_S — 5 min max
    max_file_size_mb: int = 25  # VOICE__MAX_FILE_SIZE_MB
    confidence_threshold: float = 0.7  # VOICE__CONFIDENCE_THRESHOLD — below = raw transcript
    rate_limit_transcribe: str = "5/minute"  # VOICE__RATE_LIMIT_TRANSCRIBE
    rate_limit_brief: str = "3/minute"  # VOICE__RATE_LIMIT_BRIEF
    rate_limit_run: str = "2/minute"  # VOICE__RATE_LIMIT_RUN


class MCPConfig(BaseModel):
    """MCP (Model Context Protocol) server settings."""

    enabled: bool = False  # MCP__ENABLED
    max_response_tokens: int = 4000  # MCP__MAX_RESPONSE_TOKENS — truncate responses beyond this
    tool_timeout_s: int = 120  # MCP__TOOL_TIMEOUT_S
    audit_log_enabled: bool = True  # MCP__AUDIT_LOG_ENABLED
    # Tool allowlist — empty means all tools exposed
    # Operators can restrict to e.g. ["qa_*", "knowledge_*"]
    tool_allowlist: list[str] = []  # MCP__TOOL_ALLOWLIST
    cache_enabled: bool = True  # MCP__CACHE_ENABLED — in-memory response cache
    cache_max_size: int = 100  # MCP__CACHE_MAX_SIZE — max cached responses
    cache_ttl: int = 300  # MCP__CACHE_TTL — seconds before cache entries expire
    compress_schemas: bool = True  # MCP__COMPRESS_SCHEMAS — strip verbose schema fields


class EmailEngineConfig(BaseModel):
    """Email engine settings."""

    css_compiler_enabled: bool = False  # EMAIL_ENGINE__CSS_COMPILER_ENABLED
    css_compiler_target_clients: list[str] = [
        "gmail_web",
        "outlook_2019",
        "apple_mail",
        "yahoo_mail",
    ]  # EMAIL_ENGINE__CSS_COMPILER_TARGET_CLIENTS
    schema_injection_enabled: bool = False  # EMAIL_ENGINE__SCHEMA_INJECTION_ENABLED
    schema_injection_types: list[str] = [  # EMAIL_ENGINE__SCHEMA_INJECTION_TYPES
        "promotional",
        "transactional",
        "event",
    ]


class CorrectionTrackerConfig(BaseModel):
    """Correction pattern tracking settings (Phase 35.7)."""

    enabled: bool = False
    min_occurrences: int = 5
    min_confidence: float = 0.9
    max_log_entries: int = 10_000


class BlueprintConfig(BaseModel):
    """Blueprint execution settings."""

    daily_token_cap: int = 500_000  # Max tokens per user per day across all blueprint runs
    judge_on_retry: bool = False  # When True, run LLM judge on recovery retries (iteration > 0)
    checkpoints_enabled: bool = False  # Opt-in checkpoint persistence (backward compatible)
    checkpoint_retention_days: int = 7  # Auto-cleanup age limit for old checkpoints
    recovery_ledger_enabled: bool = False  # Adaptive recovery routing from outcome history
    correction_examples_enabled: bool = False  # Few-shot correction examples on retries
    judge_aggregation_enabled: bool = False  # Judge verdict aggregation → prompt patching
    confidence_calibration_enabled: bool = False  # Per-agent confidence calibration
    insight_propagation_enabled: bool = False  # Cross-agent insight propagation
    visual_qa_precheck: bool = False  # Pre-QA visual defect detection via VLM screenshots
    visual_comparison: bool = False  # Post-build screenshot comparison vs original design
    visual_comparison_threshold: float = 5.0  # Pixel diff % threshold for drift warning
    visual_precheck_top_clients: int = 3  # Number of clients to render for precheck


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


class CollabWebSocketConfig(BaseModel):
    """Collaboration WebSocket settings."""

    enabled: bool = False
    max_connections_per_room: int = 20
    max_rooms_per_user: int = 10
    heartbeat_interval_seconds: int = 30
    auth_timeout_seconds: int = 10
    max_message_bytes: int = 1_048_576  # 1 MB
    # CRDT settings (Phase 24.2)
    crdt_enabled: bool = False
    crdt_compaction_threshold: int = 100  # compact after N updates
    crdt_compaction_interval_s: int = 300  # or after N seconds
    crdt_max_document_size_mb: int = 5  # reject updates beyond this


class TolgeeConfig(BaseModel):
    """Tolgee TMS integration settings."""

    enabled: bool = False  # TOLGEE__ENABLED
    base_url: str = "http://localhost:25432"  # TOLGEE__BASE_URL
    default_locale: str = "en"  # TOLGEE__DEFAULT_LOCALE
    max_locales_per_build: int = 20  # TOLGEE__MAX_LOCALES_PER_BUILD
    request_timeout: float = 30.0  # TOLGEE__REQUEST_TIMEOUT


class KestraConfig(BaseModel):
    """Kestra workflow orchestration settings."""

    enabled: bool = False  # KESTRA__ENABLED
    api_url: str = "http://localhost:8080"  # KESTRA__API_URL
    api_token: str = ""  # KESTRA__API_TOKEN
    namespace: str = "merkle-email-hub"  # KESTRA__NAMESPACE
    default_retry_attempts: int = 3  # KESTRA__DEFAULT_RETRY_ATTEMPTS
    default_retry_backoff_s: int = 30  # KESTRA__DEFAULT_RETRY_BACKOFF_S
    request_timeout_s: float = 30.0  # KESTRA__REQUEST_TIMEOUT_S


class ReportingConfig(BaseModel):
    """Typst PDF report generation settings."""

    enabled: bool = False  # REPORTING__ENABLED
    typst_binary: str = "typst"  # REPORTING__TYPST_BINARY
    cache_ttl_h: int = 24  # REPORTING__CACHE_TTL_H
    max_report_size_mb: int = 50  # REPORTING__MAX_REPORT_SIZE_MB
    compilation_timeout_s: int = 10  # REPORTING__COMPILATION_TIMEOUT_S


class PluginsConfig(BaseModel):
    """Plugin architecture settings."""

    enabled: bool = False  # PLUGINS__ENABLED
    directory: str = "plugins/"  # PLUGINS__DIRECTORY
    hot_reload: bool = False  # PLUGINS__HOT_RELOAD
    default_timeout_s: int = 30  # PLUGINS__DEFAULT_TIMEOUT_S
    health_check_interval_s: int = 60  # PLUGINS__HEALTH_CHECK_INTERVAL_S
    max_consecutive_failures: int = 3  # PLUGINS__MAX_CONSECUTIVE_FAILURES


class SkillExtractionConfig(BaseModel):
    """Configuration for automatic skill extraction from templates."""

    enabled: bool = False  # SKILL_EXTRACTION__ENABLED
    min_confidence: float = 0.7  # Only extract patterns with >= this confidence
    max_amendments_per_upload: int = 20  # Cap to prevent skill file spam
    auto_eval_after_apply: bool = True  # Trigger eval run after amendment applied


class TemplatesUploadConfig(BaseModel):
    """Template upload pipeline settings."""

    upload_enabled: bool = False  # TEMPLATES__UPLOAD_ENABLED
    max_file_size_bytes: int = 2 * 1024 * 1024  # TEMPLATES__MAX_FILE_SIZE_BYTES (2MB)
    max_uploads_per_hour: int = 5  # TEMPLATES__MAX_UPLOADS_PER_HOUR
    auto_knowledge_inject: bool = True  # TEMPLATES__AUTO_KNOWLEDGE_INJECT
    auto_eval_generate: bool = True  # TEMPLATES__AUTO_EVAL_GENERATE
    import_images: bool = True  # TEMPLATES__IMPORT_IMAGES
    max_image_download_size: int = 5 * 1024 * 1024  # 5MB per image
    max_images_per_template: int = 50
    image_download_timeout: float = 5.0  # Per-image timeout
    image_storage_path: str = "data/upload-assets"


class BriefsConfig(BaseModel):
    """Brief connection settings."""

    enabled: bool = True
    sync_timeout: float = 30.0  # HTTP timeout for platform API calls
    max_items_per_sync: int = 500  # Safety cap on items fetched per sync
    provider_base_urls: dict[
        str, str
    ] = {}  # Override API URLs, e.g. {"asana": "http://localhost:3002/briefs/asana"}


class VariantsConfig(BaseModel):
    """Multi-variant campaign assembly settings."""

    enabled: bool = False
    max_variants: int = 5
    rate_limit_per_hour: int = 3


class ProgressConfig(BaseModel):
    """Progress tracking settings."""

    max_retention_seconds: int = 300
    cleanup_interval_seconds: int = 60


class ExportConfig(BaseModel):
    """Export pipeline gate settings."""

    qa_gate_mode: str = "warn"  # enforce | warn | skip
    qa_blocking_checks: list[str] = Field(
        default_factory=lambda: [
            "html_validation",
            "link_validation",
            "spam_score",
            "personalisation_syntax",
            "liquid_syntax",
        ]
    )
    qa_warning_checks: list[str] = Field(
        default_factory=lambda: [
            "accessibility",
            "dark_mode",
            "image_optimization",
            "file_size",
        ]
    )


class SchedulingConfig(BaseModel):
    """Cron scheduling engine settings."""

    enabled: bool = False  # SCHEDULING__ENABLED
    check_interval_seconds: int = 60  # SCHEDULING__CHECK_INTERVAL_SECONDS
    job_timeout_seconds: int = 3600  # SCHEDULING__JOB_TIMEOUT_SECONDS
    max_run_history: int = 100  # SCHEDULING__MAX_RUN_HISTORY
    run_history_ttl_seconds: int = 86400  # SCHEDULING__RUN_HISTORY_TTL_SECONDS
    qa_sweep_regression_threshold: float = Field(
        default=0.05,
        description="Score drop threshold (fraction) to flag as regression",
    )
    qa_sweep_checks: list[str] = Field(
        default=["html_validation", "css_support", "css_audit"],
        description="QA checks to run during sweeps",
    )


class NotificationsConfig(BaseModel):
    """Notification channel settings."""

    enabled: bool = False  # NOTIFICATIONS__ENABLED
    default_severity: str = "warning"  # NOTIFICATIONS__DEFAULT_SEVERITY

    # Slack
    slack_enabled: bool = False  # NOTIFICATIONS__SLACK_ENABLED
    slack_webhook_url: str = ""  # NOTIFICATIONS__SLACK_WEBHOOK_URL
    slack_timeout: float = 30.0  # NOTIFICATIONS__SLACK_TIMEOUT

    # Teams
    teams_enabled: bool = False  # NOTIFICATIONS__TEAMS_ENABLED
    teams_webhook_url: str = ""  # NOTIFICATIONS__TEAMS_WEBHOOK_URL
    teams_timeout: float = 30.0  # NOTIFICATIONS__TEAMS_TIMEOUT

    # Email
    email_enabled: bool = False  # NOTIFICATIONS__EMAIL_ENABLED
    email_smtp_host: str = ""  # NOTIFICATIONS__EMAIL_SMTP_HOST
    email_smtp_port: int = 587  # NOTIFICATIONS__EMAIL_SMTP_PORT
    email_from_addr: str = "noreply@email-hub.local"  # NOTIFICATIONS__EMAIL_FROM_ADDR
    email_to_addrs: list[str] = []  # NOTIFICATIONS__EMAIL_TO_ADDRS


class SecurityConfig(BaseModel):
    """Security settings including prompt injection detection."""

    prompt_guard_enabled: bool = True  # SECURITY__PROMPT_GUARD_ENABLED
    prompt_guard_mode: Literal["warn", "strip", "block"] = "warn"  # SECURITY__PROMPT_GUARD_MODE

    # G3 — kill switch: agents in this list short-circuit with 503 on every call.
    # Env: SECURITY__DISABLED_AGENTS=scaffolder,dark_mode
    disabled_agents: list[str] = Field(default_factory=list)

    # G4 — per-run hard caps (defense-in-depth on top of provider timeouts)
    agent_max_run_seconds: int = 90  # SECURITY__AGENT_MAX_RUN_SECONDS
    agent_max_total_tokens: int = 32000  # SECURITY__AGENT_MAX_TOTAL_TOKENS


class DebounceConfig(BaseModel):
    """Distributed debounce settings."""

    enabled: bool = True  # DEBOUNCE__ENABLED
    default_window_ms: int = Field(default=2000, ge=100, le=30000)
    figma_webhook_window_ms: int = 3000  # DEBOUNCE__FIGMA_WEBHOOK_WINDOW_MS
    qa_trigger_window_ms: int = 2000  # DEBOUNCE__QA_TRIGGER_WINDOW_MS
    rendering_trigger_window_ms: int = 2000  # DEBOUNCE__RENDERING_TRIGGER_WINDOW_MS


class CredentialsConfig(BaseModel):
    """Credential pool rotation and cooldown settings."""

    enabled: bool = False  # CREDENTIALS__ENABLED
    cooldown_initial_seconds: int = 30  # CREDENTIALS__COOLDOWN_INITIAL_SECONDS
    cooldown_max_seconds: int = 300  # CREDENTIALS__COOLDOWN_MAX_SECONDS
    failure_threshold: int = 3  # CREDENTIALS__FAILURE_THRESHOLD
    unhealthy_ttl_seconds: int = 3600  # CREDENTIALS__UNHEALTHY_TTL_SECONDS
    pools: dict[str, list[str]] = Field(
        default_factory=dict,
        description="service name -> list of API keys",
    )  # CREDENTIALS__POOLS (JSON via env)


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
