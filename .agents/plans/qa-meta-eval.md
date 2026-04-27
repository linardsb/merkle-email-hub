# Plan: 48.9 QA Check Meta-Evaluation Framework

## Context
The QA engine has 14 checks but no systematic way to measure if they're calibrated correctly. A `file_size` check with a 100KB threshold might flag 20% of valid emails (high FP) while missing oversized ones with inlined images (FN). Meta-evaluation quantifies check quality against ground-truth labels so thresholds can be tuned empirically.

## Research Summary

**14 QA Checks** registered in `app/qa_engine/checks/__init__.py:33-48` as `ALL_CHECKS: list[QACheckProtocol]`:

| Check | File | Pattern |
|-------|------|---------|
| html_validation | `checks/html_validation.py` | lxml DOM, 20 checks × 5 groups |
| css_support | `checks/css_support.py` | Ontology + cssutils, 365 props |
| css_audit | `checks/css_audit.py` | Per-build matrix |
| file_size | `checks/file_size.py` | Gmail 102KB threshold |
| link_validation | `checks/link_validation.py` | HTTPS enforcement |
| spam_score | `checks/spam_score.py` | 59 weighted triggers |
| dark_mode | `checks/dark_mode.py` | color-scheme meta, prefers-color-scheme |
| accessibility | `checks/accessibility.py` | WCAG AA, 24 checks |
| fallback | `checks/fallback.py` | MSO conditionals, VML |
| image_optimization | `checks/image_optimization.py` | 10 rules × 6 groups |
| brand_compliance | `checks/brand_compliance.py` | Per-project brand rules |
| personalisation_syntax | `checks/personalisation_syntax.py` | ESP syntax validation |
| deliverability | `checks/deliverability.py` | ISP-aware, 4 dimensions |
| liquid_syntax | `checks/liquid_syntax.py` | Liquid template syntax |

**Check Protocol:** `app/qa_engine/checks/__init__.py`
```python
class QACheckProtocol(Protocol):
    name: str
    async def run(self, html: str, config: QACheckConfig | None = None) -> QACheckResult: ...
```

**Existing Calibration:** `app/ai/agents/evals/qa_calibration.py` — `run_qa_on_traces()` → `calibrate_qa()` → `build_qa_report()`. Uses `QACalibrationResult` dataclass with agreement_rate, false_pass_rate, false_fail_rate. Covers 11 of 14 checks (`QA_CHECK_NAMES`).

**Golden References:** `app/ai/agents/evals/golden_references.py` — `load_golden_references()` loads from `email-templates/components/golden-references/index.yaml`. 14 HTML files with criteria/agent mappings. `GoldenReference` frozen dataclass (name, html, criteria, agents, verified_date, source_file).

**Golden Cases:** `app/ai/agents/evals/golden_cases.py` — 7 `GoldenCase` entries with `expected_qa_checks: dict[str, bool]`. These already have per-check expected outcomes.

**Config Pattern:** `app/core/config.py` — nested Pydantic. QA has `QAChaosConfig`, `QAPropertyTestingConfig`, `QADeliverabilityConfig`, etc. Check-level via `app/qa_engine/check_config.py:QACheckConfig(enabled, threshold, params)`.

**Routes:** `app/qa_engine/routes.py` — POST `/qa/run`, `/qa/chaos`, `/qa/property-test`; GET `/qa/results/{id}`, `/qa/results`. All require `get_current_user`, admin checks where needed.

**Exceptions:** `app/qa_engine/exceptions.py` — `QARunFailedError(AppError)`, `QAResultNotFoundError(NotFoundError)`, `QAOverrideNotAllowedError(ForbiddenError)`.

## Test Landscape

**QA Tests:** 26 files, ~7.5K lines in `app/qa_engine/tests/`
- `conftest.py` (130 lines): `make_qa_result()`, `make_qa_check()`, `make_qa_override()`, `make_qa_check_result()`, `sample_html_valid`, `sample_html_minimal` fixtures
- `test_service.py` (301 lines): AsyncMock db + repository, `service()` fixture
- `test_checks.py` (1944 lines): Direct check invocation `await check.run(html)`

**Eval Tests:** 28 files in `app/ai/agents/evals/tests/`
- `test_qa_calibration.py` (104 lines): Agreement, false-pass/fail, threshold tuning
- `test_golden_references.py` (147 lines): Loader, criterion mapping, validation
- `test_golden_cases.py` (55 lines): Case definitions and runner

**Patterns:** All async (`@pytest.mark.asyncio`), factory-based, direct check invocation without mocking. `QACalibrationResult` used for precision/recall tracking.

**Golden reference YAMLs** don't have `expected_qa` fields yet — only `GoldenCase` has `expected_qa_checks`.

## Type Check Baseline

| Directory | pyright errors | mypy errors |
|-----------|---------------|-------------|
| `app/qa_engine/` | 14 (mostly test-only) | 1 (redundant cast) |
| `app/ai/agents/evals/` | 9 (mostly test-only) | 3 (minor) |

