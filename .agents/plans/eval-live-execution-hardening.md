# Plan: Eval Live Execution Hardening

## Context

All eval **tooling** is built and dry-run tested (58 unit tests, all Makefile targets working). The existing plan (`.agents/plans/eval-baseline-live-execution.md`) and its code changes are fully merged. What remains before live execution are **reliability gaps** that risk wasting LLM budget (~$4 across ~87 API calls):

1. **No incremental trace writing** — `runner.py` accumulates all traces in memory, writes at end. If it crashes after 30/36 cases (network error, rate limit, OOM), all work is lost.
2. **No provider pre-flight check** — No way to verify LLM provider works before committing to 87 API calls.
3. **No resume capability** — After a partial failure, must re-run all cases from scratch.

These are small, focused changes that make live execution reliable.

## Files to Modify

| File | Change |
|------|--------|
| `app/ai/agents/evals/runner.py` | Incremental JSONL writing + `--skip-existing` flag |
| `app/ai/agents/evals/judge_runner.py` | Incremental JSONL writing (same pattern) |
| `app/ai/agents/evals/verify_provider.py` | **NEW** — Pre-flight provider check script |
| `Makefile` | Add `eval-verify` target |

## Implementation Steps

### Step 1: Add incremental trace writing to runner.py

**Problem:** Lines 208-229 accumulate all traces in a list, write at end. A crash at trace 30/36 loses everything.

**Fix:** Open the output file at start, append each trace as it completes.

In `run_agent()`, replace the current pattern:

```python
# BEFORE (accumulate + batch write)
traces = []
# ... loop appends to traces ...
with Path.open(output_file, "w") as f:
    for trace in traces:
        f.write(json.dumps(trace) + "\n")
```

With incremental writing:

```python
# AFTER (write each trace immediately)
trace_count = 0
error_count = 0

# Determine write mode based on skip_existing
existing_ids: set[str] = set()
if skip_existing and output_file.exists():
    with Path.open(output_file) as f:
        for line in f:
            line = line.strip()
            if line:
                existing_ids.add(json.loads(line)["id"])
    mode = "a"  # append to existing
else:
    mode = "w"  # overwrite

with Path.open(output_file, mode) as f:
    if dry_run:
        from app.ai.agents.evals.mock_traces import generate_mock_trace

        for i, case in enumerate(cases, 1):
            if case["id"] in existing_ids:
                print(f"  [{i}/{len(cases)}] {case['id']}... SKIPPED (exists)")
                trace_count += 1
                continue
            print(f"  [{i}/{len(cases)}] {case['id']}... (dry-run)")
            trace = generate_mock_trace(case, agent)
            f.write(json.dumps(trace) + "\n")
            f.flush()
            trace_count += 1
    else:
        for i, case in enumerate(cases, 1):
            if case["id"] in existing_ids:
                print(f"  [{i}/{len(cases)}] {case['id']}... SKIPPED (exists)")
                trace_count += 1
                continue
            print(f"  [{i}/{len(cases)}] {case['id']}...", end=" ", flush=True)
            trace = await runner(case)
            f.write(json.dumps(trace) + "\n")
            f.flush()
            trace_count += 1
            if trace["error"] is not None:
                error_count += 1
            status = "OK" if trace["error"] is None else f"ERROR: {trace['error']}"
            print(f"{status} ({trace['elapsed_seconds']}s)")
            if (i % batch_size == 0) and i < len(cases):
                print(f"  Rate limit pause ({delay}s)...", flush=True)
                await asyncio.sleep(delay)

passed = trace_count - error_count
total = trace_count + len(existing_ids) if not skip_existing else trace_count
print(f"\nDone: {passed}/{total} succeeded. Traces: {output_file}")
```

Add `--skip-existing` CLI arg:

```python
parser.add_argument(
    "--skip-existing", action="store_true",
    help="Skip test cases already in output file (resume after crash)"
)
```

