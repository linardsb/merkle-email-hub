# Plan: Phase 5.4-5.8 Live Eval Execution

## Context

All eval tooling is built and tested via dry-run. The `traces/` directory contains dry-run mock data (`model: "dry-run-mock"`). What's needed now is **live execution** — running the 36 synthetic test cases through real LLM-backed agents, judging the outputs, establishing a real baseline, and completing the human labeling workflow.

### Current State
- **36 test cases**: 12 scaffolder + 10 dark_mode + 14 content
- **3 LLM judges**: ScaffolderJudge (5 criteria), DarkModeJudge (5 criteria), ContentJudge (5 criteria)
- **Existing traces/**: All dry-run mock data. Must be replaced with real LLM outputs.
- **baseline.json**: Contains dry-run mock pass rates. Must be replaced with real baseline.
- **human_labels.jsonl**: Scaffolded from mock verdicts (`human_pass: null`). Must be regenerated from real verdicts, then manually labeled.

### What This Plan Does NOT Cover
- No code changes to the eval framework itself (tooling is complete)
- No new endpoints, models, or routes (this is CLI execution only)
- No human labeling (that's a manual effort post-execution)

### Prerequisites
- LLM provider configured: `AI__PROVIDER`, `AI__MODEL`, `AI__API_KEY` set in `.env`
- `make eval-verify` passes (provider responds to test request)
- PostgreSQL + Redis running (`make db`) — needed by agent services for QA checks

## Files to Create/Modify

No source files modified. This plan produces data artifacts only:

| Artifact | Description | Produced By |
|----------|-------------|-------------|
| `traces/scaffolder_traces.jsonl` | 12 real LLM traces | `make eval-run` |
| `traces/dark_mode_traces.jsonl` | 10 real LLM traces | `make eval-run` |
| `traces/content_traces.jsonl` | 14 real LLM traces | `make eval-run` |
| `traces/scaffolder_verdicts.jsonl` | 12 judge verdicts | `make eval-judge` |
| `traces/dark_mode_verdicts.jsonl` | 10 judge verdicts | `make eval-judge` |
| `traces/content_verdicts.jsonl` | 14 judge verdicts | `make eval-judge` |
| `traces/scaffolder_human_labels.jsonl` | Label templates (5 judge + 10 QA per trace) | `make eval-labels` |
| `traces/dark_mode_human_labels.jsonl` | Label templates | `make eval-labels` |
| `traces/content_human_labels.jsonl` | Label templates | `make eval-labels` |
| `traces/analysis.json` | Error analysis with failure clusters | `make eval-analysis` |
| `traces/baseline.json` | Baseline pass rates (committed to VCS) | `make eval-baseline` |
| `traces/blueprint_traces.jsonl` | 5 end-to-end blueprint traces | `make eval-blueprint` |

## Implementation Steps

### Step 0: Environment Setup

1. Ensure `.env` has LLM provider configured:
   ```bash
   # Option A: Anthropic (recommended for quality)
   AI__PROVIDER=anthropic
   AI__MODEL=claude-sonnet-4-20250514
   AI__API_KEY=sk-ant-...

   # Option B: OpenAI
   AI__PROVIDER=openai
   AI__MODEL=gpt-4o
   AI__API_KEY=sk-proj-...

   # Option C: Local (Ollama) — lower quality but free
   AI__PROVIDER=ollama
   AI__MODEL=llama3.1:8b
   AI__BASE_URL=http://localhost:11434/v1
   ```

2. Start infrastructure:
   ```bash
   make db              # PostgreSQL + Redis (needed for QA checks)
   make eval-verify     # Verify provider responds
   ```

3. Clear stale dry-run data:
   ```bash
   # Remove dry-run mock traces to start fresh
   rm -f traces/scaffolder_traces.jsonl traces/dark_mode_traces.jsonl traces/content_traces.jsonl
   rm -f traces/scaffolder_verdicts.jsonl traces/dark_mode_verdicts.jsonl traces/content_verdicts.jsonl
   rm -f traces/scaffolder_human_labels.jsonl traces/dark_mode_human_labels.jsonl traces/content_human_labels.jsonl
   rm -f traces/analysis.json traces/blueprint_traces.jsonl
   # Keep baseline.json for now (will be replaced at end)
   ```

### Step 1: Generate Agent Traces (Phase 5.3)

Run all 36 test cases through real agents:

```bash
make eval-run
# Equivalent to: uv run python -m app.ai.agents.evals.runner --agent all --output traces/ --skip-existing
```

**What happens:**
- Scaffolder: 12 briefs → `ScaffolderService().generate()` → HTML output + QA results
- Dark Mode: 10 HTML inputs → `DarkModeService().process()` → Enhanced HTML + QA results
- Content: 14 operation inputs → `ContentService().generate()` → Generated copy

**Expected output:**
- `traces/scaffolder_traces.jsonl` (12 lines, each with `model: "anthropic:claude-..."`)
- `traces/dark_mode_traces.jsonl` (10 lines)
- `traces/content_traces.jsonl` (14 lines)

**Timing:** ~3-5 min (batch size 5, 3s delay between batches)

**If a trace fails** (error in `trace["error"]`):
- The trace is still recorded with `output: null, error: "ErrorType: message"`
- Downstream tools skip traces with null output
- Resume with `--skip-existing` if the process crashes mid-run

**Cost estimate (Anthropic Sonnet):**
- Scaffolder: ~12 × 4K tokens ≈ 48K tokens
- Dark Mode: ~10 × 6K tokens ≈ 60K tokens
- Content: ~14 × 2K tokens ≈ 28K tokens
- Total: ~136K tokens ≈ $0.50-1.00

### Step 2: Generate Judge Verdicts (Phase 5.4 prerequisite)

Run LLM judges on all traces:

```bash
make eval-judge
# Equivalent to: uv run python -m app.ai.agents.evals.judge_runner --agent all --traces traces --output traces --skip-existing
```

**What happens:**
- For each trace with non-null output:
  - Judge builds prompt with criteria definitions + agent input/output
  - Calls LLM with `temperature=0.0` for deterministic evaluation
  - Parses JSON response: `{overall_pass, criteria_results: [{criterion, passed, reasoning}]}`

**Expected output:**
- `traces/scaffolder_verdicts.jsonl` (up to 12 lines, 5 criteria each)
- `traces/dark_mode_verdicts.jsonl` (up to 10 lines, 5 criteria each)
- `traces/content_verdicts.jsonl` (up to 14 lines, 5 criteria each)

**Timing:** ~5-8 min (same batching as runner)

**Cost estimate:** ~36 × 3K tokens ≈ 108K tokens ≈ $0.30-0.60

### Step 3: Error Analysis (Phase 5.4)

Cluster failures from verdicts:

```bash
make eval-analysis
# Equivalent to: uv run python -m app.ai.agents.evals.error_analysis --verdicts traces --output traces/analysis.json
```

**What happens:**
- Loads all `*_verdicts.jsonl` files
- Groups failures by `(agent, criterion)` pair
- Computes per-criterion pass rates
- Identifies top 3 failure modes with sample reasonings

**Expected output:** `traces/analysis.json` with real pass rates and meaningful failure patterns (not "mock evaluation" placeholders).

**Review the analysis:**
- Check `summary.overall_pass_rate` — expect 40-80% for first run
- Check `top_failures` — these are the highest-priority improvement targets
- Check per-criterion rates — any below 0.5 indicates a systematic agent weakness

### Step 4: Scaffold Human Label Templates (Phase 5.5 prerequisite)

Generate label templates from real verdicts:

```bash
make eval-labels
```

**What happens:**
- For each agent, creates a JSONL file with one row per (trace, criterion) pair
- Includes both judge criteria (5 per agent) and QA check criteria (10 per agent)
- Each row has `judge_pass: true/false` (from verdict) and `human_pass: null` (to be filled)

**Expected output:**
- `traces/scaffolder_human_labels.jsonl` (12 × 15 = 180 rows)
- `traces/dark_mode_human_labels.jsonl` (10 × 15 = 150 rows)
- `traces/content_human_labels.jsonl` (14 × 15 = 210 rows)
- Total: 540 label rows (but many are fast to label)

### Step 5: Blueprint Pipeline Evals (Phase 5.7)

Run 5 end-to-end blueprint campaigns:

```bash
make eval-blueprint
# Equivalent to: uv run python -m app.ai.agents.evals.blueprint_eval --output traces/blueprint_traces.jsonl
```

**What happens:**
- Runs 5 test briefs through `BlueprintService().run()`:
  1. `bp-001`: Happy path simple promotional
  2. `bp-002`: Dark mode recovery (newsletter)
  3. `bp-003`: Complex layout retry (product launch)
  4. `bp-004`: Vague brief (minimal spec)
  5. `bp-005`: Accessibility heavy (healthcare)
- Each executes the full campaign graph: scaffolder → qa_gate → maizzle_build → export (with recovery routing on QA failure)

**Expected output:** `traces/blueprint_traces.jsonl` (5 lines with per-node trace, step counts, retries, tokens)

**Timing:** ~10-20 min (multiple LLM calls per blueprint, plus QA + build steps)

**Cost estimate:** ~5 × 20K tokens ≈ 100K tokens ≈ $0.30-0.50

**Key metrics to check:**
- At least 2/5 should show successful self-correction (QA fail → recovery → pass)
- `total_retries` should be 0-2 per brief (bounded self-correction working)
- `total_steps` should be < 20 (safety brake not triggered)

### Step 6: Establish Real Baseline (Phase 5.8)

Replace dry-run baseline with real pass rates:

```bash
# The baseline target runs the full pipeline and copies analysis.json to baseline.json
make eval-baseline
# OR if Steps 1-5 already completed:
cp traces/analysis.json traces/baseline.json
```

**Important:** `traces/baseline.json` is the ONLY traces file committed to version control (see `.gitignore`). Commit it:

```bash
git add traces/baseline.json
git commit -m "eval: establish real baseline from live LLM execution"
```

### Step 7: Human Labeling (Phase 5.5 — Manual Effort)

**This step requires a human email development expert.** It cannot be automated.

1. Open each `*_human_labels.jsonl` file
2. For each row, review the corresponding trace output and fill `human_pass: true/false`
3. Add notes for disagreements with the judge

**Labeling strategy (efficiency):**
- **Start with disagreements**: Focus on rows where you suspect the judge is wrong
- **QA criteria are fast**: Most QA checks (html_validation, link_validation, file_size) can be verified mechanically
- **Judge criteria need expertise**: brief_fidelity, color_coherence, tone_match require email domain knowledge
- **Target**: 20 labels per agent minimum for calibration to be meaningful

**Labeling format** (edit the JSONL directly):
```json
{"trace_id": "scaff-001", "agent": "scaffolder", "criterion": "brief_fidelity", "judge_pass": false, "human_pass": true, "notes": "Judge was too strict on header image requirement"}
```

### Step 8: Judge Calibration (Phase 5.5)

After human labeling is complete:

```bash
make eval-calibrate
```

**What happens:**
- Compares judge verdicts against human labels per criterion
- Computes TPR (True Positive Rate) and TNR (True Negative Rate)
- **Targets:** TPR > 0.85, TNR > 0.80

**Expected output:**
- `traces/scaffolder_calibration.json`
- `traces/dark_mode_calibration.json`
- `traces/content_calibration.json`

**If TPR/TNR below target:**
- Review judge prompt for that criterion — it may be too strict or too lenient
- Check sample mismatches in calibration report
- Iterate: adjust judge prompt → re-run `make eval-judge` → re-calibrate

### Step 9: QA Gate Calibration (Phase 5.6)

```bash
make eval-qa-calibrate
```

**What happens:**
- Runs all 10 QA checks on each trace's HTML
- Compares QA check pass/fail against human labels for QA criteria
- Reports per-check agreement rate

**Expected output:**
- `traces/qa_calibration_scaffolder.json`
- `traces/qa_calibration_dark_mode.json`
- `traces/qa_calibration_content.json`

**Target:** 8/10 checks with agreement > 75%. Checks below threshold need tuning.

### Step 10: Verify Regression Gate (Phase 5.8)

```bash
make eval-check
# Runs: eval-analysis + eval-regression (compares current vs baseline)
```

**Should pass** since current analysis IS the baseline at this point. This validates the regression tooling works with real data.

## Execution Sequence (One-Shot)

For the automated steps (Steps 0-6), use the built-in `make eval-baseline` target:

```bash
# 1. Setup
make db
make eval-verify

# 2. Clear dry-run data
rm -f traces/*_traces.jsonl traces/*_verdicts.jsonl traces/*_human_labels.jsonl
rm -f traces/analysis.json traces/blueprint_traces.jsonl

# 3. Run full pipeline + establish baseline
make eval-baseline

# 4. Verify baseline committed
git add traces/baseline.json
git commit -m "eval: establish real baseline from live LLM execution"
```

Then manual steps:
```bash
# 5. Human labeling (manual — edit *_human_labels.jsonl files)
# 6. After labeling:
make eval-calibrate
make eval-qa-calibrate
# 7. Verify full gate:
make eval-check
```

## Expected Cost

| Step | Provider Calls | Est. Tokens | Est. Cost (Sonnet) |
|------|---------------|-------------|-------------------|
| eval-run (36 traces) | 36 | ~136K | $0.50-1.00 |
| eval-judge (36 verdicts) | 36 | ~108K | $0.30-0.60 |
| eval-blueprint (5 pipelines) | ~25 | ~100K | $0.30-0.50 |
| **Total** | ~97 | ~344K | **$1.10-2.10** |

## Security Checklist

Not applicable — this plan executes existing CLI tools, creates no new endpoints or routes.

- [x] No new API endpoints
- [x] No code modifications to existing source
- [x] LLM API keys stored in `.env` (gitignored)
- [x] Trace JSONL files gitignored (may contain LLM outputs)
- [x] Only `baseline.json` committed (aggregated pass rates, no LLM content)
- [x] Human labels contain no PII (only pass/fail + technical notes)

## Verification

- [ ] `make eval-verify` passes (provider configured)
- [ ] All 36 traces have `model` field != "dry-run-mock"
- [ ] All 36 verdicts have real reasonings (not "mock evaluation")
- [ ] `traces/analysis.json` has meaningful failure patterns
- [ ] `traces/baseline.json` committed with real pass rates
- [ ] Blueprint evals show at least 2/5 successful self-corrections
- [ ] After human labeling: `make eval-calibrate` shows TPR > 0.85, TNR > 0.80
- [ ] After human labeling: `make eval-qa-calibrate` shows 8/10 checks > 75% agreement
- [ ] `make eval-check` passes (no regressions vs baseline)

## Post-Execution: Unblocked Tasks

Completing this plan unblocks:
1. **Phase 7.2** (Eval-Informed Agent Prompts) — needs real failure patterns from error analysis
2. **Task 4.1** (Remaining 6 Agents) — baseline establishes quality bar for new agents
3. **Phase 5.8 CI integration** — regression gate ready for `.github/workflows/ci.yml`
