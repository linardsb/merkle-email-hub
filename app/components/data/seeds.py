"""Seed data for pre-tested email components.

Each component includes dark mode CSS (@media prefers-color-scheme),
Outlook dark mode selectors ([data-ogsc]/[data-ogsb]),
and MSO conditional comments where applicable.
"""

_COMPAT_FULL: dict[str, str] = {
    "gmail": "full",
    "outlook_365": "full",
    "outlook_2019": "full",
    "apple_mail": "full",
    "ios_mail": "full",
    "yahoo": "full",
    "samsung_mail": "full",
    "outlook_com": "full",
}

_COMPAT_PARTIAL_SAMSUNG: dict[str, str] = {
    **_COMPAT_FULL,
    "samsung_mail": "partial",
}

COMPONENT_SEEDS: list[dict[str, object]] = [
    # ── 1. Email Header ──
    {
        "name": "Email Header",
        "slug": "email-header",
        "description": "Logo with optional navigation links. Full-width container with centered content.",
        "category": "structure",
        "html_source": """\
<style>
  @media (prefers-color-scheme: dark) {
    .header-bg { background-color: #1a1a2e !important; }
    .header-link { color: #8ecae6 !important; }
  }
  [data-ogsc] .header-bg { background-color: #1a1a2e !important; }
  [data-ogsc] .header-link { color: #8ecae6 !important; }
</style>
<!--[if mso]>
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0" border="0"><tr><td>
<![endif]-->
<table role="presentation" class="header-bg" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #ffffff;">
  <tr>
    <td style="padding: 20px 24px;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td style="width: 150px;">
            <img src="https://via.placeholder.com/150x40" alt="Company Logo" width="150" height="40" style="display: block; border: 0;" />
          </td>
          <td style="text-align: right; vertical-align: middle;">
            <a href="https://example.com" class="header-link" style="color: #333333; text-decoration: none; font-family: Arial, sans-serif; font-size: 14px; padding: 0 8px;">Home</a>
            <a href="https://example.com/products" class="header-link" style="color: #333333; text-decoration: none; font-family: Arial, sans-serif; font-size: 14px; padding: 0 8px;">Products</a>
            <a href="https://example.com/contact" class="header-link" style="color: #333333; text-decoration: none; font-family: Arial, sans-serif; font-size: 14px; padding: 0 8px;">Contact</a>
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>
<!--[if mso]>
</td></tr></table>
<![endif]-->""",
        "css_source": None,
        "compatibility": _COMPAT_FULL,
    },
    # ── 2. Email Footer ──
    {
        "name": "Email Footer",
        "slug": "email-footer",
        "description": "Unsubscribe link, company address, and legal text. GDPR-compliant footer.",
        "category": "structure",
        "html_source": """\
<style>
  @media (prefers-color-scheme: dark) {
    .footer-bg { background-color: #1a1a2e !important; }
    .footer-text { color: #b0b0b0 !important; }
    .footer-link { color: #8ecae6 !important; }
  }
  [data-ogsc] .footer-bg { background-color: #1a1a2e !important; }
  [data-ogsc] .footer-text { color: #b0b0b0 !important; }
  [data-ogsc] .footer-link { color: #8ecae6 !important; }
</style>
<!--[if mso]>
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0" border="0"><tr><td>
<![endif]-->
<table role="presentation" class="footer-bg" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #f5f5f5;">
  <tr>
    <td style="padding: 32px 24px; text-align: center;">
      <p class="footer-text" style="margin: 0 0 12px; font-family: Arial, sans-serif; font-size: 12px; color: #666666; line-height: 1.5;">
        &copy; 2026 Company Name. All rights reserved.
      </p>
      <p class="footer-text" style="margin: 0 0 12px; font-family: Arial, sans-serif; font-size: 12px; color: #666666; line-height: 1.5;">
        123 Business Street, London, EC1A 1BB
      </p>
      <p style="margin: 0; font-family: Arial, sans-serif; font-size: 12px;">
        <a href="{{unsubscribeUrl}}" class="footer-link" style="color: #0066cc; text-decoration: underline;">Unsubscribe</a>
        &nbsp;|&nbsp;
        <a href="{{preferencesUrl}}" class="footer-link" style="color: #0066cc; text-decoration: underline;">Manage Preferences</a>
        &nbsp;|&nbsp;
        <a href="https://example.com/privacy" class="footer-link" style="color: #0066cc; text-decoration: underline;">Privacy Policy</a>
      </p>
    </td>
  </tr>
</table>
<!--[if mso]>
</td></tr></table>
<![endif]-->""",
        "css_source": None,
        "compatibility": _COMPAT_FULL,
    },
    # ── 3. CTA Button ──
    {
        "name": "CTA Button",
        "slug": "cta-button",
        "description": "Centered call-to-action button with VML fallback for Outlook.",
        "category": "action",
        "html_source": """\
<style>
  @media (prefers-color-scheme: dark) {
    .cta-btn { background-color: #4895ef !important; }
    .cta-btn a { color: #ffffff !important; }
  }
  [data-ogsc] .cta-btn { background-color: #4895ef !important; }
</style>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
  <tr>
    <td style="padding: 24px 0; text-align: center;">
      <!--[if mso]>
      <v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" xmlns:w="urn:schemas-microsoft-com:office:word" href="https://example.com/cta" style="height:48px;v-text-anchor:middle;width:220px;" arcsize="10%" strokecolor="#0066cc" fillcolor="#0066cc">
        <w:anchorlock/>
        <center style="color:#ffffff;font-family:Arial,sans-serif;font-size:16px;font-weight:bold;">Shop Now</center>
      </v:roundrect>
      <![endif]-->
      <!--[if !mso]><!-->
      <table role="presentation" class="cta-btn" cellpadding="0" cellspacing="0" border="0" align="center" style="background-color: #0066cc; border-radius: 4px;">
        <tr>
          <td style="padding: 12px 32px;">
            <a href="https://example.com/cta" style="color: #ffffff; text-decoration: none; font-family: Arial, sans-serif; font-size: 16px; font-weight: bold; display: inline-block;">Shop Now</a>
          </td>
        </tr>
      </table>
      <!--<![endif]-->
    </td>
  </tr>
</table>""",
        "css_source": None,
        "compatibility": _COMPAT_FULL,
    },
    # ── 4. Hero Block ──
    {
        "name": "Hero Block",
        "slug": "hero-block",
        "description": "Full-width hero with background image, headline, subtext, and CTA. VML background for Outlook.",
        "category": "content",
        "html_source": """\
<style>
  @media (prefers-color-scheme: dark) {
    .hero-overlay { background-color: rgba(0,0,0,0.7) !important; }
    .hero-title { color: #ffffff !important; }
    .hero-subtitle { color: #cccccc !important; }
  }
  [data-ogsc] .hero-title { color: #ffffff !important; }
  [data-ogsc] .hero-subtitle { color: #cccccc !important; }
</style>
<!--[if mso]>
<v:rect xmlns:v="urn:schemas-microsoft-com:vml" fill="true" stroke="false" style="width:600px;height:300px;">
  <v:fill type="frame" src="https://via.placeholder.com/600x300" />
  <v:textbox inset="0,0,0,0">
<![endif]-->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-image: url('https://via.placeholder.com/600x300'); background-size: cover; background-position: center;">
  <tr>
    <td class="hero-overlay" style="padding: 48px 24px; text-align: center; background-color: rgba(0,0,0,0.4);">
      <h1 class="hero-title" style="margin: 0 0 16px; font-family: Arial, sans-serif; font-size: 32px; font-weight: bold; color: #ffffff; line-height: 1.2;">
        Discover What's New
      </h1>
      <p class="hero-subtitle" style="margin: 0 0 24px; font-family: Arial, sans-serif; font-size: 16px; color: #e0e0e0; line-height: 1.5;">
        Explore our latest collection curated just for you.
      </p>
      <a href="https://example.com" style="display: inline-block; padding: 12px 32px; background-color: #ffffff; color: #333333; text-decoration: none; font-family: Arial, sans-serif; font-size: 16px; font-weight: bold; border-radius: 4px;">Learn More</a>
    </td>
  </tr>
</table>
<!--[if mso]>
  </v:textbox>
</v:rect>
<![endif]-->""",
        "css_source": None,
        "compatibility": _COMPAT_PARTIAL_SAMSUNG,
    },
    # ── 5. Product Card ──
    {
        "name": "Product Card",
        "slug": "product-card",
        "description": "Product image with title, price, description, and CTA button. Table-based layout.",
        "category": "commerce",
        "html_source": """\
<style>
  @media (prefers-color-scheme: dark) {
    .product-card { background-color: #2d2d44 !important; }
    .product-title { color: #e0e0e0 !important; }
    .product-price { color: #8ecae6 !important; }
    .product-desc { color: #b0b0b0 !important; }
  }
  [data-ogsc] .product-card { background-color: #2d2d44 !important; }
  [data-ogsc] .product-title { color: #e0e0e0 !important; }
  [data-ogsc] .product-price { color: #8ecae6 !important; }
</style>
<!--[if mso]>
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0" border="0"><tr><td>
<![endif]-->
<table role="presentation" class="product-card" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden;">
  <tr>
    <td>
      <img src="https://via.placeholder.com/600x300" alt="Product Image" width="600" height="300" style="display: block; width: 100%; height: auto; border: 0;" />
    </td>
  </tr>
  <tr>
    <td style="padding: 20px 24px;">
      <h2 class="product-title" style="margin: 0 0 8px; font-family: Arial, sans-serif; font-size: 20px; font-weight: bold; color: #333333;">
        Product Name
      </h2>
      <p class="product-price" style="margin: 0 0 12px; font-family: Arial, sans-serif; font-size: 18px; font-weight: bold; color: #0066cc;">
        &pound;49.99
      </p>
      <p class="product-desc" style="margin: 0 0 20px; font-family: Arial, sans-serif; font-size: 14px; color: #666666; line-height: 1.5;">
        A short description of this product highlighting its key features and benefits.
      </p>
      <a href="https://example.com/product" style="display: inline-block; padding: 10px 24px; background-color: #0066cc; color: #ffffff; text-decoration: none; font-family: Arial, sans-serif; font-size: 14px; font-weight: bold; border-radius: 4px;">View Product</a>
    </td>
  </tr>
</table>
<!--[if mso]>
</td></tr></table>
<![endif]-->""",
        "css_source": None,
        "compatibility": _COMPAT_FULL,
    },
    # ── 6. Spacer ──
    {
        "name": "Spacer",
        "slug": "spacer",
        "description": "Adjustable-height transparent spacer. Works consistently across all clients.",
        "category": "structure",
        "html_source": """\
<!--[if mso]>
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0" border="0"><tr><td height="32" style="font-size:0;line-height:0;">&nbsp;</td></tr></table>
<![endif]-->
<!--[if !mso]><!-->
<div style="height: 32px; line-height: 32px; font-size: 1px;">&nbsp;</div>
<!--<![endif]-->""",
        "css_source": None,
        "compatibility": _COMPAT_FULL,
    },
    # ── 7. Social Icons ──
    {
        "name": "Social Icons",
        "slug": "social-icons",
        "description": "Row of social media icon links. Centered layout with consistent spacing.",
        "category": "social",
        "html_source": """\
<style>
  @media (prefers-color-scheme: dark) {
    .social-bg { background-color: #1a1a2e !important; }
    .social-label { color: #b0b0b0 !important; }
  }
  [data-ogsc] .social-bg { background-color: #1a1a2e !important; }
  [data-ogsc] .social-label { color: #b0b0b0 !important; }
</style>
<table role="presentation" class="social-bg" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #ffffff;">
  <tr>
    <td style="padding: 24px 0; text-align: center;">
      <p class="social-label" style="margin: 0 0 16px; font-family: Arial, sans-serif; font-size: 14px; color: #666666;">Follow us</p>
      <table role="presentation" cellpadding="0" cellspacing="0" border="0" align="center">
        <tr>
          <td style="padding: 0 8px;">
            <a href="https://facebook.com" style="text-decoration: none;">
              <img src="https://via.placeholder.com/32x32" alt="Facebook" width="32" height="32" style="display: block; border: 0;" />
            </a>
          </td>
          <td style="padding: 0 8px;">
            <a href="https://twitter.com" style="text-decoration: none;">
              <img src="https://via.placeholder.com/32x32" alt="Twitter / X" width="32" height="32" style="display: block; border: 0;" />
            </a>
          </td>
          <td style="padding: 0 8px;">
            <a href="https://instagram.com" style="text-decoration: none;">
              <img src="https://via.placeholder.com/32x32" alt="Instagram" width="32" height="32" style="display: block; border: 0;" />
            </a>
          </td>
          <td style="padding: 0 8px;">
            <a href="https://linkedin.com" style="text-decoration: none;">
              <img src="https://via.placeholder.com/32x32" alt="LinkedIn" width="32" height="32" style="display: block; border: 0;" />
            </a>
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>""",
        "css_source": None,
        "compatibility": _COMPAT_FULL,
    },
    # ── 8. Image Block ──
    {
        "name": "Image Block",
        "slug": "image-block",
        "description": "Responsive image with alt text, explicit dimensions, and optional caption.",
        "category": "content",
        "html_source": """\
<style>
  @media (prefers-color-scheme: dark) {
    .imgblock-caption { color: #b0b0b0 !important; }
  }
  [data-ogsc] .imgblock-caption { color: #b0b0b0 !important; }
</style>
<!--[if mso]>
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0" border="0"><tr><td>
<![endif]-->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
  <tr>
    <td style="padding: 0; text-align: center;">
      <img src="https://via.placeholder.com/600x400" alt="Descriptive alt text for the image" width="600" height="400" style="display: block; width: 100%; max-width: 600px; height: auto; border: 0;" />
    </td>
  </tr>
  <tr>
    <td style="padding: 8px 24px;">
      <p class="imgblock-caption" style="margin: 0; font-family: Arial, sans-serif; font-size: 12px; color: #999999; text-align: center; font-style: italic;">
        Image caption — describe the content for context.
      </p>
    </td>
  </tr>
</table>
<!--[if mso]>
</td></tr></table>
<![endif]-->""",
        "css_source": None,
        "compatibility": _COMPAT_FULL,
    },
    # ── 9. Text Block ──
    {
        "name": "Text Block",
        "slug": "text-block",
        "description": "Heading and paragraph text with configurable alignment. Core content component.",
        "category": "content",
        "html_source": """\
<style>
  @media (prefers-color-scheme: dark) {
    .textblock-bg { background-color: #1a1a2e !important; }
    .textblock-heading { color: #e0e0e0 !important; }
    .textblock-body { color: #cccccc !important; }
  }
  [data-ogsc] .textblock-bg { background-color: #1a1a2e !important; }
  [data-ogsc] .textblock-heading { color: #e0e0e0 !important; }
  [data-ogsc] .textblock-body { color: #cccccc !important; }
</style>
<!--[if mso]>
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0" border="0"><tr><td>
<![endif]-->
<table role="presentation" class="textblock-bg" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #ffffff;">
  <tr>
    <td style="padding: 24px;">
      <h2 class="textblock-heading" style="margin: 0 0 12px; font-family: Arial, sans-serif; font-size: 24px; font-weight: bold; color: #333333; line-height: 1.3;">
        Section Heading
      </h2>
      <p class="textblock-body" style="margin: 0; font-family: Arial, sans-serif; font-size: 16px; color: #555555; line-height: 1.6;">
        Body text goes here. This component supports multiple paragraphs and can be customised with different font sizes and colours to match your brand guidelines.
      </p>
    </td>
  </tr>
</table>
<!--[if mso]>
</td></tr></table>
<![endif]-->""",
        "css_source": None,
        "compatibility": _COMPAT_FULL,
    },
    # ── 10. Divider ──
    {
        "name": "Divider",
        "slug": "divider",
        "description": "Horizontal line separator with configurable colour and spacing.",
        "category": "structure",
        "html_source": """\
<style>
  @media (prefers-color-scheme: dark) {
    .divider-line { border-top-color: #444466 !important; }
  }
  [data-ogsc] .divider-line { border-top-color: #444466 !important; }
</style>
<!--[if mso]>
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0" border="0"><tr><td>
<![endif]-->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
  <tr>
    <td style="padding: 16px 24px;">
      <div class="divider-line" style="border-top: 1px solid #e0e0e0; font-size: 1px; line-height: 1px;">&nbsp;</div>
    </td>
  </tr>
</table>
<!--[if mso]>
</td></tr></table>
<![endif]-->""",
        "css_source": None,
        "compatibility": _COMPAT_FULL,
    },
]
