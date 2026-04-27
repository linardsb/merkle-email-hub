"""Evaluator agent — adversarial evaluation of other agents' output."""

from app.ai.agents.evaluator.service import EvaluatorAgentService

_evaluator_service: EvaluatorAgentService | None = None


def get_evaluator_service() -> EvaluatorAgentService:
    """Get or create the Evaluator service singleton."""
    global _evaluator_service
    if _evaluator_service is None:
        _evaluator_service = EvaluatorAgentService()
    return _evaluator_service
