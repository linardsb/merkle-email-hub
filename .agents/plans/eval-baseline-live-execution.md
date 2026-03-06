# Plan: Step 0 — Eval Baseline (Phase 5.4-5.8 Live Execution)

## Context

All eval **tooling** is built and dry-run tested (58 unit tests passing). What remains is **live execution** — running the 36 synthetic test cases through real LLM providers to establish baseline metrics. This is the critical prerequisite for Phase 7 (agent capability improvements) and Phase 8 (knowledge graph). Without a baseline, we can't measure whether any subsequent work actually helps.

### What's Already Built
- Runner CLI with `--dry-run` flag (`runner.py`)
- Judge runner CLI with `--dry-run`, `--provider`, `--model`, `--batch-size`, `--delay` flags (`judge_runner.py`)
- Error analysis CLI (`error_analysis.py`)
- Label scaffolding CLI (`scaffold_labels.py`)
- Calibration CLI (`calibration.py`)
- QA calibration CLI (`qa_calibration.py`)
- Blueprint eval CLI with `--dry-run` (`blueprint_eval.py`)
- Regression detection CLI (`regression.py`)
- Mock trace generators (`mock_traces.py`)
- Makefile targets: `eval-run`, `eval-judge`, `eval-labels`, `eval-analysis`, `eval-blueprint`, `eval-regression`, `eval-check`, `eval-calibrate`, `eval-qa-calibrate`, `eval-dry-run`, `eval-full`

### What This Plan Covers
1. **5.3** — Run 36 test cases through 3 agents with a real LLM → collect JSONL traces
2. **5.4** — Run judges on traces → error analysis → failure taxonomy
3. **5.5** — Scaffold human labels → manual labeling guide → calibrate judges
4. **5.6** — QA gate calibration against human labels
5. **5.7** — Blueprint pipeline end-to-end eval (5 test briefs)
6. **5.8** — Establish baseline → store in version control

### Cost Estimate (Claude Sonnet for judges, provider-dependent for agents)

| Step | LLM Calls | Estimated Tokens | Estimated Cost |
|------|-----------|-----------------|----------------|
| 5.3 Runner (36 traces) | 36 agent calls | ~180K input + ~108K output | ~$2.16 (Sonnet) |
| 5.4 Judge (36 verdicts) | 36 judge calls | ~144K input + ~36K output | ~$0.97 (Sonnet) |
| 5.7 Blueprint (5 briefs) | ~15 node calls | ~75K input + ~45K output | ~$0.90 (Sonnet) |
| **Total** | **~87 calls** | **~588K tokens** | **~$4.03** |

Human labeling (5.5-5.6) is manual effort, not LLM cost.

## Prerequisites

Before starting, the user must configure an LLM provider:

```bash
# Option A: Anthropic (recommended for eval quality)
export AI__PROVIDER=anthropic
export AI__API_KEY=sk-ant-...
export AI__MODEL=claude-sonnet-4-20250514

# Option B: OpenAI-compatible
export AI__PROVIDER=openai
export AI__API_KEY=sk-...
export AI__MODEL=gpt-4o
export AI__BASE_URL=https://api.openai.com/v1  # optional, default

# Option C: Local (Ollama) — free but lower quality baseline
export AI__PROVIDER=openai
export AI__MODEL=qwen2.5-coder:32b
export AI__BASE_URL=http://localhost:11434/v1
export AI__API_KEY=ollama
```

Verify provider works: `uv run python -c "import asyncio; from app.ai.registry import get_registry; from app.ai.protocols import Message; from app.core.config import get_settings; s=get_settings(); r=get_registry(); p=r.get_llm(s.ai.provider); print(asyncio.run(p.complete([Message(role='user', content='Say hello')])))"` — should print a CompletionResponse.

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `app/ai/agents/evals/runner.py` | Modify | Add `--batch-size` and `--delay` flags for rate limiting during live runs |
| `app/ai/agents/evals/blueprint_eval.py` | Modify | Add `--provider` and `--model` override flags (consistency with judge_runner) |
| `traces/baseline.json` | Create | Baseline analysis JSON committed to version control |
| `traces/.gitkeep` | Create | Ensure traces dir exists; actual traces remain gitignored |
| `.gitignore` | Modify | Ensure `traces/*.jsonl` ignored but `traces/baseline.json` tracked |
| `docs/eval-labeling-guide.md` | Create | Instructions for human labeling of eval outputs |
| `Makefile` | Modify | Add `eval-baseline` target that runs full pipeline + stores baseline |

