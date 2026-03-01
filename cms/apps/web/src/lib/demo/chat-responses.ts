import type { AgentMode } from "@/types/chat";

/**
 * Canned AI responses for demo mode, one per agent mode.
 * Simulated via progressive character streaming.
 */
export const DEMO_CHAT_RESPONSES: Record<AgentMode, string> = {
  chat: `I can help you with email development! Here are some things I can assist with:

**Rendering Issues**
- Dark mode compatibility across Outlook, Gmail, and Apple Mail
- MSO conditional comments for Outlook table layouts
- VML backgrounds and rounded corners for Outlook

**Best Practices**
- Always use \`role="presentation"\` on layout tables
- Include \`color-scheme: light dark\` meta tag for native dark mode support
- Keep total email size under 102KB to avoid Gmail clipping
- Use explicit width/height on images for proper Outlook rendering

**CSS Support**
- \`border-radius\` — works everywhere except Outlook desktop
- \`background-image\` — needs VML fallback for Outlook
- \`gap\` — not supported in most email clients, use padding instead

What specific area would you like help with?`,

  scaffolder: `Here's a Maizzle template skeleton based on your brief:

\`\`\`html
---
preheader: "Your preheader text here"
---

<extends src="src/layouts/main.html">
  <block name="template">
    <table class="w-full" cellpadding="0" cellspacing="0" role="presentation">
      <!-- Header -->
      <tr>
        <td class="p-24 bg-white">
          <a href="https://example.com">
            <img src="images/logo.png" alt="Logo" width="150">
          </a>
        </td>
      </tr>

      <!-- Hero Section -->
      <tr>
        <td class="p-48 bg-slate-800 text-center text-white">
          <h1 class="text-3xl font-bold m-0 mb-16">
            Your Headline Here
          </h1>
          <p class="text-lg m-0 mb-24 text-slate-300">
            Supporting copy that drives action.
          </p>
          <a href="https://example.com/cta"
             class="inline-block px-36 py-14 bg-red-600 text-white font-bold no-underline rounded">
            Call to Action
          </a>
        </td>
      </tr>

      <!-- Content Area -->
      <tr>
        <td class="p-32 bg-white">
          <h2 class="text-xl font-bold m-0 mb-12 text-slate-800">
            Section Title
          </h2>
          <p class="text-base m-0 text-slate-600 leading-relaxed">
            Your content here.
          </p>
        </td>
      </tr>

      <!-- Footer -->
      <tr>
        <td class="p-32 bg-slate-100 text-center text-xs text-slate-500">
          <p class="m-0 mb-12">&copy; 2026 Your Company</p>
          <a href="{{ unsubscribeUrl }}" class="text-blue-600 underline">
            Unsubscribe
          </a>
        </td>
      </tr>
    </table>
  </block>
</extends>
\`\`\`

This template uses Maizzle's Tailwind utility classes which compile to inline styles. The layout includes responsive breakpoints and dark mode support out of the box.`,

  dark_mode: `Here's how to add comprehensive dark mode support to your email:

**1. Meta tag** (required for native dark mode):
\`\`\`html
<meta name="color-scheme" content="light dark">
<meta name="supported-color-schemes" content="light dark">
\`\`\`

**2. CSS media query** for standard clients:
\`\`\`css
@media (prefers-color-scheme: dark) {
  .body-bg { background-color: #1a1a2e !important; }
  .content-bg { background-color: #2d2d44 !important; }
  .heading { color: #e0e0e0 !important; }
  .body-text { color: #cccccc !important; }
  .link { color: #8ecae6 !important; }
}
\`\`\`

**3. Outlook dark mode** (uses \`[data-ogsc]\` selectors):
\`\`\`css
[data-ogsc] .body-bg { background-color: #1a1a2e !important; }
[data-ogsc] .content-bg { background-color: #2d2d44 !important; }
[data-ogsc] .heading { color: #e0e0e0 !important; }
\`\`\`

**Key tips:**
- Always use \`!important\` — email clients need it to override inline styles
- Test with Apple Mail Dark, Outlook 365, and Samsung Mail Dark personas
- Use class-based selectors (not IDs or tag selectors)
- Background images need separate dark mode handling
- Logos with transparency may need a light background container in dark mode`,

  content: `Here are optimised subject lines for your spring sale campaign:

**Primary Options:**
1. "Spring Into Savings — Up to 40% Off Everything" *(urgency + value)*
2. "Fresh Styles, Unbeatable Prices — Spring Sale Now On" *(seasonal + value)*
3. "Your Spring Wardrobe Refresh Starts Here" *(aspirational)*

**Urgency Variants (for reminder/last-chance):**
4. "Ends This Weekend — Don't Miss 40% Off Spring" *(deadline)*
5. "FINAL HOURS: Spring Sale Ends Tonight" *(caps for urgency)*

**Preheader Suggestions:**
- "Shop new arrivals at their lowest prices of the season"
- "Free shipping on orders over £50. Ends Sunday."
- "Your favourites are selling fast — shop now before they're gone"

**CTA Copy Options:**
- Primary: "Shop the Sale" / "View All Deals"
- Urgency: "Shop Before Midnight" / "Grab Your Favourites"
- Subtle: "Explore Spring Styles" / "See What's New"

All options are under 50 characters for optimal mobile display and avoid common spam trigger words.`,

  outlook_fixer: `Here's how to fix common Outlook rendering issues in your email:

**1. MSO Conditional Comments** (Outlook-only code):
\`\`\`html
<!--[if mso]>
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0">
<tr><td>
<![endif]-->
  <!-- Your responsive content here -->
<!--[if mso]>
</td></tr></table>
<![endif]-->
\`\`\`

**2. VML Backgrounds** (background images in Outlook):
\`\`\`html
<!--[if gte mso 9]>
<v:rect xmlns:v="urn:schemas-microsoft-com:vml" fill="true" stroke="false" style="width:600px;height:300px;">
<v:fill type="frame" src="https://example.com/hero.jpg" />
<v:textbox inset="0,0,0,0">
<![endif]-->
  <div style="background-image:url('https://example.com/hero.jpg');">
    <!-- Content here -->
  </div>
<!--[if gte mso 9]></v:textbox></v:rect><![endif]-->
\`\`\`

**3. Common Fixes:**
- Add \`mso-table-lspace: 0; mso-table-rspace: 0;\` to all tables
- Use \`mso-line-height-rule: exactly\` for precise line heights
- Replace \`max-width\` with MSO conditional fixed-width tables
- Add VML namespace: \`xmlns:v="urn:schemas-microsoft-com:vml"\``,

  accessibility: `Here's an accessibility audit of your email template:

**Issues Found:**

1. **Missing \`lang\` attribute** — Add \`lang="en"\` to your \`<html>\` tag for screen readers
2. **Images without alt text** — 2 images found without \`alt\` attributes
3. **Low contrast text** — Body text (#999) on white (#fff) has only 2.8:1 ratio (needs 4.5:1)
4. **Missing table roles** — Layout tables need \`role="presentation"\` to prevent screen reader confusion

**Recommendations:**
- Add \`role="article"\` and \`aria-label\` to the main email wrapper
- Use semantic headings (h1 → h2 → h3) — don't skip levels
- Ensure link text is descriptive ("Shop Now" not "Click Here")
- Minimum touch target size: 44×44px for CTA buttons
- Add \`title\` attributes to links for additional context
- Test with VoiceOver (macOS) and NVDA (Windows)

**WCAG AA Compliance Score: 62/100** — needs improvement on contrast and alt text.`,

  personalisation: `Here's how to add dynamic personalisation to your email:

**Braze Liquid Tags:**
\`\`\`html
<!-- First name with fallback -->
Hi {{customer.first_name | default: "there"}},

<!-- Conditional content block -->
{% if customer.loyalty_tier == "gold" %}
  <p>As a Gold member, enjoy exclusive early access!</p>
{% else %}
  <p>Join our loyalty program for exclusive benefits.</p>
{% endif %}

<!-- Dynamic product recommendations -->
{% for product in customer.recommended_products | limit: 3 %}
  <tr><td>
    <img src="{{product.image_url}}" alt="{{product.name}}" width="200">
    <p>{{product.name}} — {{product.price}}</p>
  </td></tr>
{% endfor %}
\`\`\`

**SFMC AMPscript:**
\`\`\`
%%[SET @fname = AttributeValue("FirstName")]%%
Hello %%=IIF(NOT EMPTY(@fname), @fname, "there")=%%,
\`\`\`

**Best Practices:**
- Always include fallback values for empty fields
- Test with missing/null subscriber data
- Keep personalisation tokens outside of alt text for accessibility`,

  code_reviewer: `Here's a code review of your email template:

**Issues (3 found):**

1. **Redundant inline styles** (line 42, 58, 73)
   Multiple elements repeat \`font-family: Arial, sans-serif; font-size: 14px;\` — extract to a CSS class for maintainability.

2. **Missing width attribute on images** (line 35)
   \`<img src="hero.jpg">\` — Outlook requires explicit \`width\` and \`height\` attributes for correct rendering.

3. **Oversized file (108KB)** ⚠️
   Gmail clips emails over 102KB. Current template is 108KB after inlining.
   - Remove unused CSS rules (~4KB savings)
   - Compress image URLs (~2KB savings)
   - Minify HTML whitespace (~3KB savings)

**Optimisation Suggestions:**
- Replace hex colours with shorthand where possible (#ffffff → #fff)
- Remove empty \`style=""\` attributes (3 instances)
- Consolidate duplicate MSO conditional blocks
- Consider lazy-loading below-fold images

**Overall Score: 7.2/10** — solid structure, needs file size optimisation.`,

  knowledge: `Based on the knowledge base, here's what I found:

**Can I Email — CSS Support Summary:**

| Property | Gmail | Outlook | Apple Mail | Yahoo |
|----------|-------|---------|------------|-------|
| \`border-radius\` | ✅ | ❌ | ✅ | ✅ |
| \`background-image\` | ✅ | ⚠️ VML | ✅ | ✅ |
| \`flexbox\` | ❌ | ❌ | ✅ | ❌ |
| \`gap\` | ❌ | ❌ | ✅ | ❌ |
| \`max-width\` | ✅ | ❌ | ✅ | ✅ |
| \`position\` | ❌ | ❌ | ✅ | ❌ |
| \`@media\` | ✅ | ❌ | ✅ | ❌ |

**Key Insight:** Only ~30% of modern CSS properties work reliably across all major email clients. Stick to table-based layouts with inline styles for maximum compatibility.

**Related Knowledge Articles:**
- "Email Client CSS Support Matrix 2026"
- "Gmail Clipping Prevention Guide"
- "Outlook VML Fallback Patterns"

What specific CSS property or email client would you like to know more about?`,

  innovation: `Here are some cutting-edge email techniques to explore:

**1. AMP for Email (Interactive)**
Gmail supports AMP components for interactive emails:
\`\`\`html
<amp-carousel width="600" height="300" layout="responsive" type="slides">
  <amp-img src="slide1.jpg" width="600" height="300"></amp-img>
  <amp-img src="slide2.jpg" width="600" height="300"></amp-img>
</amp-carousel>
\`\`\`
*Support: Gmail only — always include HTML fallback.*

**2. CSS Animation in Email**
Subtle animations for Apple Mail and iOS:
\`\`\`css
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
.hero-text { animation: fadeIn 0.8s ease-in; }
\`\`\`
*Degrades gracefully — static in non-supporting clients.*

**3. Dark Mode Colour Detection**
Use \`light-dark()\` function (emerging support):
\`\`\`css
color: light-dark(#333333, #e0e0e0);
\`\`\`

**4. Kinetic Email (CSS-only interactivity)**
Checkbox hack for accordion/tab interfaces without JavaScript — works in Apple Mail, Gmail (web), and Yahoo.

**Feasibility Assessment:** AMP is production-ready for Gmail audiences. CSS animations are safe as progressive enhancement. Kinetic email is experimental but impressive for demos.`,
};
