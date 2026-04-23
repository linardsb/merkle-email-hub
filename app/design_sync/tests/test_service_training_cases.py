"""Tests for `create_training_case` — ordering + partial-state guarantees."""

from __future__ import annotations

from pathlib import Path

import pytest
from pytest import MonkeyPatch

from app.design_sync.exceptions import TrainingCaseExistsError
from app.design_sync.service import create_training_case


@pytest.mark.asyncio
async def test_create_training_case_rejects_manifest_duplicate_without_writing_files(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """Manifest dup check must fire BEFORE mkdir/writes leave partial state."""
    debug_dir = tmp_path / "debug"
    debug_dir.mkdir()
    manifest_path = debug_dir / "manifest.yaml"
    manifest_path.write_text('cases:\n  - id: "ghost"\n    name: "Stale"\n')

    monkeypatch.setattr("app.design_sync.service._DEBUG_DIR", debug_dir)
    monkeypatch.setattr("app.design_sync.service._MANIFEST_PATH", manifest_path)

    # The directory does NOT exist (simulates out-of-band deletion).
    with pytest.raises(TrainingCaseExistsError):
        await create_training_case(
            case_id="ghost",
            case_name="Ghost",
            html_content="<html></html>",
        )

    # Critical: no partial state left behind.
    assert not (debug_dir / "ghost").exists()
    # Manifest untouched.
    assert manifest_path.read_text().count('id: "ghost"') == 1


@pytest.mark.asyncio
async def test_create_training_case_allows_retry_after_manifest_fix(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """After cleaning a stale manifest entry, retry must succeed.

    Pre-fix, the first attempt left behind an empty ``{case_id}/`` directory,
    and retries then tripped the ``case_dir.exists()`` guard forever.
    """
    debug_dir = tmp_path / "debug"
    debug_dir.mkdir()
    manifest_path = debug_dir / "manifest.yaml"
    manifest_path.write_text('cases:\n  - id: "ghost"\n    name: "Stale"\n')

    monkeypatch.setattr("app.design_sync.service._DEBUG_DIR", debug_dir)
    monkeypatch.setattr("app.design_sync.service._MANIFEST_PATH", manifest_path)

    with pytest.raises(TrainingCaseExistsError):
        await create_training_case(
            case_id="ghost",
            case_name="Ghost",
            html_content="<x/>",
        )

    # Simulate operator removing the stale manifest entry.
    manifest_path.write_text("cases: []\n")

    result = await create_training_case(
        case_id="ghost",
        case_name="Ghost",
        html_content="<x/>",
    )
    assert result["case_id"] == "ghost"
    assert (debug_dir / "ghost" / "expected.html").exists()
