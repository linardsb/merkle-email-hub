# Tech Debt 06 — `custom_checks.py` Split + 14-Check Boilerplate Collapse

**Source:** `TECH_DEBT_AUDIT.md`
**Scope:** Mechanical split of the 3,738-LOC god file into 11 domain modules + factory for the 14 RuleEngine boilerplate classes. ~900 LOC removed.
**Goal:** Each `custom_checks/*.py` is 250–400 LOC, single-domain. Each `checks/*.py` is replaced by a registry entry.
**Estimated effort:** ½ to full session.
**Prerequisite:** None.

## Findings addressed

F018 (`custom_checks.py` 3738 LOC, 125 funcs, 11 `_param` copies) — Critical
F019 (14 QA check classes are RuleEngine boilerplate) — High
F029 (blanket `# ruff: noqa: ARG001` on 3738-LOC file) — Medium
F067 (no per-check tests; `test_checks.py` 1944 LOC mega-file) — Medium

## Pre-flight

```bash
git checkout -b refactor/tech-debt-06-qa-engine-split
make check
make test app/qa_engine/  # baseline
```

Before changing anything, capture a snapshot of QA results on the 14 golden templates:
```bash
make eval-golden  # or equivalent — must produce reproducible output
cp traces/qa_golden_baseline.json traces/qa_golden_baseline.before.json
```

## Part A — Split `custom_checks.py` (F018)

### A1. Create the package

```
app/qa_engine/custom_checks/
  __init__.py       ← imports all 11 domain modules to trigger register_custom_check
  _helpers.py       ← single _param helper, iter_capped generator, shared lxml utils
  html.py           ← lines  1-844   (was: html structure)
  a11y.py           ← lines  845-1619 (was: a11y_param block)
  mso.py            ← lines  1620-1724
  dark_mode.py      ← lines  1725-2068
  link.py           ← lines  2069-2274
  file_size.py      ← lines  2275-2435
  spam.py           ← lines  2436-2702
  brand.py          ← lines  2703-2891
  image.py          ← lines  2892-3192
  css.py            ← lines  3193-3472
  personalisation.py ← lines  3473-3737
```

The line ranges come from the section comments in the original file (`app/qa_engine/custom_checks.py:158, 845, 1620, …`).

### A2. Extract `_param`

Single helper in `app/qa_engine/custom_checks/_helpers.py`:
```python
from typing import Any
from app.qa_engine.schemas import CheckConfig

def param(config: CheckConfig, key: str, default: Any = None) -> Any:
    return config.params.get(key, default)

def iter_capped(doc, tag: str, cap: int):
    """Iterate elements with a count cap; addresses F024 (per-check generator dup)."""
    count = 0
    for elem in doc.iter(tag):
        if cap and count >= cap:
            break
        yield elem
        count += 1
```

Replace all 11 `_param`/`_a11y_param`/etc. with imports of `param`.

### A3. Side-effect imports

`app/qa_engine/custom_checks/__init__.py`:
```python
"""Custom QA checks. Importing this package triggers register_custom_check
side effects in each domain module."""
from app.qa_engine.custom_checks import (
    html, a11y, mso, dark_mode, link, file_size,
    spam, brand, image, css, personalisation,
)
__all__ = [...]
```

The original `app/qa_engine/custom_checks.py` becomes a 3-line shim re-exporting from the package, **OR** — preferred — it is deleted and any importer moves to `from app.qa_engine.custom_checks import ...`. Verify import sites:
```bash
rg "from app.qa_engine.custom_checks" app/ --type py
```

### A4. Drop the blanket `# ruff: noqa: ARG001`

Apply per-function `# noqa: ARG001` only where the protocol genuinely forces unused params. Run `ruff check app/qa_engine/custom_checks/` and resolve real warnings.

## Part B — Collapse 14 RuleEngine boilerplate classes (F019)

### B1. Create the factory

**New file:** `app/qa_engine/checks/_factory.py`:
```python
from dataclasses import dataclass
from typing import Callable
from lxml import html as lxml_html
from app.qa_engine.rule_engine import RuleEngine
from app.qa_engine.rules_loader import load_rules
from app.qa_engine.schemas import QACheckResult

@dataclass(frozen=True)
class RuleEngineCheck:
    name: str
    rules_path: str
    severity: str = "warning"
    cache_clear: Callable[[], None] | None = None

    async def run(self, html_str: str, config) -> QACheckResult:
        if self.cache_clear is not None:
            self.cache_clear()
        rules = load_rules(self.rules_path)
        doc = lxml_html.document_fromstring(html_str)
        engine = RuleEngine(rules)
        violations = await engine.evaluate(doc, config)
        return QACheckResult(
            name=self.name, severity=self.severity, violations=violations,
        )
```

### B2. Registry table

