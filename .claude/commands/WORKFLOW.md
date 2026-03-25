# Slash Commands & Workflows

## Backend — New Feature
```
/be-prime → /be-planning → /be-execute → /be-ship → /commit
```

## Backend — New Feature (Fast Path)
```
/parallel-plan → /preflight-check → /be-execute → /be-ship → /commit
```
`/parallel-plan` replaces `/be-prime` + `/be-planning` with parallel agents (research, test scout, pyright baseline run concurrently). `/preflight-check` scans the plan's target files for hardcoded assertions, tuple unpacking, and fragile patterns before execution.

## Backend — Bug Fix / Code Review Fix
```
/be-code-review-fix → /be-validate → /commit
```
Skip prime/planning — go straight to diagnosis and fix. Use `/be-prime` first only if you need full context for a complex bug.

## Frontend — New Feature
```
/fe-prime → /fe-planning → /fe-execute → /fe-ship → /commit
```

## Frontend — New Feature (Fast Path)
```
/fe-parallel-plan → /fe-preflight-check → /fe-execute → /fe-ship → /commit
```
`/fe-parallel-plan` replaces `/fe-prime` + `/fe-planning` with parallel agents (research, test scout, tsc baseline run concurrently). `/fe-preflight-check` scans for hardcoded assertions, snapshot tests, stale mocks, and `as any` casts before execution.

## Frontend — Bug Fix / Code Review Fix
```
/fe-code-review-fix → /fe-validate → /commit
```
Skip prime/planning — go straight to diagnosis and fix. Use `/fe-prime` first only if you need full context for a complex bug.

## Code Review (any stack)
```
/review → /be-code-review-fix or /fe-code-review-fix → validate → /commit
```
Review finds issues, fix resolves them, validate confirms, commit ships.

## E2E Testing (Exploratory + Security)
```
/fe-execute → /fe-validate → /e2e-test → /commit
```
Optional: Run after feature implementation for pre-commit browser validation.

## Available Commands

### Backend
| Command | Purpose | When to Use |
|---------|---------|-------------|
| `/be-prime` | Load full backend context | Start of feature work or complex debugging |
| `/be-planning` | Create implementation plan | New features, multi-file changes |
| `/be-execute` | Execute plan step by step | After planning approval |
| `/be-code-review-fix` | Diagnose and fix issues | Bugs, review findings, test failures, type errors |
| `/be-validate` | Run all quality checks | After any code changes |
| `/be-ship` | Full quality pipeline (validate→review→fix→validate) | Before committing a feature |

### Frontend
| Command | Purpose | When to Use |
|---------|---------|-------------|
| `/fe-prime` | Load full frontend context | Start of feature work |
| `/fe-planning` | Create frontend plan | New features, multi-file changes |
| `/fe-execute` | Execute frontend plan | After planning approval |
| `/fe-code-review-fix` | Diagnose and fix issues | Bugs, review findings, test failures, type errors |
| `/fe-validate` | Run frontend quality checks | After any code changes |
| `/fe-ship` | Full quality pipeline (validate→review→fix→validate) | Before committing a feature |

### Accelerators
| Command | Purpose | When to Use |
|---------|---------|-------------|
| `/parallel-plan` | Parallel research + test scout + planning | Replaces `/be-prime` → `/be-planning` for new features |
| `/preflight-check` | Scan plan files for fragile patterns (backend) | Before `/be-execute` to prevent fix cycles |
| `/fe-parallel-plan` | Parallel research + test scout + planning (frontend) | Replaces `/fe-prime` → `/fe-planning` for new features |
| `/fe-preflight-check` | Scan plan files for fragile patterns (frontend) | Before `/fe-execute` to prevent fix cycles |

### Cross-cutting
| Command | Purpose | When to Use |
|---------|---------|-------------|
| `/commit` | Create conventional commit with safety checks + AI context tracking | After validate passes |
| `/review` | Code review against 8 quality standards | Before committing, after feature work |
| `/update-docs` | Sync TODO.md, CLAUDE.md, and PRD.md | After completing tasks |
| `/handoff` | Write HANDOFF.md for session continuation | When session is long or switching contexts |

## Session Continuity
```
... (any workflow) → /handoff
```
When a session runs long or you need to continue later, `/handoff` captures completed work, decisions, dead ends, and next steps into `HANDOFF.md`. Start the next session with: **"Read HANDOFF.md and continue"**

## Reference Docs (`.claude/docs/`)
Heavy reference documents with scout headers. Sub-agents check the header (`purpose`, `when-to-use`, `size`) before loading the full doc. Available:
- `architecture-deep-dive.md` — VSA layout, agent pipeline, blueprint engine, eval system
- `eval-system-guide.md` — judges, calibration, regression, production sampling, golden tests
- `qa-engine-guide.md` — 11 checks, chaos testing, property testing, outlook analyzer, CSS compiler
- `design-system-guide.md` — brand identity, token mapping, template assembly, brand repair
