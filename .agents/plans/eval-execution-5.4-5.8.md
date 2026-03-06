# Plan: Phase 5.4-5.8 Eval Execution

## Context

All eval **tooling** for 5.4-5.8 is built and unit-tested (error_analysis, calibration, scaffold_labels, qa_calibration, blueprint_eval, regression). What remains is the **execution glue** — the tooling currently requires a live LLM provider to generate traces and verdicts. We need to make the full pipeline runnable end-to-end:

1. **5.3** (prerequisite): Run traces → requires LLM provider configured
2. **5.4**: Run error analysis on verdicts
3. **5.5**: Scaffold labels → human labeling → calibrate judges
4. **5.6**: QA gate calibration against human labels
5. **5.7**: Blueprint pipeline eval
6. **5.8**: Establish baseline + regression gate

### Key Insight

The pipeline has two modes:
- **Live mode**: Requires `AI__PROVIDER` + `AI__API_KEY` configured. Calls real LLM for traces + judge verdicts.
- **Dry-run mode** (NEW): Generate mock traces for testing the full pipeline without LLM costs. Useful for CI and local dev.

This plan adds a `--dry-run` flag to the runner and judge_runner so the full pipeline can be exercised without an LLM provider, plus missing Makefile targets and `.gitignore` entries.

## Files to Create/Modify

1. `app/ai/agents/evals/runner.py` — Add `--dry-run` flag that produces mock traces (placeholder HTML + metadata)
2. `app/ai/agents/evals/judge_runner.py` — Add `--dry-run` flag that produces deterministic mock verdicts
3. `app/ai/agents/evals/blueprint_eval.py` — Add `--dry-run` flag with mock blueprint traces
4. `Makefile` — Add `eval-calibrate`, `eval-qa-calibrate`, `eval-dry-run` targets
5. `.gitignore` — Add `traces/` directory
6. `app/ai/agents/evals/mock_traces.py` — **(NEW)** Mock trace/verdict generators for dry-run mode
7. `app/ai/agents/evals/tests/test_dry_run_pipeline.py` — **(NEW)** Integration test: full pipeline dry-run end-to-end

## Implementation Steps

### Step 1: Add `traces/` to `.gitignore`

Edit `.gitignore` — append:
```
# Eval traces (may contain LLM outputs)
traces/
```

### Step 2: Create mock trace generators (`mock_traces.py`)

Create `app/ai/agents/evals/mock_traces.py`:

