"""Background memory compaction and decay poller."""

from __future__ import annotations

from app.core.config import get_settings
from app.core.database import get_db_context
from app.core.logging import get_logger
from app.core.poller import DataPoller
from app.knowledge.embedding import get_embedding_provider
from app.memory.service import MemoryService

logger = get_logger(__name__)
settings = get_settings()


async def judge_functional_equivalence(memory_a: str, memory_b: str) -> bool:
    """Use lightweight LLM to confirm two memories are functionally equivalent.

    Returns True if they encode the same intent/knowledge, False otherwise.
    Failure-safe: returns False on any error (never merge on uncertainty).
    """
    prompt = (
        "You are comparing two agent memory entries. Determine if they encode "
        "the same knowledge or intent, even if worded differently.\n\n"
        f"Memory A: {memory_a[:500]}\n\n"
        f"Memory B: {memory_b[:500]}\n\n"
        "Are these functionally equivalent (same knowledge/intent)? "
        "Reply with exactly 'YES' or 'NO'."
    )

    try:
        from app.ai.providers.registry import get_registry  # type: ignore[import-not-found]
        from app.ai.providers.types import Message  # type: ignore[import-not-found]
        from app.ai.utils import resolve_model  # type: ignore[import-not-found]

        ai_settings = get_settings()
        registry = get_registry()
        provider = registry.get_llm(ai_settings.ai.provider)
        model = resolve_model("lightweight")

        response = await provider.complete(
            [Message(role="user", content=prompt)],
            temperature=0.0,
            model=model,
        )
        answer: str = response.content.strip().upper()
        return bool(answer.startswith("YES"))
    except Exception:
        logger.warning(
            "memory.intent_judge_failed",
            memory_a_preview=memory_a[:80],
            memory_b_preview=memory_b[:80],
            exc_info=True,
        )
        return False


class MemoryCompactionPoller(DataPoller):
    """Periodically applies decay weights and compacts redundant memories."""

    def __init__(self) -> None:
        super().__init__(
            name="memory-compaction",
            interval_seconds=settings.memory.compaction_interval_hours * 3600,
        )

    async def fetch(self) -> object:
        """Run compaction cycle."""
        async with get_db_context() as db:
            provider = get_embedding_provider(settings)
            service = MemoryService(db, provider)
            stats = await service.run_compaction()
            return stats

    async def store(self, data: object) -> None:
        """Log compaction results."""
        logger.info("memory.compaction.cycle_completed", stats=str(data))
