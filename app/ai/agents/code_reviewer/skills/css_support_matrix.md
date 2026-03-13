<!-- L4 source: docs/SKILL_html-email-css-dom-reference.md -->
# CSS Support Matrix for Email Clients

## Layout Properties

| Property | Gmail | Outlook | Apple Mail | Yahoo | Samsung |
|----------|-------|---------|------------|-------|---------|
| display:block | ✅ | ✅ | ✅ | ✅ | ✅ |
| display:inline-block | ✅ | ✅ | ✅ | ✅ | ✅ |
| display:none | ✅ | ✅ | ✅ | ✅ | ✅ |
| display:flex | ❌ | ❌ | ✅ | ❌ | ❌ |
| display:grid | ❌ | ❌ | ✅ | ❌ | ❌ |
| float | ✅ | ⚠️ | ✅ | ✅ | ✅ |
| position | ❌ | ❌ | ✅ | ❌ | ❌ |
| overflow | ⚠️ | ❌ | ✅ | ⚠️ | ⚠️ |

## Box Model

| Property | Gmail | Outlook | Apple Mail | Yahoo | Samsung |
|----------|-------|---------|------------|-------|---------|
| margin | ✅ | ⚠️ | ✅ | ✅ | ✅ |
| padding | ✅ | ⚠️ td only | ✅ | ✅ | ✅ |
| width | ✅ | ✅ | ✅ | ✅ | ✅ |
| max-width | ✅ | ❌ | ✅ | ✅ | ✅ |
| min-width | ✅ | ❌ | ✅ | ✅ | ✅ |
| height | ✅ | ✅ | ✅ | ✅ | ✅ |
| box-sizing | ✅ | ❌ | ✅ | ✅ | ✅ |

## Typography

| Property | Gmail | Outlook | Apple Mail | Yahoo | Samsung |
|----------|-------|---------|------------|-------|---------|
| font-family | ✅ | ✅ | ✅ | ✅ | ✅ |
| font-size | ✅ | ✅ | ✅ | ✅ | ✅ |
| font-weight | ✅ | ✅ | ✅ | ✅ | ✅ |
| font-style | ✅ | ✅ | ✅ | ✅ | ✅ |
| line-height | ✅ | ⚠️ | ✅ | ✅ | ✅ |
| text-align | ✅ | ✅ | ✅ | ✅ | ✅ |
| text-decoration | ✅ | ✅ | ✅ | ✅ | ✅ |
| text-transform | ✅ | ✅ | ✅ | ✅ | ✅ |
| letter-spacing | ✅ | ✅ | ✅ | ✅ | ✅ |
| word-spacing | ✅ | ⚠️ | ✅ | ✅ | ✅ |
| @font-face | ❌ | ❌ | ✅ | ❌ | ❌ |

## Color & Background

| Property | Gmail | Outlook | Apple Mail | Yahoo | Samsung |
|----------|-------|---------|------------|-------|---------|
| color | ✅ | ✅ | ✅ | ✅ | ✅ |
| background-color | ✅ | ✅ | ✅ | ✅ | ✅ |
| background-image | ✅ | ❌ | ✅ | ✅ | ✅ |
| background-size | ✅ | ❌ | ✅ | ✅ | ✅ |
| background-position | ✅ | ❌ | ✅ | ✅ | ✅ |
| background shorthand | ⚠️ | ❌ | ✅ | ⚠️ | ⚠️ |
| opacity | ❌ | ❌ | ✅ | ❌ | ❌ |
| rgba() | ✅ | ❌ | ✅ | ✅ | ✅ |

## Border & Decoration

| Property | Gmail | Outlook | Apple Mail | Yahoo | Samsung |
|----------|-------|---------|------------|-------|---------|
| border | ✅ | ✅ | ✅ | ✅ | ✅ |
| border-radius | ✅ | ❌ | ✅ | ✅ | ✅ |
| border-collapse | ✅ | ✅ | ✅ | ✅ | ✅ |
| box-shadow | ❌ | ❌ | ✅ | ❌ | ❌ |
| outline | ✅ | ❌ | ✅ | ✅ | ✅ |

## Advanced

| Property | Gmail | Outlook | Apple Mail | Yahoo | Samsung |
|----------|-------|---------|------------|-------|---------|
| @media queries | ⚠️ | ❌ | ✅ | ⚠️ | ⚠️ |
| :hover | ❌ | ❌ | ✅ | ❌ | ❌ |
| animation | ❌ | ❌ | ✅ | ❌ | ❌ |
| transition | ❌ | ❌ | ✅ | ❌ | ❌ |
| transform | ❌ | ❌ | ✅ | ❌ | ❌ |
| CSS variables | ❌ | ❌ | ✅ | ❌ | ❌ |
| calc() | ❌ | ❌ | ✅ | ❌ | ❌ |

## Legend
- ✅ Full support
- ⚠️ Partial support (with caveats)
- ❌ Not supported (use fallback or avoid)