**Replace** `app/qa_engine/checks/__init__.py` with:
```python
from app.qa_engine.checks._factory import RuleEngineCheck
from app.qa_engine.checks.css_audit import CssAuditCheck   # bespoke
from app.qa_engine.checks.deliverability import DeliverabilityCheck  # bespoke

CHECKS = [
    RuleEngineCheck("html_validation", "rules/html_validation.yaml"),
    RuleEngineCheck("dark_mode",        "rules/dark_mode.yaml",
                    cache_clear=clear_dark_mode_cache),
    RuleEngineCheck("accessibility",    "rules/accessibility.yaml"),
    RuleEngineCheck("fallback",         "rules/fallback.yaml"),
    RuleEngineCheck("file_size",        "rules/file_size.yaml",
                    cache_clear=clear_file_size_cache),
    RuleEngineCheck("link_validation",  "rules/link_validation.yaml",
                    cache_clear=clear_link_cache),
    RuleEngineCheck("image_optimization","rules/image_optimization.yaml",
                    cache_clear=clear_image_cache),
    RuleEngineCheck("brand_compliance", "rules/brand_compliance.yaml"),
    RuleEngineCheck("personalisation_syntax", "rules/personalisation_syntax.yaml"),
    RuleEngineCheck("spam_score",       "rules/spam_score.yaml"),
    RuleEngineCheck("css_support",      "rules/css_support.yaml"),
    RuleEngineCheck("liquid_syntax",    "rules/liquid_syntax.yaml"),
    RuleEngineCheck("rendering_resilience", "rules/rendering_resilience.yaml"),
    CssAuditCheck(),
    DeliverabilityCheck(),
]
```

### B3. Delete the 13 boilerplate check classes

Delete:
- `app/qa_engine/checks/html_validation.py`
- `dark_mode.py`
- `accessibility.py`
- `fallback.py`
- `file_size.py`
- `link_validation.py`
- `image_optimization.py`
- `brand_compliance.py`
- `personalisation_syntax.py`
- `spam_score.py`
- `css_support.py`
- `liquid_syntax.py`
- `rendering_resilience.py`

Keep `css_audit.py` and `deliverability.py` (bespoke).

### B4. Update the QA engine

`app/qa_engine/service.py` — wherever it imports the check classes by name, switch to iterating `CHECKS` from the registry. Preserve any per-check skip/disable logic via `config.disabled_checks`.

### B5. Address F039: `clear_*_cache()` location

The factory accepts `cache_clear` as a callable. The original placement of `clear_link_cache()` *inside* `run()` (per-invocation, useless) becomes the same in the factory — but the cache lifetime is now visible at the registry. Consider whether each cache should be removed altogether (it's per-invocation = no caching). For this plan, preserve current behaviour; address as follow-up.

## Part C — Test split (F067)

### C1. Per-check test files

Split `app/qa_engine/tests/test_checks.py` (1944 LOC) into:
- `test_html_validation.py`
- `test_dark_mode.py`
- ...one per check.

Each file inherits a shared `RuleEngineTestCase` base (in `app/qa_engine/tests/_base.py`) covering: rule loading, evaluation against fixture HTML, severity mapping.

### C2. Per-check fixtures

Move check-specific fixtures from the mega-file into per-check `tests/fixtures/{check_name}/` directories.

## Verification

```bash
make check
make test app/qa_engine/ -v

# QA output equivalence:
make eval-golden
diff traces/qa_golden_baseline.json traces/qa_golden_baseline.before.json
# MUST be empty (refactor preserves behaviour)

# LOC reduction:
wc -l app/qa_engine/custom_checks/*.py
# Each file 250-400; total still ~3700 (split, not deleted)

# Boilerplate removed:
ls app/qa_engine/checks/  # 4 files: __init__, _factory, css_audit, deliverability
```

## Rollback

The factory + registry approach is reversible per check: revert one file, re-add a per-check class, and remove from `CHECKS` list. Full rollback is a single PR revert.

## Risk notes

- **`register_custom_check` order matters.** Some checks may depend on ordering of registration via the side-effect import. Test on a fresh process to verify.
- **The `qa_golden_baseline.json` diff must be empty.** Any divergence means the split changed semantics — inspect, fix, re-run. Don't ship until clean.
- **`load_rules` caching**: the factory calls it on every `run()`. If `load_rules` was previously cached at import time (per check class), this is a perf regression. Add `@functools.lru_cache` to `load_rules` if needed.
- **`# ruff: noqa: ARG001` blanket** removal will surface real warnings — fix at the source, don't re-blanket.

## Done when

- [ ] `app/qa_engine/custom_checks.py` (3738 LOC) → 11 modules of 250-400 LOC each + `_helpers.py`.
- [ ] 13 RuleEngine check classes deleted; `CHECKS` registry in `__init__.py`.
- [ ] `qa_golden_baseline.json` diff empty.
- [ ] Per-check test files exist; `test_checks.py` mega-file deleted.
- [ ] `make check` green.
- [ ] PR titled `refactor(qa-engine): split custom_checks + collapse RuleEngine boilerplate (F018 F019)`.
- [ ] Mark F018, F019, F029, F067 as **RESOLVED**.