## Implementation Steps

### Step 1: Add rate limiting to runner.py (prevent API throttling)

The runner currently fires all 36 cases sequentially but without configurable delays. For live execution against rate-limited APIs, add batch/delay controls matching `judge_runner.py`.

Edit `app/ai/agents/evals/runner.py`:

1. Add CLI args after existing args:
```python
parser.add_argument("--batch-size", type=int, default=5,
                    help="Traces per batch before delay (default: 5)")
parser.add_argument("--delay", type=float, default=3.0,
                    help="Seconds between batches (default: 3.0)")
```

2. In the `run_agent()` function, add `batch_size: int = 5, delay: float = 3.0` params.

3. After each case execution (in the for loop over cases), add batching logic:
```python
if not dry_run and (i % batch_size == 0) and i < len(cases):
    print(f"  Rate limit pause ({delay}s)...", flush=True)
    await asyncio.sleep(delay)
```

4. Wire through from `main()`:
```python
await run_agent(agent, args.output, dry_run=args.dry_run,
                batch_size=args.batch_size, delay=args.delay)
```

### Step 2: Add provider/model overrides to blueprint_eval.py

Edit `app/ai/agents/evals/blueprint_eval.py`:

1. Add CLI args:
```python
parser.add_argument("--provider", type=str, default=None,
                    help="Override AI provider (default: from config)")
parser.add_argument("--model", type=str, default=None,
                    help="Override model (default: from config)")
```

2. If `--provider` or `--model` are set, temporarily override `settings.ai.provider` / `settings.ai.model` before calling `BlueprintService.run()`. Use environment variable injection:
```python
import os
if args.provider:
    os.environ["AI__PROVIDER"] = args.provider
if args.model:
    os.environ["AI__MODEL"] = args.model
```

Note: This works because `get_settings()` is `@lru_cache` — we need to clear it. Add after env override:
```python
from app.core.config import get_settings
get_settings.cache_clear()
```

### Step 3: Update .gitignore for baseline tracking

Edit `.gitignore` — the current entry is `traces/`. Change to:
```gitignore
# Eval traces (may contain LLM outputs)
traces/*.jsonl
traces/*.json
!traces/baseline.json
traces/.gitkeep
```

This ignores all trace/verdict/analysis files but explicitly tracks `baseline.json`.

### Step 4: Create traces directory with .gitkeep

```bash
mkdir -p traces
touch traces/.gitkeep
```

### Step 5: Create human labeling guide

Create `docs/eval-labeling-guide.md`:

