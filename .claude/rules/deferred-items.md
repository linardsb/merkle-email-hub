# Deferred-Items Convention

A central JSON ledger at `.agents/deferred-items.json` tracks acceptance criteria and known-by-inspection gaps that shipped phases left open. Treat it as load-bearing memory — entries usually point to real bugs that just haven't surfaced yet.

## When to consult

**Before** any of these actions, grep `.agents/deferred-items.json`:

- `/be-planning`, `/fe-planning`, `/parallel-plan`, `/be-execute`, `/fe-execute` on a new phase or subtask → check for entries whose `phase` field overlaps the new work, or whose `code_refs` overlap files in the plan's "Files to Create/Modify" list.
- Investigating an unexpected bug → check for entries whose `symptom_if_broken` matches the symptom you're seeing. The cause may already be cataloged.
- Writing a phase plan with acceptance criteria → check for `phase-*-ac-*` entries from upstream phases that the new plan should close.

If a match is found, surface it in the planning output / preflight report so the user can decide whether to address it as part of the new work or accept it as carried-forward technical debt.

## When to add an entry

Append an entry whenever a phase ships with:

- **A soft acceptance criterion** — one that depends on data, fixtures, or services that don't exist yet (e.g. "validates against real LEGO fixture" when LEGO has no `structure.json` in the repo).
- **A speculative gap found by inspection** — a code path that *probably* fails on real-world data but can't be confirmed without that data.
- **A code-shape concession** — a workaround taken because the cleaner fix needs a refactor scheduled for a later phase.

Don't add entries for:

- Bugs you can fix now → just fix them.
- Tasks captured in `TODO-completed.md`, `.agents/plans/`, or backlog issues → those have their own homes.
- Subjective preferences ("could be cleaner if…") → not load-bearing.

## Schema

Each entry must have:

```json
{
  "id": "phase-<N>.<sub>-<short-slug>",
  "phase": "<N>.<sub>",
  "title": "<one-line summary>",
  "status": "deferred" | "closed",
  "severity": "soft" | "speculative" | "known-bug",
  "introduced": "<YYYY-MM-DD>",
  "introduced_commit": "<short SHA>",
  "summary": "<2-3 sentence description>",
  "code_refs": ["<file>:<line> (<symbol>)", ...],
  "symptom_if_broken": "<what a regression would look like>",
  "closes_when": "<concrete condition that retires this entry>"
}
```

Optional fields: `available_data` (where related data lives), `fast_closure_path` (a one-shot script idea), `blocks` / `blocked_by` (dependency edges between entries), `fix_sketch` (proposed code change), `notes`.

## When to retire an entry

Change `status` from `deferred` to `closed` and add a `closed_commit` field when the `closes_when` condition is genuinely met — i.e. the symptom-if-broken can no longer occur. Don't delete closed entries; their history is useful for future debugging.

## Tooling

The deferred-items grep is wired into `/preflight-check` as **Step 2** (`.claude/commands/preflight-check.md`) — every preflight run cross-references the plan's "Files to Create/Modify" list and matching phase against `.agents/deferred-items.json` and prints a "Deferred Items Touching This Plan" table (empty table if no matches — never silent). The agent or user must decide per match whether to **close**, **avoid**, or **carry forward** each one.

If the table consistently surfaces noise (entries that match but are not relevant), tighten the `code_refs` on the noisy entry rather than weakening the grep.
