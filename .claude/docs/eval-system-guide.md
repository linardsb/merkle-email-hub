---
purpose: Eval system internals — judge prompts, calibration, regression gates, production sampling, golden tests
when-to-use: When modifying agent behavior, adding new judges, debugging eval failures, or working on eval infrastructure
size: ~200 lines
source: app/ai/agents/evals/
---

<!-- Scout header above. Sub-agents: read ONLY the header to decide relevance. Load full content only if needed. -->

# Eval System Guide

## Overview

The eval system validates AI agent quality through binary pass/fail LLM judges. Each of the 9 agents has a 5-criteria judge. The system supports synthetic test data, production trace sampling, calibration against human labels, and regression detection.

## Key Commands

```bash
make eval-full       # Full eval pipeline (requires LLM) — synthetic + production
make eval-check      # Eval gate: analysis + regression detection
make eval-golden     # CI golden test: 7 deterministic templates, no LLM
make eval-qa-coverage # Deterministic micro-judges coverage
make eval-suggest    # Generate SKILL.md amendment suggestions from failures
make eval-refresh    # Merge production verdicts into analysis
```

## Judge Architecture

### Judge Prompt Structure
Each judge in `app/ai/agents/evals/judges/` defines 5 binary criteria. Judges receive the agent's input (brief/context) and output (HTML/decisions), then return pass/fail per criterion.

### Judge Runner (`judge_runner.py`)
- Runs judge prompts against agent outputs
- `temperature=0.0` for reproducibility
- Failure-safe: judge errors don't block pipeline

### Inline Judges (`app/ai/blueprints/inline_judge.py`)
- Bridge `JUDGE_REGISTRY` into live blueprint execution
- Only run on retry attempts (`iteration > 0`)
- Lightweight model tier
- Config: `BLUEPRINT__JUDGE_ON_RETRY=true`

## Calibration (`calibration.py`)

Calibrates judges against human-labeled data:
- Target: TPR (True Positive Rate) and TNR (True Negative Rate)
- Process: run judge on labeled examples, compute rates, adjust thresholds
- Output: calibration metrics per agent per criterion

## Regression Detection (`regression.py`)

- Compares current eval run against baseline
- Per-agent tolerance: 3 percentage points (`AGENT_REGRESSION_TOLERANCE`)
- Fails CI if any agent drops beyond tolerance
- Tracks per-criterion and aggregate pass rates

## Golden Cases (`golden_cases.py`)

7 deterministic test templates for CI (`make eval-golden`):
- No LLM calls — validates pipeline mechanics
- Checks: template selection, slot filling, HTML structure
- Fast: runs in seconds

## Production Sampling (`production_sampler.py`)

Closes the eval feedback loop:
1. Successful blueprint runs probabilistically enqueued to Redis
2. `ProductionJudgeWorker` (DataPoller) processes queue with LLM judges
3. Verdicts append to `traces/production_verdicts.jsonl`
4. `refresh_analysis()` merges with synthetic verdicts into `traces/analysis.json`
5. `failure_warnings.py` reads merged analysis — agents learn from production failures

Config: `EVAL__PRODUCTION_SAMPLE_RATE` (default `0.0` = disabled)

## Synthetic Test Data

- `synthetic_data_*.py` files generate test inputs per agent
- Scaffolder has 22 test cases (10 template selection edge cases)
- Each synthetic case has expected outcomes for judge validation

## Amendment Suggester (`amendment_suggester.py`)

- Groups eval failures by agent + failure category
- Generates SKILL.md amendment diffs for clusters with 3+ occurrences
- Output: `traces/suggestions/` directory
- Review-only — never auto-applies changes

## Adding a New Judge

1. Create `app/ai/agents/evals/judges/{agent}_judge.py`
2. Define 5 binary criteria relevant to the agent's output quality
3. Register in `JUDGE_REGISTRY` in `judge_runner.py`
4. Add synthetic test cases in `synthetic_data_{agent}.py`
5. Run `make eval-full` to establish baseline
6. Run `make eval-check` to verify no regressions
