"""Tests for the client lookup agent tools (Phase 32.4)."""

from __future__ import annotations

import json
from typing import Any

import pytest

from app.ai.agents.tools.client_lookup import (
    ClientLookupTool,
    MultiClientLookupTool,
    get_tool_definitions,
)
from app.knowledge.client_matrix import load_client_matrix


@pytest.fixture(autouse=True)
def _clear_matrix_cache() -> None:
    """Ensure clean matrix state between tests."""
    load_client_matrix.cache_clear()


# ── Helpers ──────────────────────────────────────────────────────────


def _parse(raw: str) -> dict[str, Any]:
    """Parse JSON string result."""
    result: dict[str, Any] = json.loads(raw)
    return result


# ── ClientLookupTool ─────────────────────────────────────────────────


class TestClientLookupTool:
    """Tests for single-client lookup queries."""

    tool = ClientLookupTool()

    @pytest.mark.anyio
    async def test_css_support_found(self) -> None:
        result = _parse(
            await self.tool.execute(
                query_type="css_support",
                client_id="outlook_365_win",
                property="border-radius",
            )
        )
        assert result["client"] == "outlook_365_win"
        assert result["query_type"] == "css_support"
        assert result["result"]["support"] == "none"
        assert "VML" in result["workaround"]

    @pytest.mark.anyio
    async def test_css_support_unknown_property(self) -> None:
        result = _parse(
            await self.tool.execute(
                query_type="css_support",
                client_id="outlook_365_win",
                property="totally-fake-property",
            )
        )
        assert result["result"]["support"] == "unknown"
        assert "No data" in result["result"]["notes"]

    @pytest.mark.anyio
    async def test_dark_mode_lookup(self) -> None:
        result = _parse(
            await self.tool.execute(
                query_type="dark_mode",
                client_id="samsung_mail",
            )
        )
        assert result["result"]["type"] == "double_inversion_risk"
        assert result["result"]["developer_control"] == "partial"
        assert len(result["result"]["selectors"]) >= 1

    @pytest.mark.anyio
    async def test_known_bugs_lookup(self) -> None:
        result = _parse(
            await self.tool.execute(
                query_type="known_bugs",
                client_id="outlook_365_win",
            )
        )
        bugs = result["result"]["bugs"]
        assert result["result"]["count"] >= 1
        bug_ids = [b["id"] for b in bugs]
        assert "ghost_table" in bug_ids

    @pytest.mark.anyio
    async def test_size_limits_lookup(self) -> None:
        result = _parse(
            await self.tool.execute(
                query_type="size_limits",
                client_id="gmail_web",
            )
        )
        assert result["result"]["clip_threshold_kb"] == 102

    @pytest.mark.anyio
    async def test_font_support_lookup_list(self) -> None:
        result = _parse(
            await self.tool.execute(
                query_type="font_support",
                client_id="outlook_365_win",
            )
        )
        fonts = result["result"]["fonts"]
        assert isinstance(fonts, list)
        assert "Arial" in fonts

    @pytest.mark.anyio
    async def test_font_support_wildcard(self) -> None:
        result = _parse(
            await self.tool.execute(
                query_type="font_support",
                client_id="gmail_web",
            )
        )
        assert result["result"]["fonts"] == "*"

    @pytest.mark.anyio
    async def test_unknown_client(self) -> None:
        result = _parse(
            await self.tool.execute(
                query_type="css_support",
                client_id="nonexistent_client",
                property="flexbox",
            )
        )
        assert "error" in result["result"]
        assert "Unknown client" in result["result"]["error"]
        assert isinstance(result["result"]["available_clients"], list)
        assert len(result["result"]["available_clients"]) >= 1

    @pytest.mark.anyio
    async def test_css_support_missing_property_param(self) -> None:
        result = _parse(
            await self.tool.execute(
                query_type="css_support",
                client_id="outlook_365_win",
            )
        )
        assert "error" in result["result"]
        assert "property is required" in result["result"]["error"]

    @pytest.mark.anyio
    async def test_invalid_query_type(self) -> None:
        result = _parse(
            await self.tool.execute(
                query_type="invalid_type",
                client_id="outlook_365_win",
            )
        )
        assert "error" in result
        assert "valid_types" in result

    @pytest.mark.anyio
    async def test_result_is_valid_json(self) -> None:
        raw = await self.tool.execute(
            query_type="dark_mode",
            client_id="outlook_365_win",
        )
        parsed = json.loads(raw)
        assert isinstance(parsed, dict)

    @pytest.mark.anyio
    async def test_confidence_always_1(self) -> None:
        result = _parse(
            await self.tool.execute(
                query_type="dark_mode",
                client_id="outlook_365_win",
            )
        )
        assert result["confidence"] == 1.0

    @pytest.mark.anyio
    async def test_size_limits_empty(self) -> None:
        result = _parse(
            await self.tool.execute(
                query_type="size_limits",
                client_id="outlook_365_win",
            )
        )
        assert result["result"]["clip_threshold_kb"] is None


