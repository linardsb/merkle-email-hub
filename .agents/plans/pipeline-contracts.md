# Plan: 48.5 Quality Contracts and Stage Gates

## Context
Define quality contracts that run between pipeline stages. A contract is a set of assertions that an agent's output must pass before artifacts propagate to the next DAG level. Without contracts, broken output (invalid HTML, stripped colors) wastes tokens on downstream agents processing garbage.

## Research Summary

**Pipeline directory:** `app/ai/pipeline/` does not exist yet — new module for Phase 48.

**Existing patterns to follow:**
- `app/qa_engine/checks/*.py` — 14 QA checks, all `async run(html, config) -> QACheckResult`. Same check-and-return pattern for contract assertions.
- `app/ai/blueprints/protocols.py` — `NodeResult(status, html, details, structured_failures)`, `NodeContext(html, brief, qa_failures, iteration, metadata)`
- `app/ai/blueprints/nodes/qa_gate_node.py` — Current QA gate runs 11 checks; contract system is the per-node equivalent
- `app/ai/shared.py:366` — `sanitize_html_xss(html, profile)` for `no_xss` check
- `app/qa_engine/dark_mode_parser.py` — `get_cached_dm_result()` for dark mode detection
- `app/core/config.py` — Nested Pydantic `BaseModel` configs under `AppSettings`, env `__` delimiter
- `app/core/exceptions.py` — `AppError` → `DomainValidationError` hierarchy

**Artifact flow:** `BlueprintRun.html` → `NodeContext.html` → node executes → `NodeResult.html` → `BlueprintRun.html`. Contracts validate `NodeResult.html` after each node.

**HTML parsing:** `lxml.html.document_fromstring(html)` used across QA checks.

## Test Landscape

**Related test files:**
- `app/qa_engine/tests/conftest.py` — `make_qa_check_result()` factory, `sample_html_valid`/`sample_html_minimal` fixtures
- `app/ai/blueprints/tests/conftest.py` — Same fixtures + `mock_provider`
- `app/qa_engine/tests/test_checks.py` — 300+ lines; class-based, async, field-by-field assertions

**Convention:** `asyncio_mode = "auto"` (no marker needed), class grouping (`class TestX:`), class-level check instances, `(result.details or "")` safe access.

**Golden templates:** 15 in `app/ai/templates/library/` (announcement, newsletter, promotional, transactional, etc.)
**Component seeds:** `app/components/data/seeds.py` — Email Shell + 14 inline components, all table/td layout.

## Type Check Baseline

| Directory | Pyright | Mypy |
|-----------|---------|------|
| `app/ai/` | 202 errors (bulk from untyped Whisper lib), 384 warnings | 5 errors |
| `app/qa_engine/` | 14 errors | 1 error |
| `app/ai/pipeline/` | Does not exist yet | — |

Target: 0 new pyright/mypy errors in `app/ai/pipeline/`.

## Files to Create

| File | Purpose |
|------|---------|
| `app/ai/pipeline/__init__.py` | Module init |
| `app/ai/pipeline/contracts.py` | `Contract`, `Assertion`, `ContractValidator`, `ContractResult`, `AssertionFailure` |
| `app/ai/pipeline/contracts/html_valid.yaml` | Predefined: parseable, 100B–100KB, has `<table>` root |
| `app/ai/pipeline/contracts/no_critical_issues.yaml` | Predefined: zero failing QA checks with severity=error |
| `app/ai/pipeline/contracts/fidelity_above_threshold.yaml` | Predefined: fidelity >= 0.85 |
| `app/ai/pipeline/tests/__init__.py` | Test module init |
| `app/ai/pipeline/tests/conftest.py` | Fixtures: valid/invalid/oversized/xss HTML, factory functions |
| `app/ai/pipeline/tests/test_contracts.py` | 12 tests |

## Files to Modify

| File | Change |
|------|--------|
| `app/core/config.py` | Add `PipelineConfig` with `contract_retry`, `contract_strict` fields |

## Implementation Steps

### Step 1: Create `app/ai/pipeline/__init__.py` and `app/ai/pipeline/tests/__init__.py`
Empty init files.

