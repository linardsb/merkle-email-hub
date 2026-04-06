"""Typed artifact protocol for inter-agent data flow.

Provides immutable artifact types and an in-memory store with optional
Redis persistence for pipeline run state.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, TypeVar

from app.core.exceptions import ArtifactNotFoundError, ArtifactTypeError
from app.core.logging import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from redis.asyncio import Redis

    from app.ai.agents.schemas.build_plan import DesignTokens, EmailBuildPlan
    from app.design_sync.visual_verify import SectionCorrection
    from app.qa_engine.schemas import QACheckResult

__all__ = [
    "Artifact",
    "ArtifactStore",
    "BuildPlanArtifact",
    "CorrectionArtifact",
    "DesignTokenArtifact",
    "EvalArtifact",
    "HtmlArtifact",
    "QaResultArtifact",
    "ScreenshotArtifact",
]

T = TypeVar("T", bound="Artifact")


# ── Base ──


@dataclass(frozen=True)
class Artifact:
    """Base artifact type. All artifacts are immutable."""

    name: str
    produced_by: str
    produced_at: datetime
    schema_version: str = "1"


# ── Concrete Types ──


@dataclass(frozen=True)
class HtmlArtifact(Artifact):
    """HTML content artifact."""

    html: str = ""
    sections: tuple[str, ...] = ()


@dataclass(frozen=True)
class BuildPlanArtifact(Artifact):
    """Email build plan artifact."""

    plan: EmailBuildPlan | None = None


@dataclass(frozen=True)
class QaResultArtifact(Artifact):
    """QA check results artifact."""

    results: tuple[QACheckResult, ...] = ()
    passed: bool = True
    score: float = 1.0


@dataclass(frozen=True)
class CorrectionArtifact(Artifact):
    """Visual verification corrections artifact."""

    corrections: tuple[SectionCorrection, ...] = ()
    applied: int = 0
    skipped: int = 0


@dataclass(frozen=True)
class DesignTokenArtifact(Artifact):
    """Design tokens artifact."""

    tokens: DesignTokens | None = None


@dataclass(frozen=True)
class ScreenshotArtifact(Artifact):
    """Screenshot data artifact."""

    screenshots: dict[str, bytes] = field(default_factory=lambda: dict[str, bytes]())


@dataclass(frozen=True)
class EvalArtifact(Artifact):
    """Eval judge verdict artifact."""

    verdict: str = ""
    feedback: str = ""
    score: float = 0.0


# ── Store ──


class ArtifactStore:
    """In-memory artifact store for a single pipeline run."""

    def __init__(self) -> None:
        self._store: dict[str, Artifact] = {}

    def put(self, name: str, artifact: Artifact) -> None:
        """Store an artifact, overwriting any existing one with the same name."""
        self._store[name] = artifact

    def get(self, name: str, expected_type: type[T]) -> T:
        """Retrieve an artifact by name with type checking.

        Raises:
            ArtifactNotFoundError: If no artifact with the given name exists.
            ArtifactTypeError: If the artifact is not of the expected type.
        """
        artifact = self._store.get(name)
        if artifact is None:
            raise ArtifactNotFoundError(name)
        if not isinstance(artifact, expected_type):
            raise ArtifactTypeError(name, expected_type.__name__, type(artifact).__name__)
        return artifact

    def get_optional(self, name: str, expected_type: type[T]) -> T | None:
        """Retrieve an artifact if it exists and matches the expected type."""
        artifact = self._store.get(name)
        if artifact is None:
            return None
        if not isinstance(artifact, expected_type):
            return None
        return artifact

    def has(self, name: str) -> bool:
        """Check whether an artifact with the given name exists."""
        return name in self._store

    def names(self) -> frozenset[str]:
        """Return all stored artifact names."""
        return frozenset(self._store)

    def snapshot(self) -> dict[str, str]:
        """Return a name → type mapping of all stored artifacts."""
        return {k: type(v).__name__ for k, v in self._store.items()}

    # ── Optional Redis Persistence ──

    async def persist(self, run_id: str, redis: Redis) -> None:
        """Persist artifact snapshot metadata to Redis."""
        data = json.dumps(self.snapshot())
        await redis.set(f"artifact:{run_id}", data, ex=86400)
        logger.debug(
            "artifacts.persist_completed",
            extra={"run_id": run_id, "artifact_count": len(self._store)},
        )

    @classmethod
    async def restore(cls, run_id: str, redis: Redis) -> dict[str, str]:
        """Load artifact snapshot metadata from Redis.

        Returns name → type mapping. Full typed restore requires
        per-type deserializers (deferred to future phase).
        """
        raw = await redis.get(f"artifact:{run_id}")
        if raw is None:
            logger.debug("artifacts.restore_empty", extra={"run_id": run_id})
            return {}
        result: dict[str, str] = json.loads(raw)
        logger.debug(
            "artifacts.restore_completed",
            extra={"run_id": run_id, "artifact_count": len(result)},
        )
        return result
