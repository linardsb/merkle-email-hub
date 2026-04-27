# Phase 48 Status — Parked

**Date:** 2026-04-27
**Decision:** Path B (Park) — see `.agents/plans/tech-debt-05-phase-48-decision.md`.
**Findings resolved:** F008 (`EvaluatorNode` not instantiated), F009 (`PipelineExecutor` not invoked).

## Summary

Phase 48 shipped a DAG-based pipeline executor, an adversarial evaluator agent, a hook system, and a tree-based component compilation path behind disabled flags. The DAG executor, evaluator agent, hook system, and adversarial gate were never wired into any production blueprint. Roughly 1,500 LOC sat in `app/` as tested-but-unused infrastructure.

The tech-debt audit (TECH_DEBT_AUDIT.md) flagged this as F008/F009. The decision was to park, not ship-in-shadow, because shadow mode is a sprint-sized telemetry project for code that may never become primary.

## What moved

The dormant tree is at `prototypes/ai-pipeline/`. See its README for re-import prerequisites.

| Path before | Path after |
|---|---|
| `app/ai/pipeline/` | `prototypes/ai-pipeline/pipeline/` |
| `app/ai/agents/evaluator/` | `prototypes/ai-pipeline/agents/evaluator/` |
| `app/ai/hooks/` | `prototypes/ai-pipeline/hooks/` |
| `app/ai/blueprints/nodes/evaluator_node.py` | `prototypes/ai-pipeline/nodes/evaluator_node.py` |

## What stayed in `app/`

Phase 48 work that *did* land in production:

- `app/components/tree_schema.py` (48.6) — `EmailTree` Pydantic model, used by Scaffolder tree-mode and `TreeCompiler`.
- `app/components/tree_compiler.py` (48.8) — deterministic EmailTree → HTML compiler.
- `app/ai/agents/scaffolder/tree_builder.py` + `pipeline.execute_tree()` (48.7) — tree output mode, gated by `AI__SCAFFOLDER_TREE_MODE`.
- `app/qa_engine/meta_eval.py` + `synthetic_generator.py` (48.9, 48.10) — confusion-matrix gate and adversarial QA fixtures.
- `app/mcp/optimization.py` (48.11) — MCP cache and schema compression.
- `app/knowledge/proactive_qa.py` (48.12) — proactive warning extraction (the pipeline-injection seam was dropped; the rest of the module stands on its own).

## Engine simplifications

With the evaluator agent gone, `app/ai/blueprints/engine.py` lost:

- `EdgeCondition` literal `"revise"`
- `BlueprintRun.evaluator_revision_count`
- The evaluator-revision cap branch
- The `is_revise` routing branch in `_resolve_next_node`
- `BlueprintConfig.max_revisions`

`AgentHandoff.to_artifacts()` and `AgentHandoff.from_artifact_store()` were also removed — they were the bridge between the legacy engine and the DAG artifact store, and had no callers outside the parked test suite.

## Re-import gate

Before lifting any of `prototypes/ai-pipeline/` back to `app/`, an evaluator calibration baseline (TPR/TNR per criterion against known-good and known-bad agent outputs) must exist. See the prototypes README for the full recipe.