```markdown
# Eval Human Labeling Guide

## Overview

After running the eval pipeline (`make eval-run` + `make eval-judge` + `make eval-labels`),
you'll have human label template files in `traces/`:

- `traces/scaffolder_human_labels.jsonl`
- `traces/dark_mode_human_labels.jsonl`
- `traces/content_human_labels.jsonl`

Each file contains one JSON object per line. Your job is to fill in the `human_pass` field.

## Label Format

Each line looks like:
```json
{"trace_id": "scaff-001", "agent": "scaffolder", "criterion": "brief_fidelity", "judge_pass": true, "human_pass": null, "notes": ""}
```

**Your task:** Change `"human_pass": null` to `"human_pass": true` or `"human_pass": false`.

## How to Label

### Step 1: Open the traces file
Read the agent's trace file (e.g., `traces/scaffolder_traces.jsonl`) to see what the agent produced.
Each trace has an `output.html` field — this is what you're evaluating.

### Step 2: For each criterion, evaluate the output

**Judge criteria** (prefilled with judge's verdict in `judge_pass`):
- Read the criterion name and description
- Look at the agent's HTML output
- Decide: does this output PASS or FAIL for this criterion?
- Set `human_pass` to `true` or `false`
- Optionally add notes explaining your reasoning

**QA check criteria** (10 checks, `judge_pass` is null):
- These compare QA gate results to your judgment
- Look at the HTML and decide if each QA check SHOULD pass
- The QA gate's actual result is in the trace's `qa_results` field

### Step 3: Save the file

Keep it as valid JSONL (one JSON object per line, no trailing commas).

## Criteria Reference

### Scaffolder (5 judge criteria)
| Criterion | Pass if... |
|-----------|-----------|
| `brief_fidelity` | HTML implements all sections/elements requested in the brief |
| `email_layout` | Uses table-based layout, max-width 600px, cellpadding=0 |
| `mso_conditionals` | Has `<!--[if mso]>` blocks where needed (widths, VML) |
| `table_structure` | Tables are properly nested, no broken nesting |
| `code_quality` | Clean indentation, no redundant wrappers, semantic where possible |

### Dark Mode (5 judge criteria)
| Criterion | Pass if... |
|-----------|-----------|
| `color_coherence` | Dark colors are actually dark (not inverted to light) |
| `html_preservation` | No elements removed, layout structure identical to input |
| `outlook_selectors` | `[data-ogsc]`/`[data-ogsb]` selectors for all color overrides |
| `media_query` | `@media (prefers-color-scheme: dark)` block present and correct |
| `meta_tags` | `<meta name="color-scheme">` and `<meta name="supported-color-schemes">` present |

### Content (5 judge criteria)
| Criterion | Pass if... |
|-----------|-----------|
| `copy_quality` | Compelling, clear, scannable copy |
| `tone_match` | Matches the requested tone (formal, casual, urgent, etc.) |
| `spam_avoidance` | No ALL CAPS, excessive punctuation, or spam trigger phrases |
| `length_appropriate` | Meets length constraints for the operation type |
| `grammar` | No grammar or spelling errors |

### QA Gate Checks (10 criteria for all agents)
| Check | Pass if... |
|-------|-----------|
| `html_validation` | Valid DOCTYPE, html/head/body structure |
| `css_support` | No CSS properties with poor email client support |
| `file_size` | HTML < 102KB (Gmail clipping threshold) |
| `link_validation` | All links use HTTPS, valid protocols |
| `spam_score` | No common spam trigger words |
| `dark_mode` | color-scheme meta, prefers-color-scheme media query |
| `accessibility` | lang attribute, alt text on images, table roles |
| `fallback` | MSO conditional comments present |
| `image_optimization` | Images have explicit width/height, valid formats |
| `brand_compliance` | Passes brand rules (placeholder — usually passes) |

## Target Labels Per Agent

Aim for **20 labeled outputs per agent** (minimum for calibration).
The scaffolder has 12 traces, dark mode 10, content 14 — label all of them.

Each trace produces ~15 label rows (5 judge + 10 QA = 15 per trace).
Total labeling effort: ~540 rows across all 3 agents.

## Calibration Targets

After labeling, run `make eval-calibrate` and `make eval-qa-calibrate`.

- **Judge calibration:** TPR >= 0.85, TNR >= 0.80 per criterion
- **QA calibration:** Agreement rate >= 75% per check

If targets aren't met, iterate on judge prompts or QA check thresholds.
```

### Step 6: Add eval-baseline Makefile target

Edit `Makefile` — add after `eval-full`:

```makefile
eval-baseline: ## Run full eval pipeline and establish baseline (first time)
	$(MAKE) eval-run
	$(MAKE) eval-judge
	$(MAKE) eval-labels
	$(MAKE) eval-analysis
	$(MAKE) eval-blueprint
	cp traces/analysis.json traces/baseline.json
	@echo "\n=== Baseline established at traces/baseline.json ==="
	@echo "Commit traces/baseline.json to version control."
```

Update `.PHONY` to include `eval-baseline`.

### Step 7: Verify dry-run still works after changes

Run `make eval-dry-run` to confirm the rate-limiting additions don't break dry-run mode (delay should be skipped when `dry_run=True`).

## Execution Runbook (For the User)

This is the sequence the user follows after the code changes are made:

### Phase A: Generate Traces (Task 5.3)

```bash
# 1. Configure provider (see Prerequisites above)
export AI__PROVIDER=anthropic
export AI__API_KEY=sk-ant-...
export AI__MODEL=claude-sonnet-4-20250514

# 2. Run all 36 test cases through agents (est. 10-15 min)
make eval-run
# Output: traces/scaffolder_traces.jsonl (12 traces)
#         traces/dark_mode_traces.jsonl (10 traces)
#         traces/content_traces.jsonl (14 traces)

# 3. Spot-check: view a trace
head -1 traces/scaffolder_traces.jsonl | python -m json.tool | head -20
```

### Phase B: Judge Traces + Error Analysis (Task 5.4)

