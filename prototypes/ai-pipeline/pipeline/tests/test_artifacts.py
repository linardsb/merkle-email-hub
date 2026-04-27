"""Tests for ArtifactStore and concrete artifact types."""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from app.ai.pipeline.artifacts import (
    Artifact,
    ArtifactStore,
    BuildPlanArtifact,
    EvalArtifact,
    HtmlArtifact,
)
from app.core.exceptions import ArtifactNotFoundError, ArtifactTypeError

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _html_artifact(html: str = "<table></table>") -> HtmlArtifact:
    return HtmlArtifact(name="html", produced_by="test", produced_at=NOW, html=html)


# ── Core Store Tests ──


class TestArtifactStore:
    def test_put_and_get(self) -> None:
        store = ArtifactStore()
        art = _html_artifact()
        store.put("html", art)
        result = store.get("html", HtmlArtifact)
        assert result is art
        assert result.html == "<table></table>"

    def test_get_wrong_type_raises(self) -> None:
        store = ArtifactStore()
        store.put("html", _html_artifact())
        with pytest.raises(ArtifactTypeError, match="expected BuildPlanArtifact"):
            store.get("html", BuildPlanArtifact)

    def test_get_missing_raises(self) -> None:
        store = ArtifactStore()
        with pytest.raises(ArtifactNotFoundError, match="nonexistent"):
            store.get("nonexistent", HtmlArtifact)

    def test_get_optional_missing(self) -> None:
        store = ArtifactStore()
        assert store.get_optional("nope", HtmlArtifact) is None

    def test_get_optional_wrong_type(self) -> None:
        store = ArtifactStore()
        store.put("html", _html_artifact())
        assert store.get_optional("html", BuildPlanArtifact) is None

    def test_has(self) -> None:
        store = ArtifactStore()
        assert not store.has("html")
        store.put("html", _html_artifact())
        assert store.has("html")

    def test_names(self) -> None:
        store = ArtifactStore()
        store.put("html", _html_artifact())
        store.put("eval", EvalArtifact(name="eval", produced_by="judge", produced_at=NOW))
        assert store.names() == frozenset({"html", "eval"})

    def test_snapshot(self) -> None:
        store = ArtifactStore()
        store.put("html", _html_artifact())
        snap = store.snapshot()
        assert snap == {"html": "HtmlArtifact"}

    def test_overwrite(self) -> None:
        store = ArtifactStore()
        store.put("html", _html_artifact("<v1>"))
        store.put("html", _html_artifact("<v2>"))
        assert store.get("html", HtmlArtifact).html == "<v2>"


# ── Frozen Immutability ──


class TestFrozenArtifacts:
    def test_frozen_artifacts(self) -> None:
        art = _html_artifact()
        with pytest.raises(AttributeError):
            art.html = "mutated"  # type: ignore[misc]

    def test_frozen_base(self) -> None:
        art = Artifact(name="x", produced_by="test", produced_at=NOW)
        with pytest.raises(AttributeError):
            art.name = "y"  # type: ignore[misc]


# ── Redis Persistence ──


class TestRedisPersistence:
    @pytest.mark.asyncio
    async def test_persist_snapshot(self) -> None:
        store = ArtifactStore()
        store.put("html", _html_artifact())
        redis = AsyncMock()
        await store.persist("run-1", redis)
        redis.set.assert_called_once()
        key, data = redis.set.call_args.args[:2]
        assert key == "artifact:run-1"
        assert json.loads(data) == {"html": "HtmlArtifact"}

    @pytest.mark.asyncio
    async def test_restore_snapshot(self) -> None:
        redis = AsyncMock()
        redis.get.return_value = json.dumps({"html": "HtmlArtifact"})
        result = await ArtifactStore.restore("run-1", redis)
        assert result == {"html": "HtmlArtifact"}
        redis.get.assert_called_once_with("artifact:run-1")

    @pytest.mark.asyncio
    async def test_restore_missing(self) -> None:
        redis = AsyncMock()
        redis.get.return_value = None
        result = await ArtifactStore.restore("run-404", redis)
        assert result == {}
