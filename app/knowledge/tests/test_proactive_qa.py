"""Tests for proactive QA warning extraction, querying, and pipeline integration."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.knowledge.proactive_qa import (
    FailureExtractor,
    ProactiveWarning,
    ProactiveWarningInjector,
    _score_to_severity,
)

# ── Fixtures & Factories ──


def _make_settings(
    *,
    proactive_qa_enabled: bool = True,
    proactive_max_warnings: int = 10,
    failure_min_occurrences: int = 2,
) -> MagicMock:
    settings = MagicMock()
    settings.knowledge.proactive_qa_enabled = proactive_qa_enabled
    settings.knowledge.proactive_max_warnings = proactive_max_warnings
    settings.knowledge.failure_min_occurrences = failure_min_occurrences
    return settings


def _make_memory_entry(
    *,
    content: str = "[failure_pattern] Agent 'scaffolder' failed QA check 'html_validation'",
    source: str = "failure_pattern",
    qa_check: str = "html_validation",
    client_ids: list[str] | None = None,
) -> tuple[MagicMock, float]:
    memory = MagicMock()
    memory.content = content
    memory.metadata_json = {
        "source": source,
        "qa_check": qa_check,
        "client_ids": client_ids or ["outlook_2019"],
    }
    return (memory, 0.8)


# ── Test 1: Extract from failed QA ──


class TestFailureExtractor:
    def test_extract_from_failed_qa(self) -> None:
        extractor = FailureExtractor()
        warnings = extractor.extract_from_qa_result(
            check_name="html_validation",
            passed=False,
            details={"message": "Missing VML wrapper", "suggestion": "Add VML wrapper"},
            component_slugs=["hero-full-width"],
            client_ids=["outlook_2019"],
            score=0.2,
        )
        assert len(warnings) == 1
        assert warnings[0].component == "hero-full-width"
        assert warnings[0].client == "outlook_2019"
        assert warnings[0].failure == "html_validation"
        assert warnings[0].severity == "critical"
        assert warnings[0].suggestion == "Add VML wrapper"

    # ── Test 2: Skip passed QA ──

    def test_extract_skips_passed_qa(self) -> None:
        extractor = FailureExtractor()
        warnings = extractor.extract_from_qa_result(
            check_name="html_validation",
            passed=True,
            details={},
            component_slugs=["hero-full-width"],
            client_ids=["outlook_2019"],
            score=1.0,
        )
        assert warnings == []

    # ── Test 3: Deduplication ──

    def test_deduplication_blake2b(self) -> None:
        extractor = FailureExtractor()
        for _ in range(3):
            extractor.extract_from_qa_result(
                check_name="dark_mode",
                passed=False,
                details={"message": "Dark mode incomplete"},
                component_slugs=["card-grid"],
                client_ids=["gmail"],
                score=0.5,
            )
        # Should only have 1 warning, not 3
        warnings = extractor.extract_from_qa_result(
            check_name="dark_mode",
            passed=False,
            details={"message": "Dark mode incomplete"},
            component_slugs=["card-grid"],
            client_ids=["gmail"],
            score=0.5,
        )
        assert warnings == []

    # ── Test 4: Severity mapping ──

    def test_severity_mapping(self) -> None:
        assert _score_to_severity(0.1) == "critical"
        assert _score_to_severity(0.29) == "critical"
        assert _score_to_severity(0.3) == "warning"
        assert _score_to_severity(0.5) == "warning"
        assert _score_to_severity(0.69) == "warning"
        assert _score_to_severity(0.7) == "info"
        assert _score_to_severity(1.0) == "info"


# ── Test 5-8: ProactiveWarningInjector ──


class TestProactiveWarningInjector:
    @pytest.mark.asyncio
    async def test_query_warnings_returns_matching(self) -> None:
        settings = _make_settings(failure_min_occurrences=1)
        injector = ProactiveWarningInjector(settings)

        mock_warnings = [
            ProactiveWarning(
                component="hero-full-width",
                client="outlook_2019",
                failure="html_validation",
                severity="critical",
                suggestion="Add VML wrapper",
                occurrence_count=1,
            ),
        ]

        with patch(
            "app.knowledge.proactive_qa._recall_component_warnings",
            new_callable=AsyncMock,
            return_value=mock_warnings,
        ):
            warnings = await injector.query_warnings(
                component_slugs=["hero-full-width"],
                client_ids=["outlook_2019"],
                project_id=None,
            )

        assert len(warnings) == 1
        assert warnings[0].failure == "html_validation"

    @pytest.mark.asyncio
    async def test_query_warnings_empty_no_match(self) -> None:
        settings = _make_settings(failure_min_occurrences=1)
        injector = ProactiveWarningInjector(settings)

        with patch(
            "app.knowledge.proactive_qa._recall_component_warnings",
            new_callable=AsyncMock,
            return_value=[],
        ):
            warnings = await injector.query_warnings(
                component_slugs=["hero-full-width"],
                client_ids=["outlook_2019"],
                project_id=None,
            )

        assert warnings == []

    @pytest.mark.asyncio
    async def test_query_warnings_respects_min_occurrences(self) -> None:
        settings = _make_settings(failure_min_occurrences=3)
        injector = ProactiveWarningInjector(settings)

        # occurrence_count=1, below min of 3
        mock_warnings = [
            ProactiveWarning(
                component="hero-full-width",
                client="outlook_2019",
                failure="html_validation",
                severity="critical",
                suggestion="Add VML wrapper",
                occurrence_count=1,
            ),
        ]

        with patch(
            "app.knowledge.proactive_qa._recall_component_warnings",
            new_callable=AsyncMock,
            return_value=mock_warnings,
        ):
            warnings = await injector.query_warnings(
                component_slugs=["hero-full-width"],
                client_ids=["outlook_2019"],
                project_id=None,
            )

        assert warnings == []

    @pytest.mark.asyncio
    async def test_query_warnings_caps_at_max(self) -> None:
        settings = _make_settings(failure_min_occurrences=1, proactive_max_warnings=2)
        injector = ProactiveWarningInjector(settings)

        mock_warnings = [
            ProactiveWarning(
                component="hero-full-width",
                client="outlook_2019",
                failure=f"check_{i}",
                severity="warning",
                suggestion=f"Fix check {i}",
                occurrence_count=1,
            )
            for i in range(5)
        ]

        with patch(
            "app.knowledge.proactive_qa._recall_component_warnings",
            new_callable=AsyncMock,
            return_value=mock_warnings,
        ):
            warnings = await injector.query_warnings(
                component_slugs=["hero-full-width"],
                client_ids=["outlook_2019"],
                project_id=None,
            )

        assert len(warnings) <= 2


# ── Test 9: Format warnings ──


class TestFormatWarnings:
    def test_format_warnings_for_prompt(self) -> None:
        settings = _make_settings()
        injector = ProactiveWarningInjector(settings)

        warnings = [
            ProactiveWarning(
                component="hero-full-width",
                client="outlook_2019",
                failure="html_validation",
                severity="critical",
                suggestion="Add VML wrapper",
                occurrence_count=3,
            ),
            ProactiveWarning(
                component="card-grid",
                client="gmail",
                failure="dark_mode",
                severity="warning",
                suggestion="Add dark mode classes",
                occurrence_count=2,
            ),
        ]

        text = injector.format_warnings_for_prompt(warnings)
        assert "## Known Failure Patterns" in text
        assert "hero-full-width" in text
        assert "outlook_2019" in text
        assert "Add VML wrapper" in text
        assert "seen 3x" in text
        assert "card-grid" in text


# ── Test 10-11: Pipeline integration ──


class TestPipelineIntegration:
    @pytest.mark.asyncio
    async def test_pipeline_injects_artifact(self) -> None:
        from app.ai.pipeline.artifacts import ArtifactStore, ProactiveWarningsArtifact
        from app.ai.pipeline.dag import PipelineDag, PipelineNode
        from app.ai.pipeline.executor import PipelineExecutor
        from app.core.config import PipelineConfig

        nodes = {
            "a": PipelineNode("agent_a", "standard", inputs=(), outputs=("html",)),
        }
        dag = PipelineDag(name="test", description="test", nodes=nodes)
        store = ArtifactStore()
        config = PipelineConfig(enabled=True, max_concurrent_agents=5)

        mock_runner = AsyncMock()
        mock_runner.return_value = MagicMock(tokens_used=50)

        executor = PipelineExecutor(dag, store, config, mock_runner)

        # Mock the proactive warnings injection
        test_warning = ProactiveWarning(
            component="hero-full-width",
            client="outlook_2019",
            failure="html_validation",
            severity="critical",
            suggestion="Add VML wrapper",
            occurrence_count=3,
        )

        async def mock_inject(run_id: str) -> None:
            artifact = ProactiveWarningsArtifact(
                name="proactive_warnings",
                produced_by="proactive_qa",
                produced_at=datetime.now(UTC),
                warnings=(test_warning,),
                formatted_text="## Known Failure Patterns\n- hero-full-width",
            )
            store.put("proactive_warnings", artifact)

        with patch.object(executor, "_inject_proactive_warnings", side_effect=mock_inject):
            result = await executor.execute("test-run")

        assert "proactive_warnings" in result.artifacts
        artifact = store.get("proactive_warnings", ProactiveWarningsArtifact)
        assert len(artifact.warnings) == 1
        assert artifact.warnings[0].component == "hero-full-width"

    @pytest.mark.asyncio
    async def test_pipeline_skips_when_disabled(self) -> None:
        from app.ai.pipeline.artifacts import ArtifactStore
        from app.ai.pipeline.dag import PipelineDag, PipelineNode
        from app.ai.pipeline.executor import PipelineExecutor
        from app.core.config import PipelineConfig

        nodes = {
            "a": PipelineNode("agent_a", "standard", inputs=(), outputs=("html",)),
        }
        dag = PipelineDag(name="test", description="test", nodes=nodes)
        store = ArtifactStore()
        config = PipelineConfig(enabled=True, max_concurrent_agents=5)

        mock_runner = AsyncMock()
        mock_runner.return_value = MagicMock(tokens_used=50)

        executor = PipelineExecutor(dag, store, config, mock_runner)

        mock_settings = _make_settings(proactive_qa_enabled=False)
        with patch("app.core.config.get_settings", return_value=mock_settings):
            result = await executor.execute("test-run")

        assert "proactive_warnings" not in result.artifacts


# ── Test 12: API endpoint ──


class TestProactiveWarningsAPI:
    @pytest.mark.asyncio
    async def test_api_proactive_warnings_endpoint(self) -> None:

        from app.knowledge.proactive_qa_routes import (
            ProactiveWarningsResponse,
            router,
        )

        # Verify response model structure
        response = ProactiveWarningsResponse(
            warnings=[],
            component_count=0,
            client_count=0,
        )
        assert response.warnings == []
        assert response.component_count == 0

        # Verify the router has the expected endpoints
        routes = [getattr(r, "path", None) for r in router.routes]
        assert "/proactive-warnings" in routes
        assert "/failure-graph" in routes