Add `skip_existing: bool = False` parameter to `run_agent()` signature. Wire through from `main()`.

**Key behaviors:**
- Each trace written + flushed immediately (survives crashes)
- `--skip-existing` reads existing trace IDs, skips them, appends new ones
- Without `--skip-existing`, overwrites as before (clean run)
- `f.flush()` after each write ensures OS buffer is flushed

### Step 2: Add incremental writing to judge_runner.py

Same pattern for `run_judge()`. Currently lines 133-193 accumulate verdicts in a list.

In `run_judge()`, replace:

```python
# BEFORE
verdicts: list[JudgeVerdict] = []
# ... loop appends ...
with Path.open(output_path, "w") as f:
    for verdict in verdicts:
        f.write(json.dumps(verdict.model_dump()) + "\n")
```

With:

```python
# AFTER
verdicts: list[JudgeVerdict] = []  # keep for summary stats

existing_ids: set[str] = set()
if skip_existing and output_path.exists():
    with Path.open(output_path) as f:
        for line in f:
            line = line.strip()
            if line:
                data = json.loads(line)
                existing_ids.add(data["trace_id"])
                verdicts.append(JudgeVerdict(**data))
    mode = "a"
else:
    mode = "w"

with Path.open(output_path, mode) as f:
    # ... existing loop, but:
    # 1. Skip traces whose trace_id is in existing_ids
    # 2. Write each verdict immediately with f.flush()
    # 3. Append to verdicts list for summary
```

Add `skip_existing: bool = False` param + `--skip-existing` CLI arg (same as runner).

### Step 3: Create provider verification script

Create `app/ai/agents/evals/verify_provider.py`:

```python
"""Pre-flight check: verify LLM provider is configured and responding.

Usage:
    python -m app.ai.agents.evals.verify_provider
    make eval-verify
"""

import asyncio
import sys
import time

from app.ai.protocols import Message
from app.ai.registry import get_registry
from app.core.config import get_settings


async def verify() -> bool:
    """Verify provider can complete a simple request."""
    settings = get_settings()
    provider_name = settings.ai.provider
    model = settings.ai.model
    api_key = settings.ai.api_key

    print("=== Eval Provider Pre-Flight Check ===")
    print(f"  Provider: {provider_name}")
    print(f"  Model:    {model}")
    print(f"  API Key:  {'configured' if api_key else 'MISSING'}")
    print(f"  Base URL: {settings.ai.base_url or '(default)'}")

    if not api_key:
        print("\nFAIL: AI__API_KEY not set. Export it before running evals.")
        return False

    try:
        registry = get_registry()
        provider = registry.get_llm(provider_name)
    except Exception as e:
        print(f"\nFAIL: Could not initialize provider '{provider_name}': {e}")
        return False

    print(f"\n  Sending test request to {provider_name}/{model}...")
    start = time.monotonic()
    try:
        response = await provider.complete(
            [Message(role="user", content="Respond with exactly: OK")],
            temperature=0.0,
            max_tokens=10,
        )
        elapsed = time.monotonic() - start
        print(f"  Response: {response.content[:100]}")
        print(f"  Latency:  {elapsed:.1f}s")
        if response.usage:
            print(f"  Tokens:   {response.usage.total_tokens}")
        print("\nPASS: Provider is working. Ready for eval execution.")
        return True
    except Exception as e:
        elapsed = time.monotonic() - start
        print(f"  Error after {elapsed:.1f}s: {type(e).__name__}: {e}")
        print("\nFAIL: Provider request failed. Check API key, model, and network.")
        return False


def main() -> None:
    """CLI entrypoint."""
    success = asyncio.run(verify())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
```

### Step 4: Add eval-verify Makefile target

Add before `eval-run` in the Makefile:

```makefile
eval-verify: ## Verify LLM provider is configured and responding
	uv run python -m app.ai.agents.evals.verify_provider
```

Update the `.PHONY` line to include `eval-verify`.

Optionally, make `eval-run` depend on `eval-verify`:

