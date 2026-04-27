# Evaluator Agent

## Purpose

Adversarial evaluation of other agents' output against the original brief and quality criteria. Returns structured accept/revise/reject verdicts with actionable feedback.

## Key Design

- **Different-provider enforcement**: Uses a different LLM provider from the generator to eliminate self-evaluation bias. If generator uses OpenAI, evaluator uses Anthropic (and vice versa).
- **Per-agent criteria**: Loads agent-specific evaluation criteria from YAML files in `criteria/`. Falls back to `generic.yaml` for unknown agents.
- **Structured verdict**: Returns `EvalVerdict` with verdict (accept/revise/reject), score (0.0-1.0), issues list, feedback, and suggested corrections.

## Verdict Logic

- **accept** (score >= 0.8, no critical issues): Output meets quality bar
- **revise** (fixable issues found): Output needs corrections, feedback provided for re-run
- **reject** (fundamental failures): Output is unsalvageable

## Blueprint Integration

`EvaluatorNode` sits after an upstream agent node. On "revise", the engine re-routes to the upstream agent with evaluator feedback injected. Revision cap (`BLUEPRINT__MAX_REVISIONS`, default 2) prevents infinite loops.

## Configuration

- `AI__EVALUATOR__ENABLED`: Enable/disable (default: false)
- `AI__EVALUATOR__PROVIDER`: Override provider (empty = auto-select different)
- `AI__EVALUATOR__CRITERIA_DIR`: Path to criteria YAML files
- `AI__EVALUATOR__MAX_TOKENS`: Max response tokens (default: 2048)
- `BLUEPRINT__MAX_REVISIONS`: Max evaluator-driven revisions (default: 2)
