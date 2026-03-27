---
version: "1.0.0"
---

<!-- L4 source: docs/SKILL_html-email-css-dom-reference.md -->
# Can I Email — Reference Guide

## Data Structure

Can I Email provides per-property support data similar to Can I Use but for email clients.

### Support Levels
- **Full support (y):** Property works as expected
- **Partial support (a):** Works with caveats or limitations
- **No support (n):** Property is ignored or stripped
- **Unknown (u):** Not tested for this client/version

### Common Lookups

#### "Can I use border-radius in email?"
- Apple Mail: ✅ Full support
- Gmail: ✅ Full support
- Outlook desktop: ❌ No support (use VML for rounded elements)
- Yahoo: ✅ Full support
- Samsung: ✅ Full support
**Answer:** Yes, with Outlook VML fallback or graceful degradation.

#### "Can I use flexbox in email?"
- Apple Mail: ✅ Full support
- Gmail: ❌ No support
- Outlook: ❌ No support
- Yahoo: ❌ No support
**Answer:** No — only Apple Mail supports it. Use table-based layout.

#### "Can I use media queries in email?"
- Apple Mail: ✅ Full support
- Gmail web: ✅ Supported
- Gmail app: ⚠️ Varies by account type
- Outlook desktop: ❌ No support
- Yahoo: ⚠️ Partial support
**Answer:** Yes, for progressive enhancement. Don't rely on them for core layout.

#### "Can I use CSS variables in email?"
- Apple Mail: ✅ Full support
- All others: ❌ No support
**Answer:** No — only Apple Mail supports them. Use static values.

#### "Can I use background-image in email?"
- Apple Mail: ✅ Full support
- Gmail: ✅ Inline style only
- Outlook desktop: ❌ No support (use VML)
- Yahoo: ✅ Full support
**Answer:** Yes, with VML fallback for Outlook. Use inline style, not `<style>` block.

## Interpreting Partial Support

When Can I Email shows partial support (⚠️), check:
1. **Which version?** — Partial may mean "newer versions only"
2. **Which context?** — May work in `<style>` but not inline, or vice versa
3. **Which property value?** — Some values supported but not others
4. **Which rendering context?** — Web vs app may differ

## Using Can I Email Data in Answers

1. State the support level clearly per major client
2. Provide the fallback approach for unsupported clients
3. Note any "gotchas" for partial support
4. Include a code example showing the property with fallback
5. Cite "Source: Can I Email" or the specific knowledge base document