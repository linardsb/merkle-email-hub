"""Tests for TypstRenderer — subprocess wrapper for Typst CLI."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.reporting.exceptions import ReportTooLargeError, TypstCompilationError
from app.reporting.typst_renderer import TypstRenderer


@pytest.fixture
def renderer() -> TypstRenderer:
    return TypstRenderer()


def _mock_settings(
    *,
    typst_binary: str = "typst",
    compilation_timeout_s: int = 10,
    max_report_size_mb: int = 50,
) -> MagicMock:
    settings = MagicMock()
    settings.reporting.typst_binary = typst_binary
    settings.reporting.compilation_timeout_s = compilation_timeout_s
    settings.reporting.max_report_size_mb = max_report_size_mb
    return settings


class TestTypstRenderer:
    async def test_render_success(self, renderer: TypstRenderer) -> None:
        """Successful compilation returns PDF bytes."""
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"", b"")
        mock_proc.returncode = 0
        mock_proc.kill = MagicMock()

        fake_pdf = b"%PDF-1.4 test content"

        with (
            patch(
                "app.reporting.typst_renderer.get_settings",
                return_value=_mock_settings(),
            ),
            patch(
                "app.reporting.typst_renderer.asyncio.create_subprocess_exec",
                return_value=mock_proc,
            ),
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "read_text", return_value="// typst template"),
            patch.object(Path, "read_bytes", return_value=fake_pdf),
            patch.object(Path, "write_text"),
        ):
            result = await renderer.render("qa_report", {"test": "data"})
            assert result == fake_pdf

    async def test_render_timeout(self, renderer: TypstRenderer) -> None:
        """Timeout raises TypstCompilationError."""
        mock_proc = AsyncMock()
        mock_proc.communicate.side_effect = TimeoutError()
        mock_proc.kill = MagicMock()

        with (
            patch(
                "app.reporting.typst_renderer.get_settings",
                return_value=_mock_settings(compilation_timeout_s=1),
            ),
            patch(
                "app.reporting.typst_renderer.asyncio.create_subprocess_exec",
                return_value=mock_proc,
            ),
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "read_text", return_value="// typst template"),
            patch.object(Path, "write_text"),
        ):
            # wait_for wraps with TimeoutError
            with patch(
                "app.reporting.typst_renderer.asyncio.wait_for",
                side_effect=TimeoutError(),
            ):
                with pytest.raises(TypstCompilationError, match="timed out"):
                    await renderer.render("qa_report", {"test": "data"})

    async def test_render_nonzero_exit(self, renderer: TypstRenderer) -> None:
        """Non-zero exit code raises TypstCompilationError with stderr."""
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"", b"error: unexpected token")
        mock_proc.returncode = 1
        mock_proc.kill = MagicMock()

        with (
            patch(
                "app.reporting.typst_renderer.get_settings",
                return_value=_mock_settings(),
            ),
            patch(
                "app.reporting.typst_renderer.asyncio.create_subprocess_exec",
                return_value=mock_proc,
            ),
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "read_text", return_value="// typst template"),
            patch.object(Path, "write_text"),
        ):
            with pytest.raises(TypstCompilationError, match="unexpected token"):
                await renderer.render("qa_report", {"test": "data"})

    async def test_render_no_output_file(self, renderer: TypstRenderer) -> None:
        """Missing output file raises TypstCompilationError."""
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"", b"")
        mock_proc.returncode = 0
        mock_proc.kill = MagicMock()

        def mock_exists(self: Path) -> bool:
            # Template exists, output does not
            if "output.pdf" in str(self):
                return False
            return True

        with (
            patch(
                "app.reporting.typst_renderer.get_settings",
                return_value=_mock_settings(),
            ),
            patch(
                "app.reporting.typst_renderer.asyncio.create_subprocess_exec",
                return_value=mock_proc,
            ),
            patch.object(Path, "exists", mock_exists),
            patch.object(Path, "read_text", return_value="// typst template"),
            patch.object(Path, "write_text"),
        ):
            with pytest.raises(TypstCompilationError, match="no output file"):
                await renderer.render("qa_report", {"test": "data"})

    async def test_render_size_limit_exceeded(self, renderer: TypstRenderer) -> None:
        """PDF exceeding size limit raises ReportTooLargeError."""
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"", b"")
        mock_proc.returncode = 0
        mock_proc.kill = MagicMock()

        # 2MB file, 1MB limit
        oversized_pdf = b"X" * (2 * 1024 * 1024)

        with (
            patch(
                "app.reporting.typst_renderer.get_settings",
                return_value=_mock_settings(max_report_size_mb=1),
            ),
            patch(
                "app.reporting.typst_renderer.asyncio.create_subprocess_exec",
                return_value=mock_proc,
            ),
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "read_text", return_value="// typst template"),
            patch.object(Path, "read_bytes", return_value=oversized_pdf),
            patch.object(Path, "write_text"),
        ):
            with pytest.raises(ReportTooLargeError, match="exceeds limit"):
                await renderer.render("qa_report", {"test": "data"})

    async def test_render_template_not_found(self, renderer: TypstRenderer) -> None:
        """Non-existent template raises TypstCompilationError."""
        with patch(
            "app.reporting.typst_renderer.get_settings",
            return_value=_mock_settings(),
        ):
            with pytest.raises(TypstCompilationError, match="Template not found"):
                await renderer.render("nonexistent_template", {"test": "data"})
