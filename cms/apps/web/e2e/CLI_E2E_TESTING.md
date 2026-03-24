# CLI-Based Exploratory E2E Testing

## Overview

This project has two complementary e2e testing strategies:

| Strategy | Tool | Purpose | When to use |
|----------|------|---------|-------------|
| **Automated** | Playwright | Regression prevention | Every PR (CI), nightly (full matrix) |
| **Exploratory** | agent-browser (CLI) | Visual inspection, edge cases, new features | Pre-release, after major UI changes |

## Automated E2E (Playwright)

```bash
make e2e                # Chromium only (default, fast — PR checks)
make e2e-firefox        # Firefox only
make e2e-webkit         # WebKit (Safari) only
make e2e-all-browsers   # Full matrix (nightly / release gate)
make e2e-ui             # Interactive Playwright UI mode
make e2e-report         # Open last HTML report
```

### Browser matrix

| Spec | Chromium | Firefox | WebKit | Notes |
|------|----------|---------|--------|-------|
| auth | x | x | x | Core flow |
| dashboard | x | x | x | Core flow |
| workspace | x | x | x | Core flow |
| builder | x | x | x | DnD, contentEditable — most sensitive |
| collaboration | x | x | - | WebSocket; WebKit WS flaky |
| export | x | - | - | API-heavy, browser-independent |
| approval | x | - | - | API-heavy |
| design-sync | x | - | - | API mocking |
| ecosystem | x | - | - | Static page |

## Exploratory E2E (CLI)

The CLI e2e suite uses `agent-browser` for interactive, AI-guided exploratory testing. It covers 13 user journeys with screenshot capture and visual analysis.

### Journeys covered

1. Login flow
2. Dashboard (stat cards, quick actions)
3. Workspace — template selector, code/visual tabs
4. Workspace — preview controls (viewport, dark mode, zoom)
5. Workspace — AI chat (10 agent tabs)
6. Workspace — QA panel, export dialog
7. Components (category filter, search, detail dialog)
8. Approvals (status filters, decision flow)
9. Connectors (platform filters, export history)
10. Intelligence (performance charts, score cards)
11. Knowledge (search, domain filters, documents)
12. Renderings (compatibility matrix, rendering tests)
13. Global features (dark mode, locale, logout)

### How to run

In Claude Code:
```
/e2e-test
```

This launches the full exploratory suite defined in `.claude/commands/e2e-test.md`.

### When to use exploratory testing

- **Pre-release validation** — visual inspection before cutting a release branch
- **After major UI changes** — new components, layout refactors, theme changes
- **Bug investigation** — interactive DOM inspection with screenshots
- **New feature smoke test** — quick visual check before writing Playwright tests

### How they complement each other

- **Playwright** catches regressions automatically in CI — deterministic, fast, runs on every PR
- **CLI e2e** catches visual/UX issues that automated tests miss — interactive, thorough, human-guided
- Write Playwright tests for stable flows. Use CLI e2e for exploration and edge cases.