## Files to Create/Modify

### New Files
- `app/qa_engine/meta_eval.py` — `MetaEvaluator` class + dataclasses
- `app/qa_engine/meta_eval_routes.py` — Admin-only API endpoints
- `app/qa_engine/tests/test_meta_eval.py` — 10 tests

### Modified Files
- `app/core/config.py` — Add `QAMetaEvalConfig` to `QAConfig` (or top-level)
- `app/qa_engine/routes.py` — Include meta_eval router
- `email-templates/components/golden-references/index.yaml` — Add `expected_qa` per reference

## Implementation Steps

### Step 1: Ground-Truth Labels on Golden References

Extend `email-templates/components/golden-references/index.yaml` entries with `expected_qa`:

```yaml
references:
  - name: "VML Background Image"
    file: "vml-background-image.html"
    # ... existing fields ...
    expected_qa:
      html_validation: pass
      css_support: pass
      dark_mode: fail    # no dark mode in VML-only snippet
      accessibility: fail # no alt text context
      fallback: pass      # MSO conditionals present
```

Only label checks where the snippet is meaningful (snippets are ≤80 lines, not full emails — some checks like `file_size` or `spam_score` won't apply to snippets).

### Step 2: Schemas & Dataclasses — `app/qa_engine/meta_eval.py`

```python
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

@dataclass(frozen=True)
class CheckEvalResult:
    check_name: str
    tp: int
    fp: int
    tn: int
    fn: int
    precision: float  # tp / (tp + fp), 0.0 if no positives
    recall: float     # tp / (tp + fn), 0.0 if no positives
    f1: float         # harmonic mean
    specificity: float  # tn / (tn + fp)
    current_threshold: Any
    recommended_threshold: Any | None = None

@dataclass(frozen=True)
class ThresholdRecommendation:
    check_name: str
    current: Any
    recommended: Any
    improvement_f1: float
    reasoning: str

@dataclass(frozen=True)
class MetaEvalReport:
    checks: dict[str, CheckEvalResult]
    overall_f1: float
    timestamp: datetime
    recommendations: list[ThresholdRecommendation]
    golden_count: int
    adversarial_count: int
```

### Step 3: MetaEvaluator Class — `app/qa_engine/meta_eval.py`

```python
class MetaEvaluator:
    def __init__(
        self,
        checks: list[QACheckProtocol],
        golden_loader: Callable[[], tuple[GoldenReference, ...]],
        *,
        fp_threshold: float = 0.10,
        fn_threshold: float = 0.05,
    ) -> None: ...

    async def evaluate_all_checks(
        self,
        adversarial_emails: list[AdversarialEmail] | None = None,
    ) -> MetaEvalReport: ...

    async def evaluate_check(
        self,
        check_name: str,
        samples: list[LabeledSample],
    ) -> CheckEvalResult: ...
```

Key design decisions:
- Accept `checks` list (from `ALL_CHECKS`) rather than `QAService` — avoid DB dependency, test without mocking
- `LabeledSample` = `(html: str, expected: dict[str, Literal["pass", "fail", "skip"]])` — skip for checks that don't apply to a snippet
- Golden refs filtered: only refs with `expected_qa` labels participate
- Merge golden + adversarial samples, run each check, compare against labels
- Compute confusion matrix per check
- Generate `ThresholdRecommendation` when FP > `fp_threshold` or FN > `fn_threshold`

`AdversarialEmail` dataclass:
```python
@dataclass(frozen=True)
class AdversarialEmail:
    name: str
    html: str
    expected_qa: dict[str, str]  # check_name -> "pass"|"fail"
    target_check: str  # which check this adversarial case targets
```

### Step 4: Config — `app/core/config.py`

Add to existing QA config section:

```python
class QAMetaEvalConfig(BaseModel):
    enabled: bool = True
    fp_threshold: float = 0.10
    fn_threshold: float = 0.05
```

Access via `settings.qa.meta_eval.enabled` (nested under QA). Use `env_nested_delimiter="__"` → `QA__META_EVAL__ENABLED`.

### Step 5: Routes — `app/qa_engine/meta_eval_routes.py`

```python
router = APIRouter(prefix="/api/v1/qa/meta-eval", tags=["qa-meta-eval"])

@router.post("", response_model=MetaEvalReportResponse)
async def run_meta_eval(
    request: Request,
    _admin: User = Depends(require_admin),
) -> MetaEvalReportResponse:
    """Run full meta-evaluation of all QA checks against golden + adversarial data."""
    ...

@router.get("/latest", response_model=MetaEvalReportResponse)
async def get_latest_report(
    _admin: User = Depends(require_admin),
) -> MetaEvalReportResponse:
    """Retrieve most recent meta-eval report."""
    ...
```

Report storage: JSON file at `traces/qa_meta_eval_latest.json` (matches existing `traces/` pattern for calibration artifacts). No DB table needed — reports are ephemeral artifacts like calibration results.

Response schemas in same file or `app/qa_engine/schemas.py`:

```python
class CheckEvalResultResponse(BaseModel):
    check_name: str
    tp: int; fp: int; tn: int; fn: int
    precision: float; recall: float; f1: float; specificity: float
    current_threshold: Any
    recommended_threshold: Any | None

class ThresholdRecommendationResponse(BaseModel):
    check_name: str
    current: Any; recommended: Any
    improvement_f1: float; reasoning: str

class MetaEvalReportResponse(BaseModel):
    checks: dict[str, CheckEvalResultResponse]
    overall_f1: float
    timestamp: datetime
    recommendations: list[ThresholdRecommendationResponse]
    golden_count: int; adversarial_count: int
```

### Step 6: Wire Into Router — `app/qa_engine/routes.py`

Add `include_router(meta_eval_router)` to the QA router, gated by config:

```python
if settings.qa.meta_eval.enabled:
    from app.qa_engine.meta_eval_routes import router as meta_eval_router
    router.include_router(meta_eval_router)
```

### Step 7: Integration With Existing Calibration

In `app/ai/agents/evals/qa_calibration.py`, add optional bridge:

```python
def meta_eval_to_calibration_results(
    report: MetaEvalReport,
) -> list[QACalibrationResult]:
    """Convert MetaEvalReport to QACalibrationResult format for pipeline compat."""
```

This lets the calibration tracker (`calibration_tracker.py`) consume meta-eval results for regression tracking against baselines.

### Step 8: Golden Reference YAML Labels

Label each of the 14 golden references with expected QA outcomes. Use "skip" for checks that don't meaningfully apply to snippets:

| Reference | html_val | css_sup | dark_mode | access | fallback | Other |
|-----------|----------|---------|-----------|--------|----------|-------|
| vml-background-image | pass | pass | skip | skip | pass | — |
| dark-mode-complete | pass | pass | pass | skip | pass | — |
| accessibility-compliant | pass | pass | skip | pass | skip | — |
| esp-braze-liquid | pass | pass | skip | skip | skip | personalisation: pass |
| ... | ... | ... | ... | ... | ... | ... |

### Step 9: Tests — `app/qa_engine/tests/test_meta_eval.py`

10 tests:

1. `test_evaluate_check_all_pass` — Golden ref where check passes, verify TP counted
2. `test_evaluate_check_all_fail` — Adversarial email triggers failure, verify correct classification
3. `test_evaluate_check_mixed` — Mix of pass/fail, verify precision/recall/F1 math
4. `test_skip_labels_excluded` — Samples with "skip" label excluded from confusion matrix
5. `test_threshold_recommendation_high_fp` — FP > 10% triggers recommendation
6. `test_threshold_recommendation_high_fn` — FN > 5% triggers recommendation
7. `test_evaluate_all_checks` — Full pipeline with multiple checks, verify `MetaEvalReport` shape
8. `test_overall_f1_weighted` — Overall F1 is macro-average across checks
9. `test_meta_eval_route_admin_only` — Non-admin gets 403
10. `test_meta_eval_latest_route` — Returns stored report

**Test Fixtures:**
```python
@pytest.fixture
def labeled_golden() -> list[LabeledSample]:
    """Use sample_html_valid from conftest with expected pass labels."""
    ...

@pytest.fixture
def labeled_adversarial() -> list[LabeledSample]:
    """Minimal HTML designed to fail specific checks."""
    ...
```

## Preflight Warnings

- `QACheckResult` schema in `app/qa_engine/schemas.py` may differ from the `QACalibrationResult` dataclass in `app/ai/agents/evals/schemas.py` — don't conflate them
- Golden references are snippets (≤80 lines), not full emails — `file_size`, `spam_score`, `link_validation` checks may not produce meaningful results on snippets; use "skip" labels
- `ALL_CHECKS` includes `css_audit` which requires optimization metadata — may need to mock or skip in meta-eval context
- `brand_compliance` requires per-project brand rules — skip or provide default brand config

## Security Checklist

| Item | Status |
|------|--------|
| Auth on endpoints | `require_admin` dependency on both routes |
| Rate limiting | Inherit from QA router rate limiter |
| Input validation | No user-supplied HTML — golden/adversarial loaded from files |
| Error responses | Generic errors, no internal types leaked |
| No secrets in reports | Report contains check names + metrics only |

## Verification

- [ ] `make check` passes
- [ ] `POST /api/v1/qa/meta-eval` returns `MetaEvalReport` with per-check precision/recall
- [ ] Admin-only enforcement (non-admin → 403)
- [ ] `GET /api/v1/qa/meta-eval/latest` returns stored report
- [ ] File size check with low threshold → high FP detected → recommendation emitted
- [ ] Accessibility check on template missing alt text → correct TP/FP classification
- [ ] "skip" labels excluded from confusion matrix
- [ ] Overall F1 computed as macro-average
- [ ] pyright errors ≤ 14 (qa_engine) + 9 (evals) = 23 total
- [ ] 10 tests pass