### Step 2: Add `PipelineConfig` to `app/core/config.py`
```python
class PipelineConfig(BaseModel):
    contract_retry: bool = True
    contract_strict: bool = False
```
Add `pipeline: PipelineConfig = PipelineConfig()` to `AppSettings`.

### Step 3: Create `app/ai/pipeline/contracts.py`

**Dataclasses (all frozen):**

```python
@dataclass(frozen=True, slots=True)
class Assertion:
    check: str  # "html_valid", "min_size", "max_size", "has_table_layout", "dark_mode_present", "no_critical_qa", "fidelity_above", "no_xss", "contains", "not_contains"
    operator: Literal[">=", "<=", "==", "contains", "not_contains"] = ">="
    threshold: Any = None  # type varies by check

@dataclass(frozen=True, slots=True)
class Contract:
    name: str
    assertions: tuple[Assertion, ...]  # frozen → tuple not list

@dataclass(frozen=True, slots=True)
class AssertionFailure:
    assertion: Assertion
    actual_value: Any
    message: str

@dataclass(frozen=True, slots=True)
class ContractResult:
    passed: bool
    failures: tuple[AssertionFailure, ...]
    duration_ms: int
```

**Built-in check functions** (private, registered in `_CHECK_REGISTRY` dict):

| Check | Logic |
|-------|-------|
| `html_valid` | `lxml_html.document_fromstring(html)` succeeds without exception |
| `min_size` | `len(html.encode()) >= threshold` |
| `max_size` | `len(html.encode()) <= threshold` |
| `has_table_layout` | DOM has `<table>` descendant AND no `<div>`/`<p>` with layout CSS (width/flex/float/columns) |
| `dark_mode_present` | `"prefers-color-scheme" in html` or `'color-scheme' in html` |
| `no_critical_qa` | Accepts `list[QACheckResult]` from metadata, checks `all(r.severity != "error" or r.passed for r in results)`. Note: QA checks use `"error"/"warning"/"info"` severities — NOT `"critical"`. A failing check with `severity="error"` is the critical gate condition. |
| `fidelity_above` | Reads `metadata.get("fidelity")`, compares `>= threshold` |
| `no_xss` | `sanitize_html_xss(html) == html` (no changes = no XSS vectors) |

**`ContractValidator` class:**

```python
class ContractValidator:
    async def validate(self, contract: Contract, html: str, metadata: dict[str, Any] | None = None) -> ContractResult:
        start = time.monotonic()
        failures: list[AssertionFailure] = []
        for assertion in contract.assertions:
            check_fn = _CHECK_REGISTRY.get(assertion.check)
            if check_fn is None:
                failures.append(AssertionFailure(assertion, None, f"Unknown check: {assertion.check}"))
                continue
            actual = check_fn(html, metadata or {})
            if not _evaluate(assertion.operator, actual, assertion.threshold):
                failures.append(AssertionFailure(assertion, actual, _describe_failure(assertion, actual)))
        elapsed = int((time.monotonic() - start) * 1000)
        return ContractResult(passed=len(failures) == 0, failures=tuple(failures), duration_ms=elapsed)
```

**`_evaluate` helper:** Dispatches on operator literal — `>=`/`<=`/`==` for numeric, `contains`/`not_contains` for string-in-string.

**`load_contract(path: Path) -> Contract`:** Reads YAML file, returns `Contract` with parsed assertions. Cached with `@lru_cache`.

### Step 4: Create predefined contract YAML files

**`app/ai/pipeline/contracts/html_valid.yaml`:**
```yaml
name: html_valid
assertions:
  - check: html_valid
    operator: "=="
    threshold: true
  - check: min_size
    operator: ">="
    threshold: 100
  - check: max_size
    operator: "<="
    threshold: 102400
  - check: has_table_layout
    operator: "=="
    threshold: true
```

**`app/ai/pipeline/contracts/no_critical_issues.yaml`:**
```yaml
name: no_critical_issues
assertions:
  - check: no_critical_qa
    operator: "=="
    threshold: true
```

