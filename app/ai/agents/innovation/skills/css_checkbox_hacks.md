<!-- L4 source: docs/SKILL_html-email-components.md section 20 -->
<!-- Last synced: 2026-03-13 -->

# CSS Checkbox Hacks for Interactive Email

## How It Works

The checkbox hack uses hidden `<input type="checkbox">` elements with `<label>` triggers
and the `:checked` CSS pseudo-class combined with sibling selectors to create interactivity.

```
[checkbox] + [label] + [content]
When checkbox is checked: input:checked ~ .content { display: block }
```

## Client Support

| Client | Checkbox Hack | Notes |
|--------|--------------|-------|
| Apple Mail | ✅ | Full support |
| Gmail (Web) | ❌ | Strips `<input>` elements |
| Gmail (App) | ❌ | Strips `<input>` elements |
| Outlook desktop | ❌ | No `:checked` support |
| Outlook.com | ❌ | Strips `<input>` elements |
| Yahoo Mail | ✅ | Works in web client |
| Samsung Mail | ⚠️ | Varies by version |
| Thunderbird | ✅ | Full support |

**Coverage:** ~25-35% of email opens (Apple Mail + Yahoo + Thunderbird)

## Pattern 1: Tabbed Content (Radio Button Navigation)

Uses radio inputs for mutually exclusive states — only one tab visible at a time.

```html
<style>
  .tab-content { display: none; }
  #tab1:checked ~ .tab-content.tab1 { display: block; }
  #tab2:checked ~ .tab-content.tab2 { display: block; }
  #tab3:checked ~ .tab-content.tab3 { display: block; }
  .tab-label { display: inline-block; padding: 10px 20px; cursor: pointer; background: #f0f0f0; }
  input:checked + .tab-label { background: #007bff; color: #fff; }
  input[type="radio"] { display: none !important; }
</style>

<input type="radio" id="tab1" name="tabs" checked style="display:none !important;">
<label class="tab-label" for="tab1">Tab 1</label>

<input type="radio" id="tab2" name="tabs" style="display:none !important;">
<label class="tab-label" for="tab2">Tab 2</label>

<input type="radio" id="tab3" name="tabs" style="display:none !important;">
<label class="tab-label" for="tab3">Tab 3</label>

<div class="tab-content tab1">
  <p>Content for Tab 1</p>
</div>
<div class="tab-content tab2">
  <p>Content for Tab 2</p>
</div>
<div class="tab-content tab3">
  <p>Content for Tab 3</p>
</div>
```

**Fallback:** Show all content stacked (all tabs visible).

## Pattern 2: Accordion

```html
<style>
  .accordion-content { max-height: 0; overflow: hidden; transition: max-height 0.3s; }
  .accordion-toggle:checked + .accordion-label + .accordion-content { max-height: 500px; }
  .accordion-toggle { display: none !important; }
  .accordion-label { display: block; padding: 15px; background: #f0f0f0; cursor: pointer; font-weight: bold; }
  .accordion-label::after { content: "+"; float: right; }
  .accordion-toggle:checked + .accordion-label::after { content: "−"; }
</style>

<input type="checkbox" class="accordion-toggle" id="acc1" style="display:none !important;">
<label class="accordion-label" for="acc1">Section 1</label>
<div class="accordion-content">
  <p style="padding: 15px;">Section 1 content here.</p>
</div>

<input type="checkbox" class="accordion-toggle" id="acc2" style="display:none !important;">
<label class="accordion-label" for="acc2">Section 2</label>
<div class="accordion-content">
  <p style="padding: 15px;">Section 2 content here.</p>
</div>
```

**Fallback:** Show all sections expanded.

## Pattern 3: Image Carousel (CSS-Only Sliding Gallery)

Uses radio inputs for mutually exclusive slide visibility via checkbox/radio hack.

