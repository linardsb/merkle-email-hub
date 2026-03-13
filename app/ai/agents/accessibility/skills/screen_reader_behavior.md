<!-- L4 source: docs/SKILL_email-accessibility-wcag-aa.md section 12 -->
<!-- Last synced: 2026-03-13 -->

# Screen Reader Behavior in Email

How screen readers interact with email HTML — hidden content techniques, ARIA
attributes, announcement patterns, and content patterns that need special
treatment. Covers VoiceOver, NVDA, JAWS, and TalkBack across major clients.

---

## Screen Reader + Email Client Matrix

| Screen Reader | Platform | Email Client | Support Level |
|--------------|----------|-------------|---------------|
| VoiceOver | macOS | Apple Mail | Best — reads `role="article"`, full ARIA |
| VoiceOver | iOS | Mail app | Good — semantic markup respected |
| NVDA | Windows | Outlook desktop | Good — respects `role="presentation"` |
| JAWS | Windows | Outlook desktop | Good — similar to NVDA |
| NVDA | Windows | Outlook.com | Good — web rendering |
| TalkBack | Android | Gmail app | Limited — basic structure reading |

---

## Hidden Content Techniques

Each technique has different screen reader behavior — choose carefully:

| Technique | Visual | Screen Reader | Use Case |
|-----------|--------|---------------|----------|
| `display: none` | Hidden | Skipped | Content for one breakpoint only (desktop/mobile) |
| `visibility: hidden` | Hidden | Skipped | Same as `display: none` |
| `aria-hidden="true"` | **Visible** | Skipped | Decorative elements that sighted users see |
| `mso-hide: all` | Hidden (Outlook only) | **Still read** | Outlook visual hide — NOT an a11y tool |
| `max-height:0; overflow:hidden` | Hidden | **Read** | Preheader text (want SR to read it) |
| SR-only class (below) | Hidden | **Read** | Extra context for screen readers only |

### Visually Hidden (Screen Reader Only)

Email-safe method that works across clients:

```css
position: absolute;
width: 1px;
height: 1px;
overflow: hidden;
clip: rect(0,0,0,0);
white-space: nowrap;
```

### Preview Text Padding

The `&zwnj;&nbsp;` padding after preheader text MUST be hidden from screen readers:

```html
<span style="max-height:0; overflow:hidden; mso-hide:all;">
  Preheader text here.
</span>
<span aria-hidden="true" style="max-height:0; overflow:hidden; mso-hide:all;">
  &zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;<!-- repeated to push preview -->
</span>
```

---

## ARIA Attributes in Email

### Essential ARIA (Use Always)

| Attribute | Where | Why |
|-----------|-------|-----|
| `role="presentation"` | Every layout table | **#1 email a11y rule** — prevents SR from announcing grid dimensions |
| `role="article"` | Main email wrapper `<div>` or `<td>` | Identifies email body vs client UI |
| `aria-roledescription="email"` | Same wrapper as `role="article"` | Announces "email" instead of "article" |
| `aria-hidden="true"` | Decorative elements, spacers, tracking pixels, preview padding | Prevents noise announcements |

### Structural ARIA

| Attribute | Where | Why |
|-----------|-------|-----|
| `role="img"` | SVG, VML shapes acting as images | Announces as image |
| `role="separator"` | Decorative `<hr>` or divider `<td>` | Semantic separation |
| `role="list"` + `role="listitem"` | Table-faked lists (Outlook compatibility) | Maintains list semantics |
| `role="heading"` + `aria-level` | Non-heading elements acting as headings | Rare — prefer real `<h1>`-`<h6>` |

### Labeling ARIA

| Attribute | Where | Caveat |
|-----------|-------|--------|
| `aria-label` | Elements without visible text | **Gmail strips this** — don't rely on it solely |
| `aria-labelledby` | References another element's text | **Gmail strips this** |
| `aria-describedby` | Additional description | Primarily useful in AMP forms |
| `aria-live="polite"` | Dynamic update regions | AMP email form feedback |

**Critical note:** Gmail, Yahoo, and some clients strip many ARIA attributes.
Content must always be understandable WITHOUT ARIA as a baseline.

---

## Announcement Patterns — What Gets Read Aloud

### Elements That Cause Unwanted Announcements

| Element | SR Announces | Fix |
|---------|-------------|-----|
| `&nbsp;` spacer cells | "space" | `aria-hidden="true"` on cell |
| `&zwnj;` characters | "zero-width joiner" | `aria-hidden="true"` on container |
| `\|` pipe separators | "vertical bar" | `aria-hidden="true"` |
| `•` bullet separators | "bullet" | `aria-hidden="true"` |
| Decorative dashes/dots | Character name | `aria-hidden="true"` + visually hidden text if meaningful |
| Emoji | Varies wildly by client | Provide text alternative or `aria-label` |
| Unicode symbols | Character name | `aria-hidden="true"` + adjacent hidden text |

### Table-Faked List Bullets

```html
<table role="list">
  <tr role="listitem">
    <td aria-hidden="true" style="width:20px;">•</td>
    <td>List item content</td>
  </tr>
</table>
```

---

## Content Patterns Needing Special Treatment

These common email patterns are not conveyed correctly by screen readers
without explicit text alternatives:

| Pattern | Problem | Fix |
|---------|---------|-----|
| Strikethrough pricing (`<del>$50</del> $30`) | SR may not convey strikethrough | Add "Was $50, now $30" text |
| Discount badges | Image-only badge invisible | Include "50% off" as text |
| Star ratings (★★★★☆) | SR announces unicode chars | Add "Rated 4 out of 5 stars" text |
| Progress/status bars | Image-only bar invisible | Include text description |
| "New"/"Sale" badges | Image-only badges invisible | Use real text or meaningful `alt` |
| Countdown urgency | Animation-only invisible | Include live text version |
| Order status steps | Colored indicator image only | Text label per status step |

---

## MSO Conditional Content & Screen Readers

VoiceOver (Apple Mail) ignores MSO conditional content. NVDA/JAWS (Outlook)
reads MSO content and ignores non-MSO fallbacks.

**Both branches need proper accessibility:**

```html
<!--[if mso]>
<v:roundrect ...>
  <center style="...">Shop Now</center>
</v:roundrect>
<![endif]-->
<!--[if !mso]><!-->
<a href="..." style="...">Shop Now</a>
<!--<![endif]-->
```

### VML Accessibility

- Text inside `<v:textbox>` IS read by NVDA/JAWS in Outlook
- VML shapes themselves are NOT announced
- Alt text on VML elements is NOT reliably read
- **Always** ensure VML content has equivalent text in `<v:textbox>` or `<center>`

---

## Reading Order

Screen readers follow DOM order, not visual order.

### Multi-Column Layouts

- Source order: left column content, then right column content
- On mobile (stacked): becomes top-to-bottom following source order
- Ensure reading sequence makes sense in both layouts
- Two-column: text should not depend on seeing the adjacent image first

### Key Principle

There is no CSS grid/flexbox `order` property in email — source order is the
ONLY reading order. Get it right in the markup.