```python
"""Mock trace and verdict generators for dry-run eval pipeline.

Used by --dry-run mode to exercise the full eval pipeline without LLM calls.
Produces deterministic outputs suitable for testing downstream tools
(error_analysis, calibration, qa_calibration, regression).
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

# Minimal valid email HTML for QA checks to process
MOCK_HTML = """\
<!DOCTYPE html>
<html lang="en" xmlns:v="urn:schemas-microsoft-com:vml">
<head>
<meta charset="utf-8">
<meta name="color-scheme" content="light dark">
<meta name="supported-color-schemes" content="light dark">
<title>Mock Email</title>
<style>
  @media (prefers-color-scheme: dark) {
    .dark-bg { background-color: #1a1a2e !important; }
    .dark-text { color: #ffffff !important; }
  }
  [data-ogsc] .dark-bg { background-color: #1a1a2e !important; }
</style>
</head>
<body style="margin:0; padding:0; background-color:#ffffff;">
<!--[if mso]>
<table role="presentation" width="600" align="center"><tr><td>
<![endif]-->
<table role="presentation" width="100%" style="max-width:600px; margin:0 auto;">
  <tr>
    <td style="padding:20px; font-family:Arial,sans-serif; color:#333333;">
      <img src="https://placehold.co/600x200" alt="Hero banner for spring sale" width="600" height="200" style="display:block; width:100%; height:auto;">
      <h1>Mock Email Content</h1>
      <p>This is a mock email generated for eval pipeline testing.</p>
      <a href="https://example.com/cta" style="display:inline-block; padding:12px 24px; background-color:#007bff; color:#ffffff; text-decoration:none;">Shop Now</a>
    </td>
  </tr>
</table>
<!--[if mso]></td></tr></table><![endif]-->
</body>
</html>"""


def generate_mock_trace(
    case: dict[str, Any],
    agent: str,
) -> dict[str, Any]:
    """Generate a mock trace for a test case without calling LLM."""
    return {
        "id": case["id"],
        "agent": agent,
        "dimensions": case.get("dimensions", []),
        "input": case.get("input", {"brief": case.get("brief", "")}),
        "output": {
            "html": MOCK_HTML,
            "qa_results": [],
            "qa_passed": True,
            "model": "dry-run-mock",
        },
        "expected_challenges": case.get("expected_challenges", []),
        "elapsed_seconds": 0.01,
        "error": None,
        "timestamp": datetime.now(UTC).isoformat(),
    }


def generate_mock_verdict(
    trace: dict[str, Any],
    criteria: list[dict[str, str]],
    fail_rate: float = 0.2,
) -> dict[str, Any]:
    """Generate a mock judge verdict for a trace.

    Args:
        trace: The trace dict to judge.
        criteria: List of {"criterion": name, "description": desc} dicts.
        fail_rate: Fraction of criteria to mark as failed (deterministic by trace_id hash).
    """
    trace_id: str = trace["id"]
    agent: str = trace["agent"]
    hash_val = hash(trace_id)

    criteria_results: list[dict[str, Any]] = []
    for i, crit in enumerate(criteria):
        # Deterministic pass/fail based on trace_id hash + criterion index
        passed = ((hash_val + i) % 5) != 0  # ~20% fail rate
        criteria_results.append({
            "criterion": crit["criterion"],
            "passed": passed,
            "reasoning": f"{'Pass' if passed else 'Fail'}: mock evaluation of {crit['criterion']} for {trace_id}",
        })

    overall_pass = all(cr["passed"] for cr in criteria_results)

    return {
        "trace_id": trace_id,
        "agent": agent,
        "overall_pass": overall_pass,
        "criteria_results": criteria_results,
        "error": None,
    }


# Criteria definitions per agent (mirror judges/)
SCAFFOLDER_CRITERIA: list[dict[str, str]] = [
    {"criterion": "brief_fidelity", "description": "HTML faithfully implements the brief"},
    {"criterion": "email_layout", "description": "Layout uses email-safe patterns"},
    {"criterion": "mso_conditionals", "description": "MSO conditionals correctly structured"},
    {"criterion": "table_structure", "description": "Table-based layout is correct"},
    {"criterion": "code_quality", "description": "Clean, well-structured HTML"},
]

DARK_MODE_CRITERIA: list[dict[str, str]] = [
    {"criterion": "color_coherence", "description": "Dark mode colors visually coherent"},
    {"criterion": "html_preservation", "description": "Original HTML preserved"},
    {"criterion": "outlook_selectors", "description": "Outlook dark mode selectors complete"},
    {"criterion": "media_query", "description": "prefers-color-scheme query present"},
    {"criterion": "meta_tags", "description": "color-scheme meta tags present"},
]

CONTENT_CRITERIA: list[dict[str, str]] = [
    {"criterion": "copy_quality", "description": "Copy is compelling and on-brand"},
    {"criterion": "tone_match", "description": "Tone matches request"},
    {"criterion": "spam_avoidance", "description": "No spam triggers"},
    {"criterion": "length_appropriate", "description": "Content length is appropriate"},
    {"criterion": "grammar", "description": "No grammar or spelling errors"},
]

AGENT_CRITERIA: dict[str, list[dict[str, str]]] = {
    "scaffolder": SCAFFOLDER_CRITERIA,
    "dark_mode": DARK_MODE_CRITERIA,
    "content": CONTENT_CRITERIA,
}


def generate_mock_blueprint_trace(
    brief_def: dict[str, str],
) -> dict[str, Any]:
    """Generate a mock blueprint eval trace."""
    brief_id: str = brief_def["id"]
    hash_val = hash(brief_id)
    retries = hash_val % 3  # 0-2 retries

    return {
        "run_id": brief_id,
        "blueprint_name": "campaign",
        "brief": brief_def["brief"],
        "total_steps": 3 + retries,
        "total_retries": retries,
        "qa_passed": retries < 2,  # Fail if 2 retries
        "final_html_length": len(MOCK_HTML),
        "total_tokens": 1500 + (retries * 500),
        "elapsed_seconds": 0.05,
        "node_trace": [
            {
                "node_name": "scaffolder",
                "node_type": "agent",
                "status": "completed",
                "iteration": 0,
                "duration_ms": 20,
                "summary": "Mock scaffolder output",
            },
            {
                "node_name": "qa_gate",
                "node_type": "gate",
                "status": "passed" if retries == 0 else "failed",
                "iteration": 0,
                "duration_ms": 5,
                "summary": "Mock QA gate",
            },
        ],
        "error": None,
    }
```