```html
<style>
  .carousel-item { display: none; }
  #slide1:checked ~ .carousel .slide1 { display: block; }
  #slide2:checked ~ .carousel .slide2 { display: block; }
  #slide3:checked ~ .carousel .slide3 { display: block; }
  .carousel-nav { display: inline-block; }
  .carousel-nav label { display: inline-block; width: 12px; height: 12px;
    border-radius: 50%; background: #ccc; margin: 0 4px; cursor: pointer; }
  input:checked + label { background: #007bff; }
  input[type="radio"].carousel-input { display: none !important; }
</style>

<input type="radio" class="carousel-input" id="slide1" name="carousel" checked style="display:none !important;">
<input type="radio" class="carousel-input" id="slide2" name="carousel" style="display:none !important;">
<input type="radio" class="carousel-input" id="slide3" name="carousel" style="display:none !important;">

<div class="carousel">
  <div class="carousel-item slide1">
    <img src="https://placehold.co/600x300" alt="Slide 1" width="600" height="300" style="display:block; border:0;">
  </div>
  <div class="carousel-item slide2">
    <img src="https://placehold.co/600x300" alt="Slide 2" width="600" height="300" style="display:block; border:0;">
  </div>
  <div class="carousel-item slide3">
    <img src="https://placehold.co/600x300" alt="Slide 3" width="600" height="300" style="display:block; border:0;">
  </div>
</div>

<div class="carousel-nav">
  <label for="slide1"></label>
  <label for="slide2"></label>
  <label for="slide3"></label>
</div>
```

**Fallback:** Show first slide only as static image.

## Pattern 4: CSS-Only Hamburger Menu

```html
<style>
  .menu-toggle { display: none !important; }
  .menu-content { max-height: 0; overflow: hidden; transition: max-height 0.3s; }
  .menu-toggle:checked ~ .menu-content { max-height: 400px; }
  .menu-label { display: inline-block; padding: 10px; cursor: pointer; font-size: 24px; }
</style>

<input type="checkbox" class="menu-toggle" id="menu" style="display:none !important;">
<label class="menu-label" for="menu">&#9776;</label>
<div class="menu-content">
  <a href="https://example.com/1" style="display:block; padding:10px;">Link 1</a>
  <a href="https://example.com/2" style="display:block; padding:10px;">Link 2</a>
  <a href="https://example.com/3" style="display:block; padding:10px;">Link 3</a>
</div>
```

**Fallback:** Show all links stacked (no hamburger toggle).

## Pattern 5: Star Rating Selector

```css
.star-input { display: none !important; }
.star-label { cursor: pointer; font-size: 24px; color: #ccc; }
#star5:checked ~ .stars .star-label:nth-child(-n+5),
#star4:checked ~ .stars .star-label:nth-child(-n+4),
#star3:checked ~ .stars .star-label:nth-child(-n+3) { color: #ffc107; }
```

**Fallback:** Static star display or link to external survey.

## Advanced Interactive Techniques

### Live Countdown Timers
Server-side generated animated GIF with real-time countdown calculated at email open. Not CSS-based — the server renders a new frame sequence on each HTTP request. Degrades to static "offer expires" text.

### Gamification Elements
Scratch cards, spin-to-win wheels, and reveal mechanics built via checkbox hack — user clicks/taps to toggle hidden content states. Must degrade to a direct CTA link in unsupported clients.

### CSS-Only Shopping Cart Interactions
Visual add/remove states using checkbox toggles — purely cosmetic state changes in email. Actual cart operations require link to web checkout. Degrade to product listing with "Shop Now" links.

## Fallback Strategy (CRITICAL)

**All interactive elements MUST degrade gracefully to static content.** Wrap interactive and static versions separately:

```html
<!-- Interactive version (Apple Mail, Yahoo) -->
<div class="interactive-content">
  <!-- checkbox hack code -->
</div>

<!-- Static fallback (Gmail, Outlook) -->
<div class="static-fallback">
  <!-- All content visible, no interactivity -->
</div>
```

```css
/* Default: show static, hide interactive */
.interactive-content { display: none; }
.static-fallback { display: block; }

/* In supporting clients: show interactive, hide static */
@media screen and (-webkit-min-device-pixel-ratio: 0) {
  .interactive-content { display: block; }
  .static-fallback { display: none; }
}
```

Note: This detection isn't perfect. Test thoroughly.
