# Plan: 49.1 Sibling Pattern Detector — Repeated-Content Grouping

## Context

The converter pipeline processes Figma sections independently via `match_all()`. When Figma has N structurally identical siblings (e.g., 5 icon+heading+body "reasons" blocks), they either become N independent sections or get flattened into one oversized section. Neither produces correct HTML. A generic sibling detector inserts between layout analysis and component matching to group consecutive similar sections into `RepeatingGroup` objects.

## Research Summary

| File | Role | Key symbols |
|------|------|-------------|
| `app/design_sync/figma/layout_analyzer.py:22-142` | Section types, `EmailSection`, `ColumnLayout` | `EmailSectionType` (11 values incl. DIVIDER/SPACER), `ColumnLayout` (4 values), `EmailSection` (frozen, 25 fields) |
| `app/design_sync/component_matcher.py:89` | `match_all()` → `list[ComponentMatch]` | Iterates sections, calls `match_section()` per item |
| `app/design_sync/converter_service.py:661` | Integration point | `matches = match_all(layout.sections, ...)` then loop at `:696` |
| `app/design_sync/protocol.py:110` | `DesignNode` with `fill_color` | Parent wrapper's fill_color for container bgcolor |
| `app/core/config.py:342-422` | `DesignSyncConfig` | Pattern: `field_name: type = default  # ENV_VAR` |

**Derived fields for signatures** (not on `EmailSection` directly):
- `len(section.images)` → image count
- `len(section.texts)` → text count
- `len(section.buttons)` → button count
- `any(t.is_heading for t in section.texts)` → has_heading
- `section.height` bucketed to 20px → height bucket
- `section.column_layout` → layout type

## Test Landscape

| Asset | Location |
|-------|----------|
| Factory `_make_section()` | `app/design_sync/tests/test_component_matcher.py:24-60` |
| Factory `_text()`, `_image()`, `_button()` | Same file `:63-74` |
| Factory `_make_layout()` | `app/design_sync/tests/test_spacing_bridge.py:14-18` |
| Conftest `make_design_node()` | `app/design_sync/tests/conftest.py` |
| Fixture JSON files | `app/design_sync/figma/tests/fixtures/` (5 files) |

Conventions: class-based test grouping, `_make_*` factories, frozen dataclasses constructed directly, `assert m.component_slug == "..."` style.

## Type Check Baseline

| Tool | Errors |
|------|--------|
| Pyright | 261 |
| mypy | 91 (9 files) |

## Files to Create/Modify

### New: `app/design_sync/sibling_detector.py` (~250 lines)

```
SiblingSignature     — frozen dataclass (6 fields)
RepeatingGroup       — frozen dataclass (6 fields)
detect_repeating_groups()  — main entry point
_compute_signature() — EmailSection → SiblingSignature
_signature_similarity() — weighted scoring (6 dimensions)
_SKIP_TYPES          — frozenset of DIVIDER, SPACER
```

### New: `app/design_sync/tests/test_sibling_detector.py` (~350 lines, 14 tests)

### Modify: `app/core/config.py` — 3 new fields on `DesignSyncConfig`

### Modify: `app/design_sync/converter_service.py` — wire detector into `_convert_with_components()`

## Implementation Steps

### Step 1: Config fields (`app/core/config.py:422`)

Add before the closing of `DesignSyncConfig`, after `regression_strict`:

```python
# Sibling pattern detection — repeated-content grouping (Phase 49.1)
sibling_detection_enabled: bool = True  # DESIGN_SYNC__SIBLING_DETECTION_ENABLED
sibling_min_group: int = 2  # DESIGN_SYNC__SIBLING_MIN_GROUP
sibling_similarity_threshold: float = 0.8  # DESIGN_SYNC__SIBLING_SIMILARITY_THRESHOLD
```

### Step 2: `app/design_sync/sibling_detector.py` (new file)

