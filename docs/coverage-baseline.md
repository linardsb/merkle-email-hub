# Coverage Baseline

## Threshold

`--cov-fail-under=88` — enforced in `.github/workflows/ci.yml` (backend job
Test step) and `Makefile :: ci-be`. Not placed in
`pyproject.toml [tool.pytest.ini_options].addopts` so individual-file `pytest`
invocations during dev iteration do not redline.

## Measurement (Phase 2 §2.5)

| Date | Tests run | Coverage | Threshold | Margin |
|---|---|---|---|---|
| 2026-04-25 | 8175 passed, 86 skipped (`-m "not integration"`) | **89%** | 88% | +1pp |

Measured locally with `uv run pytest -m "not integration" --cov=app --cov-report=term`.

## Ratchet policy

Quarterly review can bump the threshold by 1–2 percentage points if measured
coverage has held above the new floor for ≥ one full quarter without
intentional reductions. Drops below current `--cov-fail-under` block CI.

To raise the threshold:
1. Confirm `make ci-be` still passes locally with the proposed new value.
2. Bump in `.github/workflows/ci.yml` and `Makefile :: ci-be`.
3. Append a row to the table above.

## What is excluded

- `-m "not integration"` — integration tests skipped (require real DB).
- Visual regression, snapshot, collab, benchmark markers run separately.
- `cms/` (frontend) — tracked under separate Vitest config.
