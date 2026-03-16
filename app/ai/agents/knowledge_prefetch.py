"""Knowledge graph pre-query for agent context enrichment.

Before generating from scratch, queries the Cognee knowledge graph for
similar past outcomes. If a similar template was built for this client
before, the agent starts from that baseline instead of zero.

Prefetch is advisory only — agents can ignore prior work if the task differs.
Results are filtered by project_id to prevent cross-tenant leakage.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

from app.ai.blueprints.protocols import GraphContextProvider
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class PrefetchResult:
    """A single prior outcome retrieved from the knowledge graph."""

    summary: str
    agent_type: str
    score: float
    source_run_id: str = ""


def build_prefetch_query(agent_name: str, brief: str, project_id: int | None) -> str:
    """Build a search query combining agent type + task description + project scope.

    The query is structured to find past outcomes for the same agent type
    that match the current task brief within the same project/org.
    """
    parts = [f"agent:{agent_name}", f"task:{brief[:500]}"]
    if project_id is not None:
        parts.append(f"project:{project_id}")
    return " ".join(parts)


def _cache_key(agent_name: str, brief_hash: str, project_id: int | None) -> str:
    """Build Redis cache key. Includes project_id for tenant isolation."""
    pid = project_id or "global"
    return f"prefetch:{agent_name}:{pid}:{brief_hash}"


async def prefetch_prior_outcomes(
    *,
    agent_name: str,
    brief: str,
    project_id: int | None,
    graph_provider: GraphContextProvider,
    top_k: int = 3,
    min_score: float = 0.3,
    cache_ttl: int = 300,
) -> list[PrefetchResult]:
    """Query knowledge graph for similar past agent outcomes.

    Args:
        agent_name: The agent type (e.g. "scaffolder", "dark_mode").
        brief: The current task description/brief.
        project_id: Project ID for tenant isolation (None = global).
        graph_provider: GraphContextProvider with search() method.
        top_k: Maximum results to return.
        min_score: Minimum similarity score threshold.
        cache_ttl: Redis cache TTL in seconds.

    Returns:
        List of PrefetchResult ordered by relevance score (descending).
        Empty list on errors (failure-safe).
    """
    brief_hash = hashlib.sha256(brief.encode()).hexdigest()[:16]
    cache_k = _cache_key(agent_name, brief_hash, project_id)

    # Check Redis cache first
    cached = await _get_cached(cache_k)
    if cached is not None:
        logger.debug(
            "knowledge_prefetch.cache_hit",
            agent=agent_name,
            project_id=project_id,
            result_count=len(cached),
        )
        return cached

    # Query knowledge graph
    query = build_prefetch_query(agent_name, brief, project_id)

    try:
        results = await graph_provider.search(query, top_k=top_k)
    except Exception:
        logger.debug(
            "knowledge_prefetch.graph_search_failed",
            agent=agent_name,
            project_id=project_id,
            exc_info=True,
        )
        return []

    # Filter by min score and map to PrefetchResult
    prefetch_results: list[PrefetchResult] = []
    for r in results:
        if r.score < min_score:
            continue
        prefetch_results.append(
            PrefetchResult(
                summary=r.content[:1000],  # Cap summary length
                agent_type=agent_name,
                score=r.score,
            )
        )

    prefetch_results = prefetch_results[:top_k]

    # Cache in Redis (fire-and-forget)
    await _set_cached(cache_k, prefetch_results, ttl=cache_ttl)

    logger.info(
        "knowledge_prefetch.completed",
        agent=agent_name,
        project_id=project_id,
        results_found=len(results),
        results_above_threshold=len(prefetch_results),
    )

    return prefetch_results


async def _get_cached(key: str) -> list[PrefetchResult] | None:
    """Read prefetch results from Redis cache. Returns None on miss or error."""
    try:
        from app.core.redis import get_redis

        redis = await get_redis()
        raw = await redis.get(key)
        if raw is None:
            return None
        data = json.loads(raw)
        return [PrefetchResult(**item) for item in data]
    except Exception:
        logger.debug("knowledge_prefetch.cache_read_failed", key=key, exc_info=True)
        return None


async def _set_cached(key: str, results: list[PrefetchResult], *, ttl: int) -> None:
    """Write prefetch results to Redis cache. Fire-and-forget."""
    try:
        from app.core.redis import get_redis

        redis = await get_redis()
        data = json.dumps([asdict(r) for r in results])
        await redis.set(key, data, ex=ttl)
    except Exception:
        logger.debug("knowledge_prefetch.cache_write_failed", key=key, exc_info=True)


def format_prefetch_context(results: list[PrefetchResult]) -> str:
    """Format prefetch results as an agent-readable context block.

    Injected into the agent's context as advisory reference material.
    """
    if not results:
        return ""

    lines = [
        "## Prior Work Reference (Advisory)",
        "Similar tasks were completed previously. Use as reference — adapt, don't copy.",
        "",
    ]
    for i, r in enumerate(results, 1):
        lines.append(f"### Reference {i} (similarity: {r.score:.2f})")
        lines.append(r.summary)
        lines.append("")

    return "\n".join(lines)
