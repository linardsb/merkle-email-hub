# Migration Safety Debt

## Squawk pre-commit hook stays advisory (`|| true` retained)

`.pre-commit-config.yaml:93` runs Squawk against staged migration files but
swallows the exit code:

```yaml
entry: bash -c 'command -v squawk >/dev/null 2>&1 && git diff --cached --name-only --diff-filter=ACM | grep "alembic/versions/.*\.py$" | xargs -I{} squawk --reporter=compact {} || true'
```

### Why it stays advisory in Phase 1b

- **Squawk is not part of the dev-environment baseline.** It is not in
  `pyproject.toml`, not auto-installed by `make install-hooks`, and not
  documented in any developer setup path. Removing `|| true` would silently
  hard-fail commits on every contributor who never installed Squawk.
- **Pre-flight verification of an ignore mechanism (Phase 1b §1.5 Step 6)
  was not feasible** because Squawk was unavailable on the planning machine.
  Without proof that `--exclude-rule` / `.squawk.toml` works reliably, we
  cannot promote it to a hard gate without risk of a 44-migration history
  triggering rules on already-shipped DDL.
- **CI already enforces Squawk** at `.github/workflows/ci.yml:117-139` via
  the `migration-lint` job, scoped to `pull_request` events and to the diff
  vs. base branch. Hard enforcement happens there, where the runner is
  guaranteed to have Squawk installed.

The local hook is a quality-of-life nudge (catches issues before the dev
pushes), not a safety gate. The CI job is the safety gate.

### What unblocks promoting it to a hard gate

1. Add Squawk install to `make install-hooks` (or a shared `make bootstrap`
   target) so every dev has it.
2. Capture the current diff of `squawk --reporter=compact alembic/versions/*.py`
   against the existing migrations. If any rules fire on shipped migrations,
   create a `.squawk.toml` at repo root with `--exclude-rule` entries
   (one per rule) until the historical diff is clean.
3. Replace the `|| true` in `.pre-commit-config.yaml:93` with explicit error
   propagation: `... | xargs -I{} squawk --reporter=compact {}` (no trailing
   `|| true`). Commit the `.squawk.toml` in the same PR.

This unblock is Phase 2 (audit §2.4 `alembic check` work) territory — the
migration-lint job will get hardened alongside the new `alembic check` gate.

## `alembic check` is advisory (Phase 2 §2.4)

The `migrations` job in `.github/workflows/ci.yml` runs `alembic check`
with `continue-on-error: true`. It reports drift but doesn't fail the build.

### Why it stays advisory

After Phase 2 imported every model module into `alembic/env.py`, the worst
class of drift (9 "removed table" findings — model files weren't loading
into `Base.metadata`) is gone. What remains is long-standing cosmetic
drift between SQLAlchemy model declarations and the migrations that built
the schema:

- **`TIMESTAMP()` vs `DateTime(timezone=True)`** on `created_at`/`updated_at`
  across many tables. Equivalent in Postgres; different to alembic's
  comparator.
- **`nullable=False` server-side default vs model-side `Mapped[datetime]`**
  difference for `TimestampMixin` columns.
- **PK index normalization** — alembic adds `ix_<table>_id` for every
  primary key column; many migrations didn't create them.
- **Column comment drift** — comments in the model that aren't in the DB,
  or vice versa.
- **`ix_memory_entries_embedding_hnsw`** — HNSW vector index exists on the
  DB but not declared on the SQLAlchemy `Index(...)` for `memory_entries`.
- **`qa_overrides_qa_result_id_key`** unique constraint exists on the DB
  but isn't declared on the model.

None of these change runtime behavior. Fixing them all is a sweep across
~20 model files plus a "no-op normalization" migration; that's a separate
piece of work, not Phase 2's scope.

### What unblocks promoting it to a hard gate

1. Sweep models to align column types: replace any plain `TIMESTAMP()` /
   `DateTime()` with `DateTime(timezone=True)`. Mostly happens via
   `TimestampMixin` standardization.
2. Either (a) add the PK indexes via a no-op migration, or (b) suppress
   `add_index` for primary key columns in `alembic/env.py`'s
   `target_metadata.naming_convention` / `include_object` filter.
3. Reconcile column comments and the missing HNSW + unique-constraint
   declarations.
4. Run `alembic check` against a fresh DB. If clean, drop
   `continue-on-error: true` from `.github/workflows/ci.yml :: migrations`.

## Other migration-related deferrals

None at present. `alembic upgrade head` against a fresh DB is exercised in
the e2e-smoke job (in `ci.yml`) AND in the dedicated `migrations` job
introduced in Phase 2 §2.4.
