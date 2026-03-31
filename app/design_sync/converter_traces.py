"""JSONL trace writer for converter quality data.

Writes per-conversion traces to a JSONL file for regression detection and
observability.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from app.core.config import get_settings
from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.design_sync.converter_service import ConversionResult

logger = get_logger(__name__)

_DEFAULT_TRACES_PATH = Path("traces/converter_traces.jsonl")


def compute_quality_score(result: ConversionResult) -> float:
    """Compute a weighted quality score from conversion results.

    Components:
    - avg_confidence * 0.5 (component matching quality)
    - (1 - warning_ratio) * 0.3
    - (1 - error_ratio) * 0.2
    """
    confidences = list(result.match_confidences.values())
    avg_confidence = sum(confidences) / len(confidences) if confidences else 1.0

    sections = max(result.sections_count, 1)
    warning_ratio = min(len(result.quality_warnings) / sections, 1.0)

    error_count = sum(1 for w in result.quality_warnings if w.severity == "error")
    total_warnings = len(result.quality_warnings)
    error_ratio = error_count / total_warnings if total_warnings else 0.0

    return avg_confidence * 0.5 + (1 - warning_ratio) * 0.3 + (1 - error_ratio) * 0.2


def build_trace(result: ConversionResult, connection_id: str | None) -> dict[str, Any]:
    """Build a trace dict from a ConversionResult."""
    confidences = list(result.match_confidences.values())
    trace_id = f"conv-{connection_id or 'none'}-{uuid.uuid4().hex[:8]}"

    return {
        "trace_id": trace_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "connection_id": connection_id,
        "figma_url": result.figma_url,
        "node_id": result.node_id,
        "sections_count": result.sections_count,
        "warnings": [
            {"category": w.category, "severity": w.severity, "message": w.message}
            for w in result.quality_warnings
        ],
        "match_confidences": {str(k): v for k, v in result.match_confidences.items()},
        "avg_confidence": sum(confidences) / len(confidences) if confidences else 1.0,
        "min_confidence": min(confidences) if confidences else 1.0,
        "quality_score": compute_quality_score(result),
        "compatibility_hint_count": len(result.compatibility_hints),
        "cache_hit_rate": result.cache_hit_rate,
        "design_tokens_used": result.design_tokens_used,
    }


def append_trace(trace: dict[str, Any], path: Path | None = None) -> None:
    """Append a trace as a JSONL line. Creates file if needed."""
    trace_path = path or _DEFAULT_TRACES_PATH
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    with trace_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(trace, default=str) + "\n")


async def persist_converter_trace(
    result: ConversionResult,
    connection_id: str | None,
) -> None:
    """Build and append a converter trace. Fire-and-forget."""
    try:
        settings = get_settings()
        if not settings.design_sync.conversion_traces_enabled:
            return

        trace = build_trace(result, connection_id)
        trace_path = Path(settings.design_sync.conversion_traces_path)
        append_trace(trace, trace_path)

        logger.info(
            "converter_traces.appended",
            trace_id=trace["trace_id"],
            quality_score=trace["quality_score"],
        )
    except Exception:
        logger.warning(
            "converter_traces.persist_failed",
            connection_id=connection_id,
            exc_info=True,
        )
