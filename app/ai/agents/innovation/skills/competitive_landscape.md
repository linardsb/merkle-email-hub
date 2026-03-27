---
version: "1.0.0"
---

<!-- L4 source: none (original content — competitive analysis) -->
# L3: Competitive Landscape Analysis

## When to Use
Apply this skill when the technique request mentions competitors, market positioning,
or asks about unique capabilities vs other email platforms.

## Competitive Intelligence Guidelines

### Assessment Framework
When evaluating a technique against competitors:

1. **Availability Check**: Which competitors support this technique?
   - Available data is injected as `--- COMPETITIVE LANDSCAPE ---` context
   - Use this data as ground truth, not your own knowledge

2. **Differentiation Value**:
   - HIGH: No competitor supports this technique — unique Hub advantage
   - MEDIUM: Few competitors support it — partial differentiation
   - LOW: Most competitors already support it — table stakes

3. **Feasibility × Differentiation Matrix**:
   | | High Feasibility | Low Feasibility |
   |---|---|---|
   | **High Differentiation** | SHIP IT — unique + practical | PROTOTYPE — unique but risky |
   | **Low Differentiation** | MATCH — table stakes, must have | SKIP — not worth the complexity |

### Output Additions
When competitive context is available, add to your feasibility assessment:

```
### 5. Competitive Positioning
- Competitors supporting this technique: [list]
- Competitors NOT supporting: [list]
- Differentiation value: HIGH / MEDIUM / LOW
- Strategic recommendation: [one sentence]
```

### Rules
- Only cite competitors from the injected competitive context data
- Never fabricate competitor capabilities not in the data
- If no competitive context is injected, skip the competitive positioning section
- Focus on technique feasibility first, competitive positioning second