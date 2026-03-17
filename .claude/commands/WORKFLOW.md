# Slash Commands & Workflows

## Backend — New Feature
```
/be-prime → /be-planning → /be-execute → /be-validate → /commit
```

## Backend — Bug Fix / Code Review Fix
```
/be-code-review-fix → /be-validate → /commit
```
Skip prime/planning — go straight to diagnosis and fix. Use `/be-prime` first only if you need full context for a complex bug.

## Frontend — New Feature
```
/fe-prime → /fe-planning → /fe-execute → /fe-validate → /commit
```

## Code Review (any stack)
```
/review → /be-code-review-fix → /be-validate → /commit
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

### Frontend
| Command | Purpose | When to Use |
|---------|---------|-------------|
| `/fe-prime` | Load full frontend context | Start of feature work |
| `/fe-planning` | Create frontend plan | New features, multi-file changes |
| `/fe-execute` | Execute frontend plan | After planning approval |
| `/fe-validate` | Run frontend quality checks | After any code changes |

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
