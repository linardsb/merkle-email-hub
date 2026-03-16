"""Tests for multi-representation chunk summarizer."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.knowledge.summarizer import ChunkSummarizer

# ---------------------------------------------------------------------------
# Deterministic CSS tests
# ---------------------------------------------------------------------------


class TestSummarizeCssBlock:
    def test_single_rule(self) -> None:
        css = ".header { background-color: #fff; padding: 10px; }"
        result = ChunkSummarizer.summarize_css_block(css)
        assert result.startswith("CSS rules: ")
        assert "background-color" in result
        assert "padding" in result

    def test_multiple_rules(self) -> None:
        css = ".header { color: red; } .footer { margin: 0; font-size: 14px; }"
        result = ChunkSummarizer.summarize_css_block(css)
        assert ".header" in result
        assert ".footer" in result
        assert "color" in result
        assert "margin" in result
        assert "font-size" in result

    def test_media_query(self) -> None:
        css = "@media (max-width: 600px) { .container { width: 100%; display: block; } }"
        result = ChunkSummarizer.summarize_css_block(css)
        assert "@media" in result
        assert "width" in result

    def test_empty_block(self) -> None:
        css = "/* just a comment */"
        result = ChunkSummarizer.summarize_css_block(css)
        assert result.startswith("CSS style block (")
        assert "chars)" in result

    def test_with_style_tags(self) -> None:
        css = "<style>.btn { color: blue; }</style>"
        result = ChunkSummarizer.summarize_css_block(css)
        assert "color" in result
        # <style> tag should not appear in selector
        assert "<style>" not in result


# ---------------------------------------------------------------------------
# Deterministic MSO tests
# ---------------------------------------------------------------------------


class TestSummarizeMsoBlock:
    def test_basic(self) -> None:
        html = "<!--[if mso]><table><tr><td>Content</td></tr></table><![endif]-->"
        result = ChunkSummarizer.summarize_mso_block(html)
        assert "MSO conditional block [if mso]" in result
        assert "1 table" in result

    def test_vml(self) -> None:
        html = "<!--[if mso]><v:rect><v:fill></v:fill></v:rect><![endif]-->"
        result = ChunkSummarizer.summarize_mso_block(html)
        assert "VML element" in result

    def test_no_tables(self) -> None:
        html = "<!--[if gte mso 9]><xml><o:OfficeDocumentSettings></o:OfficeDocumentSettings></xml><![endif]-->"
        result = ChunkSummarizer.summarize_mso_block(html)
        assert "MSO conditional block [if gte mso 9]" in result
        assert "table" not in result


# ---------------------------------------------------------------------------
# Routing tests (mock LLM)
# ---------------------------------------------------------------------------


class TestSummarizeRouting:
    @pytest.mark.asyncio
    async def test_routes_style_deterministic(self) -> None:
        summarizer = ChunkSummarizer()
        with patch.object(summarizer, "_summarize_html_batch", new_callable=AsyncMock) as mock_llm:
            results = await summarizer.summarize([(0, ".h{color:red;}", "style")])
            mock_llm.assert_not_called()
            assert results[0].summary is not None
            assert "CSS" in results[0].summary

    @pytest.mark.asyncio
    async def test_routes_mso_deterministic(self) -> None:
        summarizer = ChunkSummarizer()
        with patch.object(summarizer, "_summarize_html_batch", new_callable=AsyncMock) as mock_llm:
            results = await summarizer.summarize(
                [(0, "<!--[if mso]><table></table><![endif]-->", "mso_conditional")]
            )
            mock_llm.assert_not_called()
            assert results[0].summary is not None
            assert "MSO" in results[0].summary

    @pytest.mark.asyncio
    async def test_routes_section_to_llm(self) -> None:
        summarizer = ChunkSummarizer()
        with patch.object(
            summarizer, "_summarize_html_batch", new_callable=AsyncMock, return_value=["A summary"]
        ) as mock_llm:
            results = await summarizer.summarize([(0, "<div>Hello</div>", "section")])
            mock_llm.assert_called_once()
            assert results[0].summary == "A summary"

    @pytest.mark.asyncio
    async def test_routes_body_to_llm(self) -> None:
        summarizer = ChunkSummarizer()
        with patch.object(
            summarizer,
            "_summarize_html_batch",
            new_callable=AsyncMock,
            return_value=["Body summary"],
        ) as mock_llm:
            results = await summarizer.summarize([(0, "<body>Content</body>", "body")])
            mock_llm.assert_called_once()
            assert results[0].summary == "Body summary"

    @pytest.mark.asyncio
    async def test_skips_plain_text(self) -> None:
        summarizer = ChunkSummarizer()
        with patch.object(summarizer, "_summarize_html_batch", new_callable=AsyncMock) as mock_llm:
            results = await summarizer.summarize([(0, "Just some text content.", None)])
            mock_llm.assert_not_called()
            assert results[0].summary is None

    @pytest.mark.asyncio
    async def test_mixed_batch(self) -> None:
        summarizer = ChunkSummarizer()
        with patch.object(
            summarizer,
            "_summarize_html_batch",
            new_callable=AsyncMock,
            return_value=["LLM summary"],
        ):
            results = await summarizer.summarize(
                [
                    (0, ".h{color:red;}", "style"),
                    (1, "<div>Content</div>", "section"),
                    (2, "Plain text", None),
                    (3, "<!--[if mso]><table></table><![endif]-->", "mso_conditional"),
                ]
            )
            assert len(results) == 4
            assert "CSS" in (results[0].summary or "")
            assert results[1].summary == "LLM summary"
            assert results[2].summary is None
            assert "MSO" in (results[3].summary or "")


# ---------------------------------------------------------------------------
# LLM integration tests (mock httpx)
# ---------------------------------------------------------------------------


_DUMMY_REQUEST = httpx.Request("POST", "https://api.test.com/v1/chat/completions")


def _make_mock_settings() -> MagicMock:
    settings = MagicMock()
    settings.knowledge.multi_rep_api_key = "test-key"
    settings.knowledge.multi_rep_api_base_url = "https://api.test.com/v1"
    settings.knowledge.multi_rep_model = "gpt-4o-mini"
    return settings


class TestLlmSummarize:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        mock_response = httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": "A responsive hero section with centered text."}}
                ]
            },
            request=_DUMMY_REQUEST,
        )
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        result = await ChunkSummarizer._llm_summarize(
            mock_client, "<div>Hero</div>", _make_mock_settings()
        )
        assert result == "A responsive hero section with centered text."

    @pytest.mark.asyncio
    async def test_failure_returns_none(self) -> None:
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.HTTPStatusError(
            "Server error",
            request=_DUMMY_REQUEST,
            response=httpx.Response(500, request=_DUMMY_REQUEST),
        )
        result = await ChunkSummarizer._llm_summarize(
            mock_client, "<div>Fail</div>", _make_mock_settings()
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_timeout_returns_none(self) -> None:
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.ReadTimeout("Timeout")
        result = await ChunkSummarizer._llm_summarize(
            mock_client, "<div>Slow</div>", _make_mock_settings()
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_empty_response_returns_none(self) -> None:
        mock_response = httpx.Response(
            200,
            json={"choices": [{"message": {"content": "  "}}]},
            request=_DUMMY_REQUEST,
        )
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        result = await ChunkSummarizer._llm_summarize(
            mock_client, "<div>Empty</div>", _make_mock_settings()
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_no_api_key(self) -> None:
        summarizer = ChunkSummarizer()
        with (
            patch("app.knowledge.summarizer.get_settings") as mock_settings,
            patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post,
        ):
            mock_settings.return_value.knowledge.multi_rep_api_key = ""
            mock_settings.return_value.knowledge.multi_rep_max_concurrency = 5
            results = await summarizer._summarize_html_batch(["<div>Test</div>"])
            mock_post.assert_not_called()
            assert results == [None]

    @pytest.mark.asyncio
    async def test_concurrency_limit(self) -> None:
        """Verify semaphore limits parallel LLM calls."""
        call_count = 0
        max_concurrent = 0
        current_concurrent = 0

        async def _mock_summarize(_client: object, _html: str, _settings: object) -> str | None:
            nonlocal call_count, max_concurrent, current_concurrent
            current_concurrent += 1
            max_concurrent = max(max_concurrent, current_concurrent)
            call_count += 1
            import asyncio

            await asyncio.sleep(0.01)
            current_concurrent -= 1
            return f"summary-{call_count}"

        summarizer = ChunkSummarizer()
        with (
            patch("app.knowledge.summarizer.get_settings") as mock_settings,
            patch.object(ChunkSummarizer, "_llm_summarize", side_effect=_mock_summarize),
        ):
            mock_settings.return_value.knowledge.multi_rep_api_key = "test-key"
            mock_settings.return_value.knowledge.multi_rep_max_concurrency = 2

            contents = [f"<div>Section {i}</div>" for i in range(6)]
            results = await summarizer._summarize_html_batch(contents)

            assert len(results) == 6
            assert all(r is not None for r in results)
            assert max_concurrent <= 2