# ── MultiClientLookupTool ────────────────────────────────────────────


class TestMultiClientLookupTool:
    """Tests for batch client lookup queries."""

    tool = MultiClientLookupTool()

    @pytest.mark.anyio
    async def test_batch_single_client_single_property(self) -> None:
        result = _parse(
            await self.tool.execute(
                query_type="css_support",
                client_ids=["outlook_365_win"],
                properties=["border-radius"],
            )
        )
        assert len(result["results"]) == 1
        assert result["results"][0]["client"] == "outlook_365_win"
        assert result["results"][0]["property"] == "border-radius"

    @pytest.mark.anyio
    async def test_batch_multi_client_multi_property(self) -> None:
        result = _parse(
            await self.tool.execute(
                query_type="css_support",
                client_ids=["outlook_365_win", "gmail_web", "apple_mail_macos"],
                properties=["flexbox", "border-radius"],
            )
        )
        assert len(result["results"]) == 6

    @pytest.mark.anyio
    async def test_batch_with_unknown_client(self) -> None:
        result = _parse(
            await self.tool.execute(
                query_type="css_support",
                client_ids=["outlook_365_win", "fake_client"],
                properties=["flexbox"],
            )
        )
        assert len(result["results"]) == 2
        valid = result["results"][0]
        invalid = result["results"][1]
        assert "error" not in valid["result"]
        assert "error" in invalid["result"]

    @pytest.mark.anyio
    async def test_batch_empty_inputs(self) -> None:
        result = _parse(
            await self.tool.execute(
                query_type="css_support",
                client_ids=[],
                properties=[],
            )
        )
        assert result["results"] == []

    @pytest.mark.anyio
    async def test_batch_no_properties_dark_mode(self) -> None:
        result = _parse(
            await self.tool.execute(
                query_type="dark_mode",
                client_ids=["outlook_365_win", "samsung_mail"],
            )
        )
        assert len(result["results"]) == 2
        types = [r["result"]["type"] for r in result["results"]]
        assert "forced_inversion" in types
        assert "double_inversion_risk" in types

    @pytest.mark.anyio
    async def test_batch_invalid_query_type(self) -> None:
        result = _parse(
            await self.tool.execute(
                query_type="bad",
                client_ids=["gmail_web"],
            )
        )
        assert "error" in result


# ── Tool Logging ─────────────────────────────────────────────────────


class TestToolLogging:
    """Verify structured logging from tool calls."""

    @pytest.mark.anyio
    async def test_single_lookup_logs_query(self, capsys: pytest.CaptureFixture[str]) -> None:
        tool = ClientLookupTool()
        await tool.execute(
            query_type="css_support",
            client_id="gmail_web",
            property="flexbox",
        )
        captured = capsys.readouterr()
        assert "agents.client_lookup.query" in captured.out

    @pytest.mark.anyio
    async def test_batch_lookup_logs_counts(self, capsys: pytest.CaptureFixture[str]) -> None:
        tool = MultiClientLookupTool()
        await tool.execute(
            query_type="dark_mode",
            client_ids=["gmail_web", "outlook_365_win"],
        )
        captured = capsys.readouterr()
        assert "agents.client_lookup.batch_query" in captured.out


# ── Tool Definitions ─────────────────────────────────────────────────


class TestToolDefinitions:
    """Verify JSON Schema tool definitions."""

    def test_definitions_valid(self) -> None:
        defs = get_tool_definitions()
        assert len(defs) == 2
        names = [d["name"] for d in defs]
        assert "lookup_client_support" in names
        assert "lookup_client_support_batch" in names

    def test_definitions_have_required_fields(self) -> None:
        for defn in get_tool_definitions():
            assert "name" in defn
            assert "description" in defn
            assert "parameters" in defn
            params = defn["parameters"]
            assert params["type"] == "object"
            assert "properties" in params
            assert "required" in params

    def test_tool_names_unique(self) -> None:
        defs = get_tool_definitions()
        names = [d["name"] for d in defs]
        assert len(names) == len(set(names))

    def test_single_tool_schema_has_query_type(self) -> None:
        defs = get_tool_definitions()
        single = next(d for d in defs if d["name"] == "lookup_client_support")
        assert "query_type" in single["parameters"]["properties"]
        assert "client_id" in single["parameters"]["properties"]
        assert "property" in single["parameters"]["properties"]

    def test_batch_tool_schema_has_client_ids(self) -> None:
        defs = get_tool_definitions()
        batch = next(d for d in defs if d["name"] == "lookup_client_support_batch")
        assert "client_ids" in batch["parameters"]["properties"]
        assert batch["parameters"]["properties"]["client_ids"]["type"] == "array"