**`app/ai/pipeline/contracts/fidelity_above_threshold.yaml`:**
```yaml
name: fidelity_above_threshold
assertions:
  - check: fidelity_above
    operator: ">="
    threshold: 0.85
```

### Step 5: Create test conftest and fixtures

**`app/ai/pipeline/tests/conftest.py`:**
- `sample_html_valid` — full email HTML with DOCTYPE, table layout, dark mode, MSO conditionals (reuse pattern from `app/qa_engine/tests/conftest.py`)
- `sample_html_minimal` — `<html><body><p>Hello</p></body></html>` (fails most contracts)
- `sample_html_oversized` — valid HTML padded to >102KB with `<!-- padding -->` comments
- `sample_html_xss` — valid HTML with `<script>alert(1)</script>` injected
- `sample_html_no_dark_mode` — valid table layout but no prefers-color-scheme
- `make_contract(**overrides) -> Contract` — factory
- `make_assertion(**overrides) -> Assertion` — factory

### Step 6: Write 12 tests in `test_contracts.py`

```
class TestHtmlValidCheck:
  1. test_valid_html_passes — sample_html_valid → html_valid assertion passes
  2. test_broken_fragment_fails — "<p>broken" → html_valid assertion fails

class TestSizeChecks:
  3. test_min_size_passes — valid HTML > 100 bytes passes min_size
  4. test_max_size_fails — oversized HTML > 102400 bytes fails max_size

class TestTableLayoutCheck:
  5. test_table_layout_passes — valid HTML with <table> root passes
  6. test_div_layout_fails — HTML with <div style="width:600px"> fails

class TestDarkModeCheck:
  7. test_dark_mode_present — HTML with prefers-color-scheme passes
  8. test_dark_mode_missing — HTML without dark mode fails

class TestNoCriticalQA:
  9. test_no_critical_passes — metadata with passing QA results → passes
  10. test_critical_finding_fails — metadata with failing QA check (severity="error", passed=False) → fails

class TestAssertionOperators:
  11. test_operators — verify >=, <=, ==, contains, not_contains all evaluate correctly

class TestContractValidatorIntegration:
  12. test_full_contract_retry_flow — load html_valid.yaml contract, validate valid HTML (passes), validate broken HTML (fails with specific AssertionFailure details), verify duration_ms > 0
```

### Step 7: Create `contracts/__init__.py`
Empty init for the YAML contracts subpackage directory.

## Preflight Warnings
- **Severity mismatch (fixed):** `QACheckResult.severity` uses `"error"/"warning"/"info"` — NOT `"critical"`. The `no_critical_qa` check must gate on `severity == "error" and passed == False`, not `severity == "critical"`. Plan updated.
- `lxml.html.document_fromstring()` raises `etree.ParserError` on truly empty/garbage input, not just `Exception` — catch specifically.
- `sanitize_html_xss()` import from `app.ai.shared` — may need `nh3` available in test env (it's a compiled Rust dep).
- YAML contract loading uses `@lru_cache` on file path — cache won't invalidate if YAML changes at runtime (fine for production, but tests should avoid caching or clear it).
- The `no_xss` check comparing `sanitize_html_xss(html) == html` may have whitespace normalization differences — test with known XSS payloads, not whitespace-sensitive comparisons.

## Security Checklist
- No new endpoints in this subtask (pure library code)
- Contract YAML files are read-only from disk, no user-supplied paths
- `no_xss` check delegates to battle-tested `nh3` via `sanitize_html_xss()`
- No SQL, no subprocess, no eval
- All inputs to check functions are from internal pipeline artifacts, not user input

## Verification
- [ ] `make check` passes
- [ ] `uv run pytest app/ai/pipeline/tests/test_contracts.py -v` — 12 tests pass
- [ ] `uv run pyright app/ai/pipeline/` — 0 errors
- [ ] `uv run mypy app/ai/pipeline/` — 0 errors
- [ ] Contract YAML files load correctly via `load_contract()`
- [ ] Pyright errors ≤ baseline (202 in `app/ai/`, 0 new in `app/ai/pipeline/`)