```bash
# 4. Run judges on all traces (est. 5-8 min)
make eval-judge
# Output: traces/scaffolder_verdicts.jsonl
#         traces/dark_mode_verdicts.jsonl
#         traces/content_verdicts.jsonl

# 5. Run error analysis
make eval-analysis
# Output: traces/analysis.json
# Console shows: pass rates, top 3 failure clusters

# 6. Review failure taxonomy
cat traces/analysis.json | python -m json.tool
```

### Phase C: Human Labeling (Task 5.5 — Manual Effort)

```bash
# 7. Generate label templates
make eval-labels
# Output: traces/scaffolder_human_labels.jsonl
#         traces/dark_mode_human_labels.jsonl
#         traces/content_human_labels.jsonl

# 8. Label outputs (see docs/eval-labeling-guide.md)
# Open each *_human_labels.jsonl file
# For each row, set "human_pass": true or false
# Estimated effort: 2-4 hours for all 3 agents (~540 rows)

# 9. Calibrate judges
make eval-calibrate
# Output: traces/scaffolder_calibration.json
#         traces/dark_mode_calibration.json
#         traces/content_calibration.json
# Console shows: TPR/TNR per criterion, pass/fail status
```

### Phase D: QA Gate Calibration (Task 5.6)

```bash
# 10. Calibrate QA checks against human labels
make eval-qa-calibrate
# Output: traces/qa_calibration_scaffolder.json
#         traces/qa_calibration_dark_mode.json
#         traces/qa_calibration_content.json
# Console shows: per-check agreement rates, checks needing tuning
```

### Phase E: Blueprint Pipeline Eval (Task 5.7)

```bash
# 11. Run blueprint end-to-end eval (5 test briefs, est. 5-10 min)
make eval-blueprint
# Output: traces/blueprint_traces.jsonl
# Console shows: QA pass rate, avg steps/retries/tokens
```

### Phase F: Establish Baseline (Task 5.8)

```bash
# 12. Store baseline
make eval-baseline
# (Re-runs full pipeline if traces don't exist, then copies analysis.json to baseline.json)

# 13. Commit baseline to version control
git add traces/baseline.json traces/.gitkeep
git commit -m "eval: establish baseline pass rates for 3 agents (Phase 5.8)"

# 14. Verify regression gate works
make eval-check
# Should exit 0 (no regression against self)
```

## Iteration Guidance

### If judge calibration fails (TPR < 0.85 or TNR < 0.80):
1. Check `traces/*_calibration.json` → `needs_attention` array
2. For each failing criterion, review the judge prompt in `app/ai/agents/evals/judges/{agent}.py`
3. Adjust the criterion description or add examples
4. Re-run: `make eval-judge` → `make eval-calibrate`
5. Repeat until targets met

### If QA calibration shows checks < 75% agreement:
1. Check `traces/qa_calibration_*.json` → `needs_tuning` array
2. Review the check implementation in `app/qa_engine/checks/{check_name}.py`
3. Adjust thresholds or detection logic
4. Re-run: `make eval-qa-calibrate`

### If error analysis reveals systematic failures:
1. Check `traces/analysis.json` → `top_failures` array
2. Review the agent's system prompt for the failing pattern
3. Add explicit instructions or examples addressing the failure
4. Re-run: `make eval-run` → `make eval-judge` → `make eval-analysis`
5. Compare against baseline: `make eval-check`

## Verification

- [ ] `make lint` passes
- [ ] `make types` passes
- [ ] `make test` passes (existing 58 eval tests unbroken)
- [ ] `make eval-dry-run` still works (rate limiting skipped in dry-run)
- [ ] `make eval-run` generates 36 JSONL traces (with real LLM configured)
- [ ] `make eval-judge` generates 36 JSONL verdicts
- [ ] `make eval-analysis` produces analysis.json with pass rates
- [ ] `make eval-labels` generates ~540 label template rows
- [ ] `make eval-calibrate` produces calibration results (after manual labeling)
- [ ] `make eval-qa-calibrate` produces QA calibration results (after manual labeling)
- [ ] `make eval-blueprint` generates 5 blueprint traces
- [ ] `make eval-baseline` stores baseline.json
- [ ] `make eval-check` exits 0 (no regression against baseline)
- [ ] `traces/baseline.json` is tracked in git, all other traces/* are gitignored
