"""Background memory compaction and decay poller."""

from app.core.config import get_settings
from app.core.database import get_db_context
from app.core.logging import get_logger
from app.core.poller import DataPoller
from app.knowledge.embedding import get_embedding_provider
from app.memory.service import MemoryService

logger = get_logger(__name__)
settings = get_settings()


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
