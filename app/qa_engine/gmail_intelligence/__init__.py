"""Gmail AI Intelligence — Summary prediction and preview optimization."""

from app.qa_engine.gmail_intelligence.html_extractor import extract_signals
from app.qa_engine.gmail_intelligence.optimizer import PreviewTextOptimizer
from app.qa_engine.gmail_intelligence.predictor import GmailSummaryPredictor
from app.qa_engine.gmail_intelligence.types import (
    EmailSignals,
    GmailPrediction,
    OptimizedPreview,
)

__all__ = [
    "EmailSignals",
    "GmailPrediction",
    "GmailSummaryPredictor",
    "OptimizedPreview",
    "PreviewTextOptimizer",
    "extract_signals",
]
