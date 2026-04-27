"""Spam-trigger phrases loaded from `data/spam_triggers.yaml`.

Relocated from `checks.spam_score` so consumers don't depend on the spam-score
check class (which is being absorbed by the `RuleEngineCheck` factory).

`SPAM_TRIGGERS` is the flat list of trigger phrases (strings only) used by
the content agent for upstream phrase suggestions; the spam-score *check*
itself reads the same YAML via `custom_checks.spam` for its weighted scoring.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_TRIGGERS_PATH = Path(__file__).parent / "data" / "spam_triggers.yaml"


def _load_trigger_phrases() -> list[str]:
    if not _TRIGGERS_PATH.exists():
        return []
    with _TRIGGERS_PATH.open() as f:
        data: dict[str, Any] = yaml.safe_load(f) or {}
    return [str(t.get("phrase", "")) for t in data.get("triggers", [])]


SPAM_TRIGGERS: list[str] = _load_trigger_phrases()

__all__ = ["SPAM_TRIGGERS"]
