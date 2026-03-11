# Update Documentation

Synchronise all project documentation to reflect the current implementation state. Update these files in order:

## 1. Read Current State

### 1a. Documentation (via jDocMunch — section-level reads, no full-file scans)

Use `jdocmunch` to read only the sections that matter. The repo is indexed as `local/merkle-email-hub`.

**TODO.md** — read phase sections individually:
- `get_document_outline` for `TODO.md` to see all phase section IDs
- `get_section` on each phase to check completion markers (e.g. `::phase-0-foundation-blockers#2`)

**CLAUDE.md** — only the roadmap section:
- `get_section` on `local/merkle-email-hub::CLAUDE.md::implementation-roadmap#2` for the overview
- `get_section` on individual phase children (e.g. `::phase-4-v2#3`) for `[x]`/`[ ]` markers

**PRD.md** — only Section 0 (Implementation Status):
- `get_section` on `local/merkle-email-hub::PRD.md::0-implementation-status#2` (header)
- `get_section` on children: `::completed#3`, `::in-progress#3`, `::infrastructure-built#3`
- Do NOT read sections 1-12 (requirements — never modified by this command)

**Plan files** — search for completed plans:
- `search_sections` with query "DONE" or "completed" scoped to plan files

### 1b. Codebase Evidence (via jCodeMunch)

Use `jcodemunch` to scan for implementation evidence. The repo is indexed as `merkle-email-hub`.

- `get_file_tree` with `path_prefix="cms/apps/web/src/hooks"` — frontend hooks (feature coverage)
- `get_file_tree` with `path_prefix="cms/apps/web/src/app"` — dashboard/route pages
- `search_symbols` for route functions (`kind="function"`, `file_pattern="app/*/routes.py"`) — backend API coverage
- `get_file_tree` with `path_prefix="alembic/versions"` — migration files (DB schema state)

### 1c. Fallback

If jDocMunch/jCodeMunch indexes are stale or unavailable, fall back to direct `Read` + `Glob`.

## 2. Update TODO.md

- Mark any newly completed tasks with `~~strikethrough~~` and `DONE` suffix
- Ensure completion markers match actual implementation (don't mark incomplete work as done)
- Keep security requirements and verification criteria intact

## 3. Update CLAUDE.md

- Sync the `Implementation Roadmap` checklist with TODO.md completion state
- Update `[x]` / `[ ]` markers to match
- If new modules, commands, or patterns were introduced, add them to the relevant architecture sections
- Keep compact — CLAUDE.md is loaded into every conversation context

## 4. Update PRD.md

- Update the `Implementation Status` section (Section 0):
  - Move newly completed tasks to the "Completed" table with key deliverables
  - Update "In Progress" to reflect current sprint focus
  - Update "Infrastructure Built" if new cross-cutting capabilities were added
- Bump version number if significant changes
- Update the date to today

## 5. Verify Consistency

Cross-check that all three docs agree on:
- Which tasks are complete vs in-progress
- Phase numbering and task descriptions
- Architecture descriptions match actual code structure

## 6. Report Changes

Summarise what was updated in each file. If nothing changed, say so — don't make changes for the sake of it.

## Rules

- Do NOT add features or tasks that don't exist in the codebase
- Do NOT remove security requirements or verification criteria from TODO.md
- Do NOT expand CLAUDE.md beyond what's needed (it's context-window-sensitive)
- Do NOT modify the PRD requirements sections (1-12) — only update Section 0 (Implementation Status)
- Keep all changes factual and verifiable against the codebase
