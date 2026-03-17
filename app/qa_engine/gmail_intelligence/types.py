from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class GmailPrediction:
    """Predicted Gmail AI summary for an email."""

    summary_text: str
    predicted_category: str  # Primary, Promotions, Updates, Social, Forums
    key_actions: list[str] = field(default_factory=list)  # pyright: ignore[reportUnknownVariableType]
    promotion_signals: list[str] = field(default_factory=list)  # pyright: ignore[reportUnknownVariableType]
    improvement_suggestions: list[str] = field(default_factory=list)  # pyright: ignore[reportUnknownVariableType]
    confidence: float = 0.0  # 0.0-1.0


@dataclass(frozen=True)
class EmailSignals:
    """Extracted signals from email HTML for category prediction."""

    has_unsubscribe: bool = False
    has_schema_org: bool = False
    cta_count: int = 0
    price_mentions: int = 0
    urgency_words: int = 0
    link_count: int = 0
    image_count: int = 0
    plain_text: str = ""
    preview_text: str = ""


@dataclass(frozen=True)
class OptimizedPreview:
    """Optimized subject/preview text suggestions."""

    original_subject: str
    original_preview: str
    suggested_subjects: list[str] = field(default_factory=list)  # pyright: ignore[reportUnknownVariableType]
    suggested_previews: list[str] = field(default_factory=list)  # pyright: ignore[reportUnknownVariableType]
    reasoning: str = ""
