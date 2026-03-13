<!-- L4 source: docs/SKILL_html-email-components.md sections 16, 9 -->
<!-- Last synced: 2026-03-13 -->

# AMP for Email Reference

## What is AMP for Email?

AMP (Accelerated Mobile Pages) for Email enables dynamic, interactive content
within emails — forms, real-time data, carousels, and more — without JavaScript.

## Client Support

| Client | AMP Support | Notes |
|--------|------------|-------|
| Gmail (Web) | ✅ | Requires sender registration |
| Gmail (Android) | ✅ | Requires sender registration |
| Gmail (iOS) | ✅ | Requires sender registration |
| Outlook.com | ✅ | Limited to Microsoft accounts |
| Yahoo Mail | ✅ | Requires sender registration |
| Apple Mail | ❌ | No support |
| Outlook desktop | ❌ | No support |

**Coverage:** ~60% of email opens (Gmail + Outlook.com + Yahoo)

## AMP Email Boilerplate

```html
<!doctype html>
<html ⚡4email>
<head>
  <meta charset="utf-8">
  <script async src="https://cdn.ampproject.org/v0.js"></script>
  <style amp4email-boilerplate>body{visibility:hidden}</style>
  <style amp-custom>
    /* Custom styles here */
  </style>
</head>
<body>
  <!-- AMP content here -->
</body>
</html>
```

## Complete AMP Component List

| Component | Purpose | Script Required |
|-----------|---------|-----------------|
| `amp-img` | Image rendering within AMP emails | Built-in |
| `amp-carousel` | Interactive image carousels / product showcases | `amp-carousel-0.1.js` |
| `amp-accordion` | Expandable / collapsible content sections | `amp-accordion-0.1.js` |
| `amp-form` | In-email form submission (surveys, RSVPs, reviews, one-click actions) | `amp-form-0.1.js` |
| `amp-bind` | Dynamic state management (content changes on user interaction) | `amp-bind-0.1.js` |
| `amp-list` | Dynamically fetches and renders live data from API at open time | `amp-list-0.1.js` |
| `amp-mustache` | Templating for dynamic content rendering | `amp-mustache-0.2.js` |
| `amp-anim` | Animated GIF handling | `amp-anim-0.1.js` |
| `amp-selector` | Interactive selection UI (product variants, colors, sizes) | `amp-selector-0.1.js` |
| `amp-sidebar` | Slide-out navigation panels | `amp-sidebar-0.1.js` |
| `amp-fit-text` | Auto-sizes text to fit container | `amp-fit-text-0.1.js` |
| `amp-timeago` | Relative timestamps that update | `amp-timeago-0.1.js` |
| `amp-layout` | Responsive layout containers | Built-in |

## Key Component Examples

### amp-carousel (Image Carousel)
```html
<script async custom-element="amp-carousel" src="https://cdn.ampproject.org/v0/amp-carousel-0.1.js"></script>

<amp-carousel width="600" height="300" type="slides" layout="responsive" autoplay delay="3000">
  <amp-img src="https://placehold.co/600x300" width="600" height="300" alt="Slide 1"></amp-img>
  <amp-img src="https://placehold.co/600x300" width="600" height="300" alt="Slide 2"></amp-img>
</amp-carousel>
```

### amp-accordion
```html
<script async custom-element="amp-accordion" src="https://cdn.ampproject.org/v0/amp-accordion-0.1.js"></script>

<amp-accordion>
  <section expanded>
    <h3>Section 1</h3>
    <div><p>Content for section 1</p></div>
  </section>
  <section>
    <h3>Section 2</h3>
    <div><p>Content for section 2</p></div>
  </section>
</amp-accordion>
```

### amp-form (Interactive Forms)
```html
<script async custom-element="amp-form" src="https://cdn.ampproject.org/v0/amp-form-0.1.js"></script>

<form method="post" action-xhr="https://api.example.com/submit">
  <input type="text" name="feedback" placeholder="Your feedback" required>
  <button type="submit">Submit</button>
  <div submit-success><p>Thanks for your feedback!</p></div>
  <div submit-error><p>Something went wrong.</p></div>
</form>
```

### amp-list (Real-Time Data)
```html
<script async custom-element="amp-list" src="https://cdn.ampproject.org/v0/amp-list-0.1.js"></script>
<script async custom-template="amp-mustache" src="https://cdn.ampproject.org/v0/amp-mustache-0.2.js"></script>

<amp-list width="600" height="400" src="https://api.example.com/products"
  layout="responsive">
  <template type="amp-mustache">
    <div>
      <h3>{{name}}</h3>
      <p>{{price}}</p>
    </div>
  </template>
</amp-list>
```

## AMP Email Use Cases

- **Live updating content** — cart totals, order statuses, flight info, inventory levels
- **In-email shopping** — browse products, select variants, add to cart without leaving inbox
- **RSVP and event management** — accept/decline/tentative directly in email
- **Comment and reply** — respond to threads directly from inbox
- **Interactive surveys and NPS scoring** — multi-question forms with real-time submission
- **Appointment booking** — date/time picker within email
- **Onboarding wizards** — multi-step progressive disclosure flows
- **Multi-step forms** — complex data collection with validation between steps

## AMP Form Accessibility

When building AMP forms, apply these accessibility considerations:
- All `<input>` elements must have associated `<label>` elements (use `for`/`id` pairing)
- Use `aria-required="true"` on mandatory fields alongside HTML `required` attribute
- Provide visible error messages in `submit-error` blocks (not just color changes)
- Ensure `submit-success` and `submit-error` feedback is screen-reader-announced
- Use `role="alert"` on dynamic validation messages
- Maintain minimum 44x44px tap targets on all form controls
- Ensure sufficient color contrast on form labels and placeholder text

## CORS Requirements

AMP emails that fetch data require CORS headers:
```
Access-Control-Allow-Origin: https://mail.google.com (or *.mail.google.com)
AMP-Email-Allow-Sender: sender@example.com
```

## Limitations

1. **Sender registration required** — Must register with each email provider
2. **CORS required** — Dynamic endpoints need proper CORS headers
3. **No custom JavaScript** — Only AMP components allowed
4. **Size limit** — AMP HTML must be under 200KB
5. **Expiration** — AMP content may expire after 30 days (falls back to HTML)
6. **Must include HTML fallback** — AMP emails require a standard HTML MIME part

## Multi-MIME Structure (CRITICAL)

AMP emails MUST include multiple MIME parts — the HTML fallback is not optional:
1. `text/plain` — Plain text version
2. `text/x-amp-html` — AMP version (shown in supporting clients)
3. `text/html` — Standard HTML fallback (shown in non-AMP clients)

Supported AMP clients: Gmail, Yahoo Mail, Mail.ru, FairEmail. All other clients
receive the `text/html` fallback, so it must be a fully functional email.
