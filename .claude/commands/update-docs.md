# Update Documentation

Synchronise all project documentation to reflect the current implementation state. Update these files in order:

## 1. Read Current State

Read the following files to understand what's been built:
- `TODO.md` — task-level roadmap with completion markers
- `CLAUDE.md` — architecture reference and roadmap summary
- `PRD.md` — product requirements with implementation status
- `.agents/plans/*.md` — completed plan files (scan for DONE/completed markers)

Also scan the codebase for implementation evidence:
- `cms/apps/web/src/hooks/*.ts` — frontend hooks (indicates feature coverage)
- `cms/apps/web/src/app/(dashboard)/**/*.tsx` — dashboard pages
- `cms/apps/web/src/app/(dashboard)/**/page.tsx` — route pages
- `app/*/routes.py` — backend API routes (indicates backend feature coverage)
- `alembic/versions/*.py` — migration files (indicates DB schema state)

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