### Step 3: Add `--dry-run` to `runner.py`

Modify `app/ai/agents/evals/runner.py`:

1. Add import: `from app.ai.agents.evals.mock_traces import generate_mock_trace`
2. Add `--dry-run` flag to argparse
3. In `run_agent()`, add `dry_run: bool = False` param. When `True`, use `generate_mock_trace(case, agent)` instead of calling the real service
4. Wire through from `main()`:

```python
# In run_agent(), before the case loop:
if dry_run:
    from app.ai.agents.evals.mock_traces import generate_mock_trace as mock_fn
    for i, case in enumerate(cases, 1):
        print(f"  [{i}/{len(cases)}] {case['id']}... (dry-run)", flush=True)
        trace = mock_fn(case, agent)
        traces.append(trace)
    # Write + return
    ...
    return

# In main(), pass dry_run:
parser.add_argument("--dry-run", action="store_true", help="Generate mock traces without LLM")
# ...
await run_agent(agent, args.output, dry_run=args.dry_run)
```

### Step 4: Add `--dry-run` to `judge_runner.py`

Modify `app/ai/agents/evals/judge_runner.py`:

1. Add import: `from app.ai.agents.evals.mock_traces import AGENT_CRITERIA, generate_mock_verdict`
2. Add `--dry-run` flag to argparse
3. In `run_judge()`, add `dry_run: bool = False`. When `True`, skip provider resolution and use `generate_mock_verdict()`:

```python
if dry_run:
    from app.ai.agents.evals.mock_traces import AGENT_CRITERIA, generate_mock_verdict
    criteria = AGENT_CRITERIA.get(agent, [])
    for trace in traces:
        verdict_dict = generate_mock_verdict(trace, criteria)
        verdict = JudgeVerdict(**verdict_dict)
        verdicts.append(verdict)
    # Write + summary + return
```

### Step 5: Add `--dry-run` to `blueprint_eval.py`

Modify `app/ai/agents/evals/blueprint_eval.py`:

1. Add `--dry-run` flag
2. In `run_all_blueprints()`, add `dry_run: bool = False`. When `True`, use `generate_mock_blueprint_trace()` instead of calling real service.

### Step 6: Add missing Makefile targets

Edit `Makefile` to add after existing eval targets:

```makefile
eval-calibrate: ## Calibrate judges against human labels (all 3 agents)
	uv run python -m app.ai.agents.evals.calibration --verdicts traces/scaffolder_verdicts.jsonl --labels traces/scaffolder_human_labels.jsonl --output traces/scaffolder_calibration.json
	uv run python -m app.ai.agents.evals.calibration --verdicts traces/dark_mode_verdicts.jsonl --labels traces/dark_mode_human_labels.jsonl --output traces/dark_mode_calibration.json
	uv run python -m app.ai.agents.evals.calibration --verdicts traces/content_verdicts.jsonl --labels traces/content_human_labels.jsonl --output traces/content_calibration.json

eval-qa-calibrate: ## Calibrate QA gate against human labels (all 3 agents)
	uv run python -m app.ai.agents.evals.qa_calibration --traces traces/scaffolder_traces.jsonl --labels traces/scaffolder_human_labels.jsonl --output traces/qa_calibration_scaffolder.json
	uv run python -m app.ai.agents.evals.qa_calibration --traces traces/dark_mode_traces.jsonl --labels traces/dark_mode_human_labels.jsonl --output traces/qa_calibration_dark_mode.json
	uv run python -m app.ai.agents.evals.qa_calibration --traces traces/content_traces.jsonl --labels traces/content_human_labels.jsonl --output traces/qa_calibration_content.json

eval-dry-run: ## Full eval pipeline dry-run (no LLM needed)
	uv run python -m app.ai.agents.evals.runner --agent all --output traces/ --dry-run
	uv run python -m app.ai.agents.evals.judge_runner --agent all --traces traces --output traces --dry-run
	uv run python -m app.ai.agents.evals.scaffold_labels --verdicts traces/scaffolder_verdicts.jsonl --traces traces/scaffolder_traces.jsonl --output traces/scaffolder_human_labels.jsonl
	uv run python -m app.ai.agents.evals.error_analysis --verdicts traces --output traces/analysis.json
	uv run python -m app.ai.agents.evals.blueprint_eval --output traces/blueprint_traces.jsonl --dry-run
	uv run python -m app.ai.agents.evals.regression --current traces/analysis.json --baseline traces/baseline.json
	@echo "\n=== Dry-run pipeline complete ==="

eval-full: ## Full eval pipeline (requires LLM provider)
	$(MAKE) eval-run
	$(MAKE) eval-judge
	$(MAKE) eval-labels
	$(MAKE) eval-analysis
	$(MAKE) eval-blueprint
	$(MAKE) eval-regression
	@echo "\n=== Full eval pipeline complete ==="
```

