# pyright: reportMissingImports=false, reportUnknownMemberType=false
"""Apply Hub settings to Cognee configuration."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.core.config import CogneeConfig, Settings

logger = get_logger(__name__)


def apply_cognee_config(settings: Settings) -> None:
    """Push Hub settings into Cognee's global configuration.

    Cognee uses module-level config singletons — this function
    bridges our nested Pydantic settings into Cognee's API.
    """
    import cognee

    cfg: CogneeConfig = settings.cognee

    # LLM — inherit from AI config if not explicitly set
    llm_provider = cfg.llm_provider or settings.ai.provider
    llm_model = cfg.llm_model or settings.ai.model
    llm_api_key = cfg.llm_api_key or settings.ai.api_key or ""

    cognee.config.set_llm_config(
        {
            "llm_provider": llm_provider,
            "llm_model": llm_model,
            "llm_api_key": llm_api_key,
        }
    )

    # Graph DB
    cognee.config.set_graph_database_provider(cfg.graph_db_provider)
    if cfg.graph_db_provider == "neo4j" and cfg.neo4j_url:
        # Neo4j requires additional env vars — Cognee reads these internally
        os.environ.setdefault("NEO4J_URI", cfg.neo4j_url)
        os.environ.setdefault("NEO4J_USER", cfg.neo4j_user)
        os.environ.setdefault("NEO4J_PASSWORD", cfg.neo4j_password)

    # Vector DB — reuse existing pgvector if configured
    if cfg.vector_db_provider == "pgvector":
        cognee.config.set_vector_db_config(
            {
                "vector_db_provider": "pgvector",
                "vector_db_url": settings.database.url,
            }
        )

    # Storage directories
    cognee.config.system_root_directory(cfg.system_directory)
    cognee.config.data_root_directory(cfg.data_directory)

    logger.info(
        "knowledge.graph.config_applied",
        graph_db=cfg.graph_db_provider,
        llm_provider=llm_provider,
        vector_db=cfg.vector_db_provider,
    )
