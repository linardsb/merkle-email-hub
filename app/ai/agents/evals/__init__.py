"""Agent evaluation framework — synthetic data, trace runner, and LLM judges."""

from app.ai.agents.evals.golden_references import (
    GoldenReference as GoldenReference,
)
from app.ai.agents.evals.golden_references import (
    get_references_for_agent as get_references_for_agent,
)
from app.ai.agents.evals.golden_references import (
    get_references_for_criterion as get_references_for_criterion,
)
from app.ai.agents.evals.judges import JUDGE_REGISTRY as JUDGE_REGISTRY
