"""Unit tests for the pre-send rendering gate (Phase 27.3)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.rendering.gate import DEFAULT_GATE_CLIENTS, RenderingSendGate
from app.rendering.gate_schemas import (
    GateConfigUpdateRequest,
    GateEvaluateRequest,
    GateMode,
    GateResult,
    GateVerdict,
)

_TEMPLATE_DIR = Path("app/ai/templates/library")


def _load_template(name: str = "minimal_text.html") -> str:
    """Load a real golden template for testing."""
    path = _TEMPLATE_DIR / name
    return path.read_text()


SIMPLE_TABLE_HTML = """
<html><body>
<table width="600" cellpadding="0" cellspacing="0">
  <tr><td style="padding:20px;font-family:Arial,sans-serif;font-size:16px;color:#333333;">
    Hello World
  </td></tr>
</table>
</body></html>
"""

FLEXBOX_HTML = """
<html><body>
<table><tr><td style="display:flex;justify-content:center;">
  <div>Flexbox content</div>
</td></tr></table>
</body></html>
"""


def _make_db_mock() -> AsyncMock:
    """Create a mock AsyncSession."""
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute.return_value = result
    return db


@pytest.mark.asyncio
async def test_gate_skip_mode_always_passes() -> None:
    """Mode=skip → passed=True, verdict='pass', no client results."""
    db = _make_db_mock()
    gate = RenderingSendGate(db)

    with patch("app.rendering.gate.get_settings") as mock_settings:
        mock_settings.return_value.rendering.gate_mode = "skip"
        mock_settings.return_value.rendering.gate_tier1_threshold = 85.0
        mock_settings.return_value.rendering.gate_tier2_threshold = 70.0
        mock_settings.return_value.rendering.gate_tier3_threshold = 60.0

        result = await gate.evaluate(GateEvaluateRequest(html=SIMPLE_TABLE_HTML))

    assert result.passed is True
    assert result.verdict == GateVerdict.PASS
    assert result.mode == GateMode.skip
    assert result.client_results == []


@pytest.mark.asyncio
async def test_gate_simple_html_passes_all_tiers() -> None:
    """Simple table-based HTML should pass all default clients."""
    db = _make_db_mock()
    gate = RenderingSendGate(db)

    with patch("app.rendering.gate.get_settings") as mock_settings:
        mock_settings.return_value.rendering.gate_mode = "enforce"
        mock_settings.return_value.rendering.gate_tier1_threshold = 40.0
        mock_settings.return_value.rendering.gate_tier2_threshold = 30.0
        mock_settings.return_value.rendering.gate_tier3_threshold = 20.0

        result = await gate.evaluate(GateEvaluateRequest(html=SIMPLE_TABLE_HTML))

    assert result.passed is True
    assert result.verdict == GateVerdict.PASS
    assert len(result.client_results) > 0
    for cr in result.client_results:
        assert cr.passed is True


@pytest.mark.asyncio
async def test_gate_flexbox_blocks_outlook() -> None:
    """HTML with display:flex should lower confidence for outlook_desktop."""
    db = _make_db_mock()
    gate = RenderingSendGate(db)

    with patch("app.rendering.gate.get_settings") as mock_settings:
        mock_settings.return_value.rendering.gate_mode = "enforce"
        mock_settings.return_value.rendering.gate_tier1_threshold = 95.0
        mock_settings.return_value.rendering.gate_tier2_threshold = 95.0
        mock_settings.return_value.rendering.gate_tier3_threshold = 95.0

        result = await gate.evaluate(
            GateEvaluateRequest(
                html=FLEXBOX_HTML,
                target_clients=["outlook_desktop", "gmail_web"],
            )
        )

    # At least one client should be blocked with very high thresholds
    assert result.verdict == GateVerdict.BLOCK
    assert result.passed is False
    assert len(result.blocking_clients) > 0


@pytest.mark.asyncio
async def test_gate_warn_mode_passes_with_warnings() -> None:
    """Mode=warn + low confidence → verdict='warn', passed=True."""
    db = _make_db_mock()
    gate = RenderingSendGate(db)

    with patch("app.rendering.gate.get_settings") as mock_settings:
        mock_settings.return_value.rendering.gate_mode = "warn"
        mock_settings.return_value.rendering.gate_tier1_threshold = 99.0
        mock_settings.return_value.rendering.gate_tier2_threshold = 99.0
        mock_settings.return_value.rendering.gate_tier3_threshold = 99.0

        result = await gate.evaluate(GateEvaluateRequest(html=SIMPLE_TABLE_HTML))

    assert result.passed is True
    assert result.verdict == GateVerdict.WARN
    assert result.mode == GateMode.warn
    assert len(result.blocking_clients) > 0


@pytest.mark.asyncio
async def test_gate_enforce_mode_blocks() -> None:
    """Mode=enforce + low confidence → verdict='block', passed=False."""
    db = _make_db_mock()
    gate = RenderingSendGate(db)

    with patch("app.rendering.gate.get_settings") as mock_settings:
        mock_settings.return_value.rendering.gate_mode = "enforce"
        mock_settings.return_value.rendering.gate_tier1_threshold = 99.0
        mock_settings.return_value.rendering.gate_tier2_threshold = 99.0
        mock_settings.return_value.rendering.gate_tier3_threshold = 99.0

        result = await gate.evaluate(GateEvaluateRequest(html=SIMPLE_TABLE_HTML))

    assert result.passed is False
    assert result.verdict == GateVerdict.BLOCK


@pytest.mark.asyncio
async def test_gate_project_config_override() -> None:
    """Per-project thresholds override globals."""
    db = AsyncMock()

    # Mock a project with custom gate config
    project = MagicMock()
    project.rendering_gate_config = {
        "mode": "enforce",
        "tier_thresholds": {"tier_1": 10.0, "tier_2": 10.0, "tier_3": 10.0},
        "target_clients": ["gmail_web"],
        "require_external_validation": [],
    }
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = project
    db.execute.return_value = result_mock

    gate = RenderingSendGate(db)

    with patch("app.rendering.gate.get_settings") as mock_settings:
        mock_settings.return_value.rendering.gate_mode = "enforce"
        mock_settings.return_value.rendering.gate_tier1_threshold = 99.0
        mock_settings.return_value.rendering.gate_tier2_threshold = 99.0
        mock_settings.return_value.rendering.gate_tier3_threshold = 99.0

        result = await gate.evaluate(GateEvaluateRequest(html=SIMPLE_TABLE_HTML, project_id=1))

    # Project config has threshold=10, so simple HTML should pass
    assert result.passed is True
    assert result.verdict == GateVerdict.PASS


@pytest.mark.asyncio
async def test_gate_default_clients_used() -> None:
    """No target_clients → DEFAULT_GATE_CLIENTS used."""
    db = _make_db_mock()
    gate = RenderingSendGate(db)

    with patch("app.rendering.gate.get_settings") as mock_settings:
        mock_settings.return_value.rendering.gate_mode = "warn"
        mock_settings.return_value.rendering.gate_tier1_threshold = 85.0
        mock_settings.return_value.rendering.gate_tier2_threshold = 70.0
        mock_settings.return_value.rendering.gate_tier3_threshold = 60.0

        result = await gate.evaluate(GateEvaluateRequest(html=SIMPLE_TABLE_HTML))

    client_names = {cr.client_name for cr in result.client_results}
    # All default clients should be present (minus any missing from CLIENT_PROFILES)
    for client in DEFAULT_GATE_CLIENTS:
        from app.rendering.local.profiles import CLIENT_PROFILES

        if client in CLIENT_PROFILES:
            assert client in client_names


@pytest.mark.asyncio
async def test_gate_request_clients_override() -> None:
    """Request target_clients override project config."""
    db = _make_db_mock()
    gate = RenderingSendGate(db)

    with patch("app.rendering.gate.get_settings") as mock_settings:
        mock_settings.return_value.rendering.gate_mode = "warn"
        mock_settings.return_value.rendering.gate_tier1_threshold = 85.0
        mock_settings.return_value.rendering.gate_tier2_threshold = 70.0
        mock_settings.return_value.rendering.gate_tier3_threshold = 60.0

        result = await gate.evaluate(
            GateEvaluateRequest(
                html=SIMPLE_TABLE_HTML,
                target_clients=["gmail_web", "thunderbird"],
            )
        )

    client_names = {cr.client_name for cr in result.client_results}
    assert client_names == {"gmail_web", "thunderbird"}


@pytest.mark.asyncio
async def test_blocking_reasons_populated() -> None:
    """Failed client has non-empty blocking_reasons."""
    db = _make_db_mock()
    gate = RenderingSendGate(db)

    with patch("app.rendering.gate.get_settings") as mock_settings:
        mock_settings.return_value.rendering.gate_mode = "enforce"
        mock_settings.return_value.rendering.gate_tier1_threshold = 99.0
        mock_settings.return_value.rendering.gate_tier2_threshold = 99.0
        mock_settings.return_value.rendering.gate_tier3_threshold = 99.0

        result = await gate.evaluate(
            GateEvaluateRequest(
                html=SIMPLE_TABLE_HTML,
                target_clients=["gmail_web"],
            )
        )

    assert len(result.blocking_clients) > 0
    for cr in result.client_results:
        if not cr.passed:
            assert len(cr.blocking_reasons) > 0


@pytest.mark.asyncio
async def test_remediation_populated() -> None:
    """Failed Outlook client has non-empty remediation for flexbox HTML."""
    db = _make_db_mock()
    gate = RenderingSendGate(db)

    with patch("app.rendering.gate.get_settings") as mock_settings:
        mock_settings.return_value.rendering.gate_mode = "enforce"
        mock_settings.return_value.rendering.gate_tier1_threshold = 99.0
        mock_settings.return_value.rendering.gate_tier2_threshold = 99.0
        mock_settings.return_value.rendering.gate_tier3_threshold = 99.0

        result = await gate.evaluate(
            GateEvaluateRequest(
                html=FLEXBOX_HTML,
                target_clients=["outlook_desktop"],
            )
        )

    for cr in result.client_results:
        if not cr.passed and "outlook" in cr.client_name:
            assert len(cr.remediation) > 0


@pytest.mark.asyncio
async def test_gate_real_template() -> None:
    """Test with a real golden template from the library."""
    template_html = _load_template("minimal_text.html")
    db = _make_db_mock()
    gate = RenderingSendGate(db)

    with patch("app.rendering.gate.get_settings") as mock_settings:
        mock_settings.return_value.rendering.gate_mode = "warn"
        mock_settings.return_value.rendering.gate_tier1_threshold = 85.0
        mock_settings.return_value.rendering.gate_tier2_threshold = 70.0
        mock_settings.return_value.rendering.gate_tier3_threshold = 60.0

        result = await gate.evaluate(
            GateEvaluateRequest(
                html=template_html,
                target_clients=["gmail_web"],
            )
        )

    assert isinstance(result, GateResult)
    assert result.evaluated_at  # non-empty ISO string
    assert len(result.client_results) == 1


@pytest.mark.asyncio
async def test_gate_config_crud() -> None:
    """Get/update gate config round-trip via RenderingService."""
    from app.rendering.service import RenderingService

    db = AsyncMock()

    # Mock project lookup — no existing config
    project = MagicMock()
    project.rendering_gate_config = None
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = project
    db.execute.return_value = result_mock

    service = RenderingService(db)

    with patch("app.rendering.gate.get_settings") as mock_settings:
        mock_settings.return_value.rendering.gate_mode = "warn"
        mock_settings.return_value.rendering.gate_tier1_threshold = 85.0
        mock_settings.return_value.rendering.gate_tier2_threshold = 70.0
        mock_settings.return_value.rendering.gate_tier3_threshold = 60.0

        # Get default config
        config = await service.get_gate_config(project_id=1)
        assert config.mode == GateMode.warn

        # Update to enforce
        updated = await service.update_gate_config(
            project_id=1,
            update=GateConfigUpdateRequest(mode=GateMode.enforce),
        )
        assert updated.mode == GateMode.enforce
        # Thresholds should be preserved from defaults
        assert updated.tier_thresholds["tier_1"] == 85.0


@pytest.mark.asyncio
async def test_connector_export_gate_block() -> None:
    """Export with enforce mode → RenderingGateBlockedError."""
    from app.rendering.exceptions import RenderingGateBlockedError

    with (
        patch("app.connectors.service.get_settings") as mock_settings,
        patch("app.rendering.gate.get_settings") as mock_gate_settings,
    ):
        mock_settings.return_value.rendering.gate_mode = "enforce"
        mock_gate_settings.return_value.rendering.gate_mode = "enforce"
        mock_gate_settings.return_value.rendering.gate_tier1_threshold = 99.0
        mock_gate_settings.return_value.rendering.gate_tier2_threshold = 99.0
        mock_gate_settings.return_value.rendering.gate_tier3_threshold = 99.0

        from app.connectors.service import ConnectorService

        db = AsyncMock()
        service = ConnectorService(db)

        from app.connectors.schemas import ExportRequest

        data = ExportRequest(
            connector_type="braze",
            build_id=1,
            content_block_name="test",
        )
        user = MagicMock()

        with (
            patch.object(service, "_resolve_html", AsyncMock(return_value=SIMPLE_TABLE_HTML)),
            patch.object(service, "_get_provider", MagicMock()),
            patch.object(service, "_resolve_project_id", AsyncMock(return_value=None)),
            pytest.raises(RenderingGateBlockedError),
        ):
            await service.export(data, user)


@pytest.mark.asyncio
async def test_connector_export_gate_skip() -> None:
    """Export with skip mode → no gate check, proceeds to export."""
    with patch("app.connectors.service.get_settings") as mock_settings:
        mock_settings.return_value.rendering.gate_mode = "skip"

        from app.connectors.service import ConnectorService

        db = AsyncMock()
        service = ConnectorService(db)

        mock_provider = AsyncMock()
        mock_provider.export.return_value = "ext-123"

        from app.connectors.schemas import ExportRequest

        data = ExportRequest(
            connector_type="braze",
            template_version_id=1,
            content_block_name="test",
        )
        user = MagicMock()

        with (
            patch.object(service, "_resolve_html", AsyncMock(return_value=SIMPLE_TABLE_HTML)),
            patch.object(service, "_get_provider", MagicMock(return_value=mock_provider)),
            patch.object(service, "_resolve_credentials", AsyncMock(return_value=None)),
        ):
            result = await service.export(data, user)
            assert result.status == "success"