```python
"""Detect N consecutive structurally similar sections and merge into RepeatingGroup."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.logging import get_logger
from app.design_sync.figma.layout_analyzer import (
    ColumnLayout,
    EmailSection,
    EmailSectionType,
)

logger = get_logger(__name__)

_SKIP_TYPES: frozenset[EmailSectionType] = frozenset({
    EmailSectionType.DIVIDER,
    EmailSectionType.SPACER,
})


@dataclass(frozen=True)
class SiblingSignature:
    """Structural fingerprint of a section for similarity comparison."""

    image_count: int
    text_count: int
    button_count: int
    has_heading: bool
    column_layout: ColumnLayout
    approx_height_bucket: int  # height // 20


@dataclass(frozen=True)
class RepeatingGroup:
    """A group of structurally similar consecutive sections."""

    sections: list[EmailSection]
    container_bgcolor: str | None = None
    container_padding: tuple[float, float, float, float] | None = None
    pattern_component: str | None = None
    repeat_count: int = 0
    group_confidence: float = 0.0

    def __post_init__(self) -> None:
        if self.repeat_count == 0:
            object.__setattr__(self, "repeat_count", len(self.sections))
```

**Core logic:**

```python
def detect_repeating_groups(
    sections: list[EmailSection],
    *,
    min_group_size: int = 2,
    similarity_threshold: float = 0.8,
) -> list[EmailSection | RepeatingGroup]:
    """Detect consecutive structurally similar sections and merge into groups.

    Returns mixed list: unchanged EmailSection for singles, RepeatingGroup for runs.
    DIVIDER/SPACER sections are never grouped but don't break runs.
    """
    if len(sections) < min_group_size:
        return list(sections)

    signatures = [_compute_signature(s) for s in sections]
    result: list[EmailSection | RepeatingGroup] = []
    i = 0

    while i < len(sections):
        if sections[i].section_type in _SKIP_TYPES:
            result.append(sections[i])
            i += 1
            continue

        # Try to extend a run of similar sections starting at i
        run = [i]
        j = i + 1
        skipped_indices: list[int] = []

        while j < len(sections):
            if sections[j].section_type in _SKIP_TYPES:
                skipped_indices.append(j)
                j += 1
                continue

            sim = _signature_similarity(signatures[i], signatures[j])
            if sim >= similarity_threshold:
                run.append(j)
                j += 1
            else:
                break

        if len(run) >= min_group_size:
            run_sections = [sections[idx] for idx in run]
            avg_sim = _average_pairwise_similarity(
                [signatures[idx] for idx in run]
            )
            container_bg = run_sections[0].bg_color

            group = RepeatingGroup(
                sections=run_sections,
                container_bgcolor=container_bg,
                group_confidence=avg_sim,
            )
            # Emit skipped DIVIDER/SPACER sections before the group
            for sk in skipped_indices:
                if sk < run[0]:
                    result.append(sections[sk])
            result.append(group)
            logger.info(
                "sibling.group_detected",
                repeat_count=len(run_sections),
                confidence=round(avg_sim, 3),
                first_node=run_sections[0].node_id,
            )
            i = j
        else:
            result.append(sections[i])
            i += 1

    return result
```

**Signature computation:**

```python
def _compute_signature(section: EmailSection) -> SiblingSignature:
    height_bucket = int((section.height or 0) // 20)
    return SiblingSignature(
        image_count=len(section.images),
        text_count=len(section.texts),
        button_count=len(section.buttons),
        has_heading=any(t.is_heading for t in section.texts),
        column_layout=section.column_layout,
        approx_height_bucket=height_bucket,
    )
```

**Similarity scoring (weighted 6-dimension match):**

```python
_WEIGHTS: dict[str, float] = {
    "image_count": 0.30,
    "text_count": 0.25,
    "button_count": 0.15,
    "has_heading": 0.15,
    "column_layout": 0.10,
    "height_bucket": 0.05,
}

def _signature_similarity(a: SiblingSignature, b: SiblingSignature) -> float:
    score = 0.0
    score += _WEIGHTS["image_count"] * (1.0 if a.image_count == b.image_count else 0.0)
    score += _WEIGHTS["text_count"] * (1.0 if a.text_count == b.text_count else 0.0)
    score += _WEIGHTS["button_count"] * (1.0 if a.button_count == b.button_count else 0.0)
    score += _WEIGHTS["has_heading"] * (1.0 if a.has_heading == b.has_heading else 0.0)
    score += _WEIGHTS["column_layout"] * (1.0 if a.column_layout == b.column_layout else 0.0)
    score += _WEIGHTS["height_bucket"] * (
        1.0 if abs(a.approx_height_bucket - b.approx_height_bucket) <= 1 else 0.0
    )
    return score

def _average_pairwise_similarity(sigs: list[SiblingSignature]) -> float:
    if len(sigs) < 2:
        return 1.0
    total = sum(
        _signature_similarity(sigs[i], sigs[j])
        for i in range(len(sigs))
        for j in range(i + 1, len(sigs))
    )
    pairs = len(sigs) * (len(sigs) - 1) / 2
    return total / pairs
```