Update `.PHONY` line to include new targets.

### Step 7: Integration test (`test_dry_run_pipeline.py`)

Create `app/ai/agents/evals/tests/test_dry_run_pipeline.py`:

Tests:
1. `test_mock_trace_structure` — Verify mock trace has all required fields
2. `test_mock_verdict_structure` — Verify mock verdict has criteria_results
3. `test_mock_verdict_deterministic` — Same trace_id produces same results
4. `test_mock_verdict_has_failures` — Not all verdicts are pass (fail_rate works)
5. `test_mock_blueprint_trace_structure` — Verify blueprint trace fields
6. `test_full_dry_run_pipeline` — Run: mock traces → mock verdicts → error_analysis → scaffold_labels pipeline in-memory
7. `test_mock_html_passes_qa` — Run QA checks on MOCK_HTML, verify most pass

### Step 8: Update `eval-labels` to handle all 3 agents automatically

The current `eval-labels` Makefile target hardcodes 3 separate commands. This is correct — no change needed.

But we need `eval-labels` to also generate labels for dark_mode and content when doing `eval-dry-run`. Update Step 6's `eval-dry-run` to scaffold all 3 agents:

```makefile
eval-dry-run: ## Full eval pipeline dry-run (no LLM needed)
	uv run python -m app.ai.agents.evals.runner --agent all --output traces/ --dry-run
	uv run python -m app.ai.agents.evals.judge_runner --agent all --traces traces --output traces --dry-run
	$(MAKE) eval-labels
	uv run python -m app.ai.agents.evals.error_analysis --verdicts traces --output traces/analysis.json
	uv run python -m app.ai.agents.evals.blueprint_eval --output traces/blueprint_traces.jsonl --dry-run
	uv run python -m app.ai.agents.evals.regression --current traces/analysis.json --baseline traces/baseline.json
	@echo "\n=== Dry-run pipeline complete ==="
```

## Verification

- [ ] `make lint` passes (ruff format + lint on new/modified files)
- [ ] `make types` passes (mypy + pyright on mock_traces.py, modified CLIs)
- [ ] `make test` passes (existing + new tests in test_dry_run_pipeline.py)
- [ ] `make eval-dry-run` executes full pipeline without errors or LLM provider
- [ ] `traces/` directory is gitignored (verify with `git status` after dry-run)
- [ ] Mock traces have all fields expected by downstream tools (error_analysis, scaffold_labels, calibration)
- [ ] `--dry-run` flag does NOT affect default behavior (without flag, real LLM is still called)

## File Summary

| File | Action | Description |
|------|--------|-------------|
| `.gitignore` | Edit | Add `traces/` |
| `app/ai/agents/evals/mock_traces.py` | Create | Mock trace/verdict/blueprint generators |
| `app/ai/agents/evals/runner.py` | Edit | Add `--dry-run` flag + `dry_run` param |
| `app/ai/agents/evals/judge_runner.py` | Edit | Add `--dry-run` flag + `dry_run` param |
| `app/ai/agents/evals/blueprint_eval.py` | Edit | Add `--dry-run` flag + `dry_run` param |
| `Makefile` | Edit | Add `eval-calibrate`, `eval-qa-calibrate`, `eval-dry-run`, `eval-full` targets |
| `app/ai/agents/evals/tests/test_dry_run_pipeline.py` | Create | 7 unit/integration tests |