```makefile
eval-run: eval-verify ## Run agent evals (generate traces)
	uv run python -m app.ai.agents.evals.runner --agent all --output traces/
```

This prevents accidentally burning through 36 test cases only to discover the API key is wrong.

### Step 5: Update eval-baseline to use --skip-existing

In Makefile, update `eval-baseline` and `eval-full` targets to pass `--skip-existing` for resilience:

```makefile
eval-run: eval-verify ## Run agent evals (generate traces)
	uv run python -m app.ai.agents.evals.runner --agent all --output traces/ --skip-existing

eval-judge: ## Run judges on traces (generate verdicts)
	uv run python -m app.ai.agents.evals.judge_runner --agent all --traces traces --output traces --skip-existing
```

This way, if `make eval-run` crashes mid-batch, re-running it picks up where it left off.

For a clean re-run (no resume), user deletes the trace file first or passes `--no-skip-existing` (but default is skip for safety).

**Note:** Keep the `eval-dry-run` target WITHOUT `--skip-existing` so dry runs always regenerate everything.

## Verification — DONE

- [x] `make lint` passes
- [x] `make types` passes (pyright 0 errors on all 3 files)
- [x] `make test` passes (58 eval tests unbroken)
- [x] `make eval-dry-run` still works (full pipeline: 36 traces → 36 verdicts → 540 labels → analysis → 5 blueprint traces → regression check)
- [ ] `make eval-verify` with no API key → exits 1 with clear error (requires manual test)
- [ ] `make eval-verify` with valid API key → exits 0 with latency report (requires manual test)
- [x] `runner.py --skip-existing` skips cases already in output file (verified: 12/12 skipped)
- [x] `runner.py` crash mid-run → traces written so far are preserved in file (incremental flush)
- [x] `judge_runner.py --skip-existing` skips already-judged traces (verified: 12/12 skipped)
- [x] `make eval-run` (with `eval-verify` dependency) fails fast if provider not configured

## Execution Runbook (After This Plan)

Once these hardening changes are merged, live execution follows this sequence:

```bash
# 0. Configure provider
export AI__PROVIDER=anthropic
export AI__API_KEY=sk-ant-...
export AI__MODEL=claude-sonnet-4-20250514

# 1. Pre-flight check (~2s, 1 API call)
make eval-verify

# 2. Generate traces (~10-15 min, 36 API calls, ~$2.16)
make eval-run
# If crashes mid-run: just re-run, --skip-existing resumes

# 3. Judge traces (~5-8 min, 36 API calls, ~$0.97)
make eval-judge

# 4. Error analysis (<1 min, no API calls)
make eval-analysis

# 5. Scaffold human labels (<1 min, no API calls)
make eval-labels

# --- MANUAL STEP: Label ~540 rows (2-4 hours) ---
# See docs/eval-labeling-guide.md

# 6. Calibrate judges (<1 min, no API calls)
make eval-calibrate
# Target: TPR >= 0.85, TNR >= 0.80

# 7. QA gate calibration (2-3 min, no API calls)
make eval-qa-calibrate
# Target: >= 75% agreement per check

# 8. Blueprint pipeline eval (~5-10 min, ~15 API calls, ~$0.90)
make eval-blueprint

# 9. Establish baseline
cp traces/analysis.json traces/baseline.json
git add traces/baseline.json
git commit -m "eval: establish baseline (Phase 5.8)"

# 10. Verify regression gate
make eval-check
# Should exit 0
```

**Total cost:** ~$4.03 (Sonnet pricing) + ~2-4 hours human labeling effort.

## What This Plan Does NOT Cover

- **Human labeling** — Manual effort, documented in `docs/eval-labeling-guide.md`
- **Judge iteration** — If calibration targets aren't met, iterate on judge prompts (covered in existing plan)
- **CI/CD integration** — Deferred per TODO.md; `make eval-check` works locally
- **Provider selection** — User's choice (Anthropic recommended for quality)