### Step 3: Wire into converter (`converter_service.py:660`)

Insert between the imports and `match_all()` call:

```python
# After line 658 (existing imports), add:
from app.design_sync.sibling_detector import RepeatingGroup, detect_repeating_groups

# Replace lines 660-665 with:
# Detect repeating sibling groups (Phase 49.1)
grouped_sections: list[EmailSection | RepeatingGroup] = list(layout.sections)
if ds_settings.sibling_detection_enabled:
    grouped_sections = detect_repeating_groups(
        layout.sections,
        min_group_size=ds_settings.sibling_min_group,
        similarity_threshold=ds_settings.sibling_similarity_threshold,
    )

# Flatten groups back to sections for match_all (groups handled in 49.2 renderer)
flat_sections = []
group_map: dict[int, RepeatingGroup] = {}  # section_idx → group
for item in grouped_sections:
    if isinstance(item, RepeatingGroup):
        start_idx = len(flat_sections)
        for section in item.sections:
            group_map[len(flat_sections)] = item
            flat_sections.append(section)
    else:
        flat_sections.append(item)

matches = match_all(
    flat_sections,
    container_width=container_width,
    image_urls=image_urls,
)
```

> Note: `group_map` is prepared for 49.2 (renderer) to wrap grouped sections in a shared container `<table>`. For 49.1 alone, the grouping metadata is emitted via structured logging and the `RepeatingGroup` objects are available for downstream consumers.

### Step 4: Tests (`app/design_sync/tests/test_sibling_detector.py`)

14 tests across 4 classes:

**`TestSiblingSignature` (3 tests):**
1. `test_compute_signature_basic` — section with 1 image, 2 texts, heading → correct signature
2. `test_height_bucketing` — heights 120, 135 → same bucket (6); 160 → different (8)
3. `test_empty_section` — no content → all-zero signature

**`TestSignatureSimilarity` (3 tests):**
4. `test_identical_signatures` — same structure → 1.0
5. `test_completely_different` — all fields differ → 0.0
6. `test_partial_match` — same images/texts, different buttons → 0.85

**`TestDetectRepeatingGroups` (6 tests):**
7. `test_five_identical_sections_grouped` — 5 icon+heading+body → 1 group(5)
8. `test_three_product_cards` — 3 image+text+button → 1 group(3)
9. `test_mixed_sections_only_similar_grouped` — hero, text, 5 reasons, footer → [hero, text, group(5), footer]
10. `test_divider_between_similar_breaks_nothing` — DIVIDER inside run of 3 similar → still group(3), DIVIDER preserved separately
11. `test_single_section_no_grouping` — 1 section → [section]
12. `test_below_min_group_size` — 1 similar pair with min_group=3 → no grouping

**`TestConfig` (2 tests):**
13. `test_threshold_respected` — threshold=1.0 → no groups (minor height diff kills match)
14. `test_disabled_returns_original` — `sibling_detection_enabled=False` → passthrough

All tests use `_make_section()`, `_text()`, `_image()`, `_button()` factory pattern from existing tests.

## Preflight Warnings

- `match_all()` uses `enumerate(sections)` for `section_idx` — flattening groups changes indices. The `section_idx` on `ComponentMatch` will correspond to the flat list position, not the original layout position. This is fine for 49.1 but 49.2 must be aware.
- `converter_service.py` reads `ds_settings` at line 691 — reuse the same binding for the new config fields (don't call `get_settings()` twice).

## Security Checklist

No new endpoints, no user input, no external API calls. Pure in-memory data transformation of already-validated `EmailSection` objects. No security concerns.

## Verification

- [ ] `make check` passes
- [ ] `uv run pytest app/design_sync/tests/test_sibling_detector.py -v` — 14 tests pass
- [ ] Pyright errors ≤ 261 (baseline)
- [ ] mypy errors ≤ 91 (baseline)
- [ ] 5 identical sections → `RepeatingGroup(repeat_count=5)`
- [ ] DIVIDER/SPACER sections never grouped
- [ ] Config flags respected (enable/disable, threshold, min_group)
