---
version: "1.0.0"
---

<!-- L4 source: docs/SKILL_email-accessibility-wcag-aa.md section 3 -->
<!-- Last synced: 2026-03-13 -->

# Email Image Accessibility — Alt Text & Image-Off Strategy

Rules for every image type in HTML email. In email, images are blocked by
default in many corporate clients (Outlook, Gmail) — alt text is often the
**primary content**, not a fallback.

---

## Decision Tree

```
Is the image purely decorative (spacer, border, divider, tracking pixel)?
├── Yes → alt="" + role="presentation" + aria-hidden="true"
│
└── No → Is the image inside a link (<a>)?
    ├── Yes → Is there adjacent text linking to the same URL?
    │   ├── Yes → Wrap both in single <a>, use alt="" on image
    │   └── No → alt describes the link destination/action
    │
    └── No → Is it a complex image (chart, diagram, infographic)?
        ├── Yes → Brief alt (key data point) + detailed text nearby
        └── No → Descriptive alt text (max 125 characters)
```

---

## Meaningful Images — WCAG 1.1.1 (Level A)

Every `<img>` MUST have an `alt` attribute — no exceptions.

### By Image Type

| Type | Alt Text Strategy | Example |
|------|------------------|---------|
| Product | Name + key detail + price | `alt="Blue cotton t-shirt, front view — $29.99"` |
| Hero/banner | Scene + overlay text content | `alt="Summer Sale — Up to 50% off all styles"` |
| Chart/graph | Key data point or trend | `alt="Q3 revenue up 15% — details below"` |
| Icon | Action or meaning, not appearance | `alt="Email us"` not `alt="envelope icon"` |
| CTA button | Action verb + object | `alt="Shop now"` not `alt="button"` |
| Logo | Company name | `alt="Acme Corp"` |
| Person/team | Name + context if relevant | `alt="Sarah Chen, CEO, at annual conference"` |

### Alt Text Rules

1. **Max 125 characters** — screen readers may truncate longer text
2. **Never start with "Image of" or "Photo of"** — screen readers already announce "image"
3. **Describe purpose, not appearance** — convey what the image communicates in context
4. **Functional images describe the action** — `alt="Next page"` not `alt="Arrow icon"`

---

## Decorative Images

All decorative images need the triple treatment for cross-client safety:

```html
<img src="spacer.gif" alt="" role="presentation" aria-hidden="true"
     width="1" height="20" style="display:block;">
```

### What Counts as Decorative

- Spacer GIFs (still common in email templates)
- Decorative divider/border images
- Background pattern images used via `<img>` tag
- Tracking pixels (1x1 open tracking)
- Icons that duplicate adjacent text (e.g., phone icon next to "Call us: 555-0123")

---

## Image-Off Rendering (Email-Specific)

Many corporate Outlook installations and Gmail block images by default. Email
must be fully understandable with images off.

### Styled Alt Text

Email-specific technique — style the `<img>` tag so alt text renders on-brand:

```html
<img src="hero.jpg" alt="Summer Sale — 50% Off"
     width="600" height="200"
     style="display:block; font-family:Arial,sans-serif;
            font-size:24px; font-weight:bold; color:#1a1a1a;">
```

When images are blocked, the alt text renders with these styles.

### Image-Off Design Principles

- Critical information MUST be in live text (CTAs, pricing, deadlines, key messages)
- CTA buttons: use bulletproof HTML/CSS buttons, not image buttons
- Design "image-off first" — test every template with images disabled
- Hero text baked into images is invisible without alt text

---

## Linked Images

### Adjacent Image + Text Link (Same URL)

The most common email a11y failure — causes double announcement:

```html
<!-- BAD: Two separate links, screen reader announces twice -->
<a href="/product"><img src="shoe.jpg" alt="Running Shoe"></a>
<a href="/product">Running Shoe — $89</a>

<!-- GOOD: Single link wrapper, image is decorative -->
<a href="/product">
  <img src="shoe.jpg" alt="" style="display:block;">
  Running Shoe — $89
</a>
```

### Logo Linking to Website

```html
<a href="https://example.com">
  <img src="logo.png" alt="Acme Corp — visit website" style="display:block;">
</a>
```

---

## Animated GIFs

- Must not flash more than 3 times per second (WCAG 2.3.1)
- First frame must be meaningful — Outlook desktop shows only the first frame
- Never convey critical information solely through animation
- GIF file size affects load time; blank spaces while loading hurt comprehension

---

## SVG in Email

Limited email client SVG support — always provide `<img>` fallback:

```html
<svg role="img" aria-label="Descriptive label">
  <title>Descriptive label</title>
  <!-- SVG content -->
</svg>
<!-- Fallback for most email clients -->
<img src="fallback.png" alt="Descriptive label" style="display:block;">
```

Decorative SVGs: `aria-hidden="true"` + no title/aria-label.

---

## Background Images (VML)

- Never convey critical information via CSS `background-image` alone
- Outlook requires VML (`<v:rect>`) for background images — without it, no background renders
- Always provide readable text content on top of background images
- The `<td>` text is the accessible content; the VML fill is decorative