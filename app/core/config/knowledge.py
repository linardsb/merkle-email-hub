"""Knowledge base / RAG / memory / cognee settings."""

from pydantic import BaseModel


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
