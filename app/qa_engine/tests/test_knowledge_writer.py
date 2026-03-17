"""Tests for ChaosKnowledgeWriter — auto-documenting chaos failures."""

from unittest.mock import AsyncMock, patch

import pytest

from app.qa_engine.chaos.knowledge_writer import ChaosKnowledgeWriter
from app.qa_engine.schemas import ChaosFailure


def _make_failure(profile: str = "gmail_style_strip", check: str = "css_support") -> ChaosFailure:
    return ChaosFailure(
        profile=profile,
        check_name=check,
        severity="error",
        description=f"{check} failed after {profile}",
    )


class TestChaosKnowledgeWriter:
    def test_build_document_content(self) -> None:
        failure = _make_failure()
        content = ChaosKnowledgeWriter._build_document_content(failure, "Use inline styles.")
        assert "gmail_style_strip" in content
        assert "css_support" in content
        assert "Use inline styles." in content
        assert "## Recommended Fix" in content

    @pytest.mark.asyncio
    async def test_empty_failures_returns_empty(self) -> None:
        db = AsyncMock()
        writer = ChaosKnowledgeWriter(db)
        result = await writer.write_failure_documents([], project_id=1)
        assert result == []

    @pytest.mark.asyncio
    async def test_deduplicates_same_profile_check(self) -> None:
        """Two failures with same profile+check should produce one document."""
        db = AsyncMock()
        writer = ChaosKnowledgeWriter(db)
        failures = [
            _make_failure("gmail_style_strip", "css_support"),
            _make_failure("gmail_style_strip", "css_support"),
        ]
        with (
            patch.object(writer, "_title_exists", return_value=False),
            patch.object(writer._service, "ingest_text", new_callable=AsyncMock, return_value=1),
        ):
            result = await writer.write_failure_documents(failures, project_id=1)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_skips_existing_documents(self) -> None:
        db = AsyncMock()
        writer = ChaosKnowledgeWriter(db)
        failures = [_make_failure()]
        with patch.object(writer, "_title_exists", return_value=True):
            result = await writer.write_failure_documents(failures, project_id=1)
        assert result == []

    @pytest.mark.asyncio
    async def test_creates_document_with_correct_domain(self) -> None:
        db = AsyncMock()
        writer = ChaosKnowledgeWriter(db)
        failures = [_make_failure()]
        with (
            patch.object(writer, "_title_exists", return_value=False),
            patch.object(
                writer._service, "ingest_text", new_callable=AsyncMock, return_value=42
            ) as mock_ingest,
        ):
            result = await writer.write_failure_documents(failures, project_id=5)
        assert result == [42]
        mock_ingest.assert_called_once()
        call_kwargs = mock_ingest.call_args[1]
        assert call_kwargs["domain"] == "chaos_findings"
        assert "project_id" in call_kwargs.get("metadata_json", "")

    @pytest.mark.asyncio
    async def test_multiple_unique_failures(self) -> None:
        db = AsyncMock()
        writer = ChaosKnowledgeWriter(db)
        failures = [
            _make_failure("gmail_style_strip", "css_support"),
            _make_failure("image_blocked", "accessibility"),
        ]
        call_count = 0

        async def mock_ingest(**kwargs: object) -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        with (
            patch.object(writer, "_title_exists", return_value=False),
            patch.object(writer._service, "ingest_text", side_effect=mock_ingest),
        ):
            result = await writer.write_failure_documents(failures, project_id=1)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_fix_hint_used_for_known_profile(self) -> None:
        failure = _make_failure("gmail_clipping", "file_size")
        content = ChaosKnowledgeWriter._build_document_content(failure, "Keep HTML under 102KB.")
        assert "102KB" in content

    @pytest.mark.asyncio
    async def test_default_fix_hint_for_unknown_profile(self) -> None:
        db = AsyncMock()
        writer = ChaosKnowledgeWriter(db)
        failure = _make_failure("unknown_profile", "some_check")
        with (
            patch.object(writer, "_title_exists", return_value=False),
            patch.object(
                writer._service, "ingest_text", new_callable=AsyncMock, return_value=1
            ) as mock_ingest,
        ):
            await writer.write_failure_documents([failure], project_id=1)
        content = mock_ingest.call_args[1]["content"]
        assert "Review the failure" in content

    def test_sanitize_markdown_strips_special_chars(self) -> None:
        text = "**bold** _italic_ [link](url) `code` # heading <tag> ~strike~"
        result = ChaosKnowledgeWriter._sanitize_markdown(text)
        assert "*" not in result
        assert "_" not in result
        assert "[" not in result
        assert "]" not in result
        assert "`" not in result
        assert "#" not in result
        assert "<" not in result
        assert ">" not in result
        assert "~" not in result

    def test_build_document_content_includes_severity(self) -> None:
        failure = _make_failure()
        content = ChaosKnowledgeWriter._build_document_content(failure, "Fix it.")
        assert "error" in content  # severity from _make_failure
        assert "**Severity:**" in content

    @pytest.mark.asyncio
    async def test_write_failure_documents_ingestion_error_non_blocking(self) -> None:
        db = AsyncMock()
        writer = ChaosKnowledgeWriter(db)
        failures = [_make_failure()]
        with (
            patch.object(writer, "_title_exists", return_value=False),
            patch.object(
                writer._service,
                "ingest_text",
                new_callable=AsyncMock,
                side_effect=RuntimeError("DB down"),
            ),
        ):
            # ingest_text raises, but write_failure_documents doesn't catch per-item
            # The caller (service) wraps in try/except — test that the error propagates
            # from writer so the service can handle it
            with pytest.raises(RuntimeError, match="DB down"):
                await writer.write_failure_documents(failures, project_id=1)

    def test_fix_hints_cover_all_builtin_profiles(self) -> None:
        from app.qa_engine.chaos.knowledge_writer import _FIX_HINTS
        from app.qa_engine.chaos.profiles import PROFILES

        for profile_name in PROFILES:
            assert profile_name in _FIX_HINTS, f"Missing fix hint for {profile_name}"
