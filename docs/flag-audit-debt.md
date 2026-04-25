# Flag Audit Debt

`make flag-audit` (called by `make check`) requires every `*_ENABLED`
environment flag in the codebase to be registered in `feature-flags.yaml`.
As of 2026-04-25, **23 flags** are unregistered and block the gate.

These were introduced by a series of feature commits that did not update the
manifest. None were introduced by the secure-ai-agents PR — that PR's new
fields (`SECURITY__DISABLED_AGENTS`, `SECURITY__AGENT_MAX_RUN_SECONDS`,
`SECURITY__AGENT_MAX_TOTAL_TOKENS`) are not `*_ENABLED` flags so the audit
does not apply to them.

## How to fix

For each entry below, add a record to `feature-flags.yaml` under `flags:`
following the schema documented at the top of that file. Required fields:

```yaml
- name: <flag>
  description: <what it controls>
  owner: <team or person>
  created: "<YYYY-MM-DD>"  # date the flag was added to source
  removal_date: "<YYYY-MM-DD>" | null
  status: alpha | beta | ga | deprecated
  permanent_reason: <required when removal_date is null>
```

Run `make flag-audit` after each batch to confirm progress.

## Unregistered flags (23)

Source location is the file that defines the field on a Pydantic config class.
Where uncertain, grep for the flag name in `app/core/config.py`.

| Flag | Likely source | Notes |
|---|---|---|
| `AI__EVALUATOR__ENABLED` | `app/core/config.py` (`EvaluatorConfig`) | Evaluator agent gate |
| `CREDENTIALS__ENABLED` | `app/core/config.py` (`CredentialsConfig`) | Credential pool rotation |
| `DEBOUNCE__ENABLED` | `app/core/config.py` (`DebounceConfig`) | Distributed debounce |
| `DESIGN_SYNC__BGCOLOR_PROPAGATION_ENABLED` | `app/core/config.py` (`DesignSyncConfig`) | Phase 49.x bg-color propagation |
| `DESIGN_SYNC__CONVERSION_MEMORY_ENABLED` | `app/core/config.py` (`DesignSyncConfig`) | Conversion memory cache |
| `DESIGN_SYNC__CONVERSION_TRACES_ENABLED` | `app/core/config.py` (`DesignSyncConfig`) | Conversion trace logging |
| `DESIGN_SYNC__CUSTOM_COMPONENT_ENABLED` | `app/core/config.py` (`DesignSyncConfig`) | Custom component matcher |
| `DESIGN_SYNC__SIBLING_DETECTION_ENABLED` | `app/core/config.py` (`DesignSyncConfig`) | Sibling-section detection |
| `DESIGN_SYNC__TOKEN_SCOPING_ENABLED` | `app/core/config.py` (`DesignSyncConfig`) | Token scoping |
| `DESIGN_SYNC__TREE_BRIDGE_ENABLED` | `app/core/config.py` (`DesignSyncConfig`) | Tree-bridge converter path (Phase 49.8) |
| `DESIGN_SYNC__VLM_CLASSIFICATION_ENABLED` | `app/core/config.py` (`DesignSyncConfig`) | VLM section classifier |
| `DESIGN_SYNC__VLM_FALLBACK_ENABLED` | `app/core/config.py` (`DesignSyncConfig`) | VLM fallback when heuristic fails |
| `DESIGN_SYNC__VLM_VERIFY_ENABLED` | `app/core/config.py` (`DesignSyncConfig`) | VLM verification pass |
| `KNOWLEDGE__PROACTIVE_QA_ENABLED` | `app/core/config.py` (`KnowledgeConfig`) | Proactive QA pipeline (see `.agents/plans/48.12-proactive-qa-pipeline.md`) |
| `MCP__CACHE_ENABLED` | `app/core/config.py` (likely `MCPConfig`) | MCP response caching (see `.agents/plans/mcp-response-caching.md`) |
| `NOTIFICATIONS__EMAIL_ENABLED` | `app/core/config.py` (`NotificationsConfig`) | Email notifications |
| `NOTIFICATIONS__ENABLED` | `app/core/config.py` (`NotificationsConfig`) | Master notifications switch |
| `NOTIFICATIONS__SLACK_ENABLED` | `app/core/config.py` (`NotificationsConfig`) | Slack notifications |
| `NOTIFICATIONS__TEAMS_ENABLED` | `app/core/config.py` (`NotificationsConfig`) | MS Teams notifications |
| `PIPELINE__ENABLED` | `app/core/config.py` (`PipelineConfig`) | DAG pipeline executor |
| `QA_META_EVAL__ENABLED` | `app/core/config.py` (likely `QaMetaEvalConfig`) | QA meta-evaluation (see `.agents/plans/qa-meta-eval.md`) |
| `SCHEDULING__ENABLED` | `app/core/config.py` (likely `SchedulingConfig`) | Scheduled job runner |
| `SECURITY__PROMPT_GUARD_ENABLED` | `app/core/config.py` (`SecurityConfig`) | Prompt-injection guard (pre-existing, not touched by secure-ai-agents) |

## How to verify the fix

```bash
make flag-audit
# Expect: "Flag audit: 0 error(s), 0 warning(s)"

make check
# Should now reach completion without blocking on flag-audit.
```

## Why this isn't blocking the secure-ai-agents PR

The `secure-ai-agents` work passes every check independently:

- ruff (26 rule sets): clean on all 19 staged files
- pyright `app/ai/` + `app/core/`: 0 errors
- mypy `app/ai/` + `app/core/`: 0 errors
- pytest `app/ai/`: 2037 passed
- security ruff (`--select=S`): clean

`make check` is a whole-repo gate. The 23 unregistered flags are accumulated
debt from earlier feature work and would block any commit on this branch
state. They are documented here so they can be fixed in a focused PR rather
than smuggled into unrelated work with placeholder metadata.
