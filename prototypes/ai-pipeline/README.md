# Phase 48 — Parked AI Pipeline DAG Infrastructure

Parked on 2026-04-27 from `app/ai/`. Tracked under findings F008/F009 in `TECH_DEBT_AUDIT.md`. Decision recorded in `.agents/plans/tech-debt-05-phase-48-decision.md` (Path B).

## What's here

| Subdir | Origin |
|---|---|
| `pipeline/` | `app/ai/pipeline/` — DAG types, executor, contracts, artifacts, adapters, templates, tests |
| `agents/evaluator/` | `app/ai/agents/evaluator/` — adversarial evaluator agent (service, prompts, criteria, tests) |
| `hooks/` | `app/ai/hooks/` — pipeline execution hook registry, profiles, builtins (cost tracker, logger, progress reporter, adversarial gate, pattern extractor) |
| `nodes/evaluator_node.py` | `app/ai/blueprints/nodes/evaluator_node.py` — blueprint adapter that wrapped `EvaluatorAgentService` |

## Why parked

The DAG executor, evaluator agent, and hook system shipped behind disabled flags and were never wired into a production blueprint. Keeping the code in `app/` violated the "no tested-but-unused infra" rule from the tech-debt audit. Parking here preserves git history and allows re-import once a real consumer exists.

## Re-import prerequisites

Before lifting any of this back into `app/`, the following must be in place:

1. **Evaluator calibration baseline** — TPR/TNR labels for the evaluator agent against known-good and known-bad agent outputs. Without this, the adversarial gate is just rejecting on vibes.
2. **A concrete blueprint that benefits from DAG concurrency** — the legacy sequential `BlueprintEngine` is correct for the current pipeline shape; concurrent execution is only worth the complexity if there are independent agent levels.
3. **A consumer for hook events** — cost tracker, structured logger, and progress reporter are useful only as part of pipeline execution; they don't have value standalone.

## Re-import recipe

```sh
git mv prototypes/ai-pipeline/pipeline app/ai/pipeline
git mv prototypes/ai-pipeline/agents/evaluator app/ai/agents/evaluator
git mv prototypes/ai-pipeline/hooks app/ai/hooks
git mv prototypes/ai-pipeline/nodes/evaluator_node.py app/ai/blueprints/nodes/evaluator_node.py
```

Then restore in `app/core/config.py`:
- `EvaluatorConfig`, `HookConfig`, `PipelineConfig`
- `AIConfig.evaluator`, `Settings.pipeline`
- `BlueprintConfig.max_revisions`

And in `app/ai/blueprints/engine.py`:
- Add `"revise"` back to `EdgeCondition`
- Restore `BlueprintRun.evaluator_revision_count`
- Restore the evaluator-revision cap and "revise" edge handling

The git history on the move commit is the canonical reference.

## Status

Tests inside this directory are not run by `make check`. They executed green at the time of the move.
