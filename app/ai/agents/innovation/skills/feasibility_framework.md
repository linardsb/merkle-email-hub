---
version: "1.0.0"
---

<!-- L4 source: none (original content — risk assessment template) -->
# Feasibility Assessment Framework

## Assessment Template

For every experimental technique, evaluate along these dimensions:

### 1. Client Coverage (Weight: 30%)
What percentage of the target audience will see the technique work?

| Coverage | Score | Description |
|----------|-------|-------------|
| > 80% | 5/5 | Works in Gmail + Apple Mail + Outlook |
| 60-80% | 4/5 | Works in Gmail + Apple Mail (not Outlook) |
| 40-60% | 3/5 | Works in Apple Mail + some webmail |
| 20-40% | 2/5 | Apple Mail + Thunderbird only |
| < 20% | 1/5 | Single client or experimental |

### 2. Fallback Quality (Weight: 25%)
How good is the experience for unsupported clients?

| Quality | Score | Description |
|---------|-------|-------------|
| Seamless | 5/5 | Unsupported clients see equivalent content, different presentation |
| Good | 4/5 | Minor visual difference, no information loss |
| Acceptable | 3/5 | Noticeable difference but functional |
| Poor | 2/5 | Significant degradation, some content lost |
| Broken | 1/5 | Unsupported clients see broken layout or missing content |

### 3. File Size Impact (Weight: 15%)
How much does this technique add to the HTML size?

| Impact | Score | Description |
|--------|-------|-------------|
| Minimal | 5/5 | < 2KB additional |
| Low | 4/5 | 2-5KB additional |
| Moderate | 3/5 | 5-15KB additional |
| High | 2/5 | 15-30KB additional |
| Excessive | 1/5 | > 30KB additional (Gmail clipping risk) |

### 4. Implementation Complexity (Weight: 15%)
How difficult is it to implement and maintain?

| Complexity | Score | Description |
|-----------|-------|-------------|
| Simple | 5/5 | Copy-paste, no customization needed |
| Low | 4/5 | Minor modifications for each use |
| Moderate | 3/5 | Requires understanding the technique |
| High | 2/5 | Significant custom work per implementation |
| Very High | 1/5 | Expert-level, fragile, needs extensive testing |

### 5. Risk Level (Weight: 15%)
What's the worst case if something goes wrong?

| Risk | Score | Description |
|------|-------|-------------|
| None | 5/5 | Worst case: no visual enhancement |
| Low | 4/5 | Worst case: slightly different layout |
| Moderate | 3/5 | Worst case: extra whitespace or hidden content |
| High | 2/5 | Worst case: broken layout or overlapping content |
| Critical | 1/5 | Worst case: email is unreadable or links broken |

## Scoring

Weighted score = (Coverage × 0.3) + (Fallback × 0.25) + (Size × 0.15) + (Complexity × 0.15) + (Risk × 0.15)

### Recommendations

| Weighted Score | Recommendation |
|---------------|---------------|
| 4.0 - 5.0 | **Ship it** — Low risk, good coverage |
| 3.0 - 3.9 | **Test further** — Promising but needs validation |
| 2.0 - 2.9 | **Consider carefully** — High risk or low coverage |
| 1.0 - 1.9 | **Avoid** — Too risky or too limited |

## Example Assessment

### Technique: CSS Checkbox Tab Navigation

| Dimension | Score | Notes |
|-----------|-------|-------|
| Coverage | 2/5 | ~30% (Apple Mail + Yahoo) |
| Fallback | 4/5 | Shows all tabs stacked |
| File Size | 3/5 | ~8KB additional CSS |
| Complexity | 3/5 | Moderate — needs careful label-input wiring |
| Risk | 4/5 | Worst case: all content visible (not terrible) |

**Weighted Score:** 3.05 → **Test further**

**Recommendation:** Suitable for promotional emails targeting Apple Mail-heavy audiences.
Not recommended for transactional emails or Outlook-heavy B2B audiences.