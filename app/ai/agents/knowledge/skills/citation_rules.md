<!-- L4 source: none (original content — answer formatting rules) -->
# Citation & Answer Formatting Rules

## Citation Format

### In-Line Citations
Reference sources immediately after the claim:
```
Border-radius is not supported in Outlook desktop [Can I Email: border-radius].
Use VML for rounded elements in Outlook [Outlook VML Reference].
```

### Source List
At the end of the answer, list all sources:
```
Sources:
- Can I Email: border-radius (support data)
- Outlook VML Reference (code patterns)
- Email Client CSS Support Guide (compatibility matrix)
```

## Grounding Rules

### Rule 1: Cite, Don't Fabricate
Every factual claim about client support must reference a knowledge base document.
If no document covers the topic, say so explicitly.

### Rule 2: Distinguish Source Types
- **Authoritative:** Can I Email, official documentation → state as fact
- **Community:** Blog posts, tutorials → "According to [source]..."
- **Inferred:** Synthesis from multiple sources → "Based on available sources..."
- **Unknown:** No sources → "I don't have specific data on this"

### Rule 3: Version and Date Awareness
Email client behavior changes over time. Note when:
- Data may be outdated: "As of [date], [claim]..."
- Version-specific: "In Outlook 2019+, [behavior]..."
- Recently changed: "Gmail recently updated support for..."

## Hedging Language

Use appropriate confidence language:

### High Confidence (direct source match)
- "X is supported in Y"
- "X does not work in Y"
- "The recommended approach is..."

### Medium Confidence (synthesized from sources)
- "Based on available documentation, X should work..."
- "Testing indicates that X behaves as..."
- "The general consensus is..."

### Low Confidence (limited sources)
- "I don't have definitive data, but..."
- "This may vary — I'd recommend testing"
- "Based on general email development principles..."

## Answer Structure Template

```
## [Direct Answer]

[1-2 sentence answer to the question]

## Details

[Explanation with citations]

## Code Example (if applicable)

[Email-safe HTML/CSS code]

## Client Support

| Client | Support | Notes |
|--------|---------|-------|
| ... | ... | ... |

## Sources

- [Source 1]
- [Source 2]
```

## Anti-Patterns

### ❌ Uncited Claims
"Flexbox works in all modern email clients"
(This is false — cite the actual support data)

### ❌ Over-Confident Answers
"This will definitely work in all clients"
(Always note limitations and testing recommendations)

### ❌ Fabricated Sources
"According to the Gmail Developer Documentation..."
(Only cite sources actually in the knowledge base)

### ✅ Correct Pattern
"Flexbox is only supported in Apple Mail and a few WebKit-based clients [Can I Email: flexbox]. For broad compatibility, use table-based layouts with inline-block divs for responsive stacking."
