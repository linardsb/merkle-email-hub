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

## Tooling roadmap

This convention is currently enforced manually. When `.agents/deferred-items.json` reaches **~5 open entries**, wire a scan into `/preflight-check` so plan files are automatically cross-referenced against the ledger. See `.agents/deferred-items.json#tooling_followups[0]` for the trigger.
