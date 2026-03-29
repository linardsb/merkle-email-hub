"""Seed data for pre-tested email components.

Dark mode CSS and Outlook dark mode selectors are consolidated
in the Email Shell component. Individual components contain
only HTML markup with slot markers and inline styles.
"""

from typing import Any

from app.components.data.compatibility_presets import COMPAT_PRESETS

_COMPAT_FULL: dict[str, str] = COMPAT_PRESETS["full"]
_COMPAT_PARTIAL_SAMSUNG: dict[str, str] = COMPAT_PRESETS["partial_samsung"]

_INLINE_SEEDS: list[dict[str, Any]] = [
    # ── 0. Email Shell (outer document wrapper) ──
    {
        "name": "Email Shell",
        "slug": "email-shell",
        "description": "Complete HTML document wrapper. All other components slot into the email_body. Includes DOCTYPE, VML namespaces, MSO OfficeDocumentSettings, color-scheme meta, responsive utility classes, dark mode base classes, and the 600px outer container.",
        "category": "structure",
        "html_source": """\
<!DOCTYPE html>
<html lang="en" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
  <meta charset="utf-8">
  <meta name="x-apple-disable-message-reformatting">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="format-detection" content="telephone=no, date=no, address=no, email=no, url=no">
  <meta name="color-scheme" content="light dark">
  <meta name="supported-color-schemes" content="light dark">
  <!--[if mso]>
  <noscript>
    <xml>
      <o:OfficeDocumentSettings xmlns:o="urn:schemas-microsoft-com:office:office">
        <o:PixelsPerInch>96</o:PixelsPerInch>
      </o:OfficeDocumentSettings>
    </xml>
  </noscript>
  <style>
    td,th,div,p,a,h1,h2,h3,h4,h5,h6 {font-family: "Segoe UI", sans-serif; mso-line-height-rule: exactly;}
  </style>
  <![endif]-->
  <title data-slot="email_title">Email</title>
  <style>
    :root {
      color-scheme: light dark;
      supported-color-schemes: light dark;
    }
    body { margin: 0; padding: 0; width: 100%; -webkit-text-size-adjust: 100%; }
    img { border: 0; outline: none; text-decoration: none; -ms-interpolation-mode: bicubic; }
    table { border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt; }
    @media only screen and (max-width: 599px) {
      .column { display: block !important; max-width: 100% !important; width: 100% !important; }
      .bannerimg { width: 100% !important; height: auto !important; }
      .wf { width: 100% !important; }
      .hide { display: none !important; max-height: 0 !important; overflow: hidden !important; mso-hide: all !important; }
      .db { display: block !important; }
    }
    @media (prefers-color-scheme: dark) {
      .dark-bg { background-color: #1a1a2e !important; }
      .dark-text { color: #e0e0e0 !important; }
    }
    [data-ogsc] .dark-bg { background-color: #1a1a2e !important; }
    [data-ogsb] .dark-text { color: #e0e0e0 !important; }

    /* ── Component dark mode overrides ── */
    @media (prefers-color-scheme: dark) {
      /* Structure backgrounds */
      .header-bg, .footer-bg, .navbar-bg, .logoheader-bg,
      .preheader-bg, .col2-bg, .col3-bg, .col4-bg,
      .revcol-bg, .social-bg, .textblock-bg,
      .artcard-bg { background-color: #1a1a2e !important; }
      .product-card { background-color: #2d2d44 !important; }

      /* Text — links */
      .header-link, .navbar-link, .preheader-link,
      .footer-link { color: #8ecae6 !important; }

      /* Text — muted */
      .footer-text, .social-label, .imgblock-caption { color: #b0b0b0 !important; }
      .product-desc { color: #b0b0b0 !important; }

      /* Text — headings */
      .textblock-heading, .artcard-heading, .product-title,
      .hero-title { color: #e0e0e0 !important; }

      /* Text — body */
      .textblock-body, .artcard-body,
      .hero-subtitle { color: #cccccc !important; }
      .product-price { color: #8ecae6 !important; }

      /* Interactive */
      .cta-btn { background-color: #4895ef !important; }
      .cta-btn a { color: #ffffff !important; }
      .cta-ghost { border-color: #8ecae6 !important; }
      .cta-ghost a { color: #8ecae6 !important; }

      /* Hero */
      .hero-overlay { background-color: rgba(0,0,0,0.7) !important; }

      /* Divider */
      .divider-line { border-top-color: #444466 !important; }
    }

    /* Outlook dark mode — backgrounds */
    [data-ogsc] .header-bg, [data-ogsc] .footer-bg, [data-ogsc] .navbar-bg,
    [data-ogsc] .logoheader-bg, [data-ogsc] .preheader-bg,
    [data-ogsc] .col2-bg, [data-ogsc] .col3-bg, [data-ogsc] .col4-bg,
    [data-ogsc] .revcol-bg, [data-ogsc] .social-bg,
    [data-ogsc] .textblock-bg, [data-ogsc] .artcard-bg { background-color: #1a1a2e !important; }
    [data-ogsc] .product-card { background-color: #2d2d44 !important; }

    /* Outlook dark mode — text */
    [data-ogsc] .header-link, [data-ogsc] .navbar-link,
    [data-ogsc] .preheader-link, [data-ogsc] .footer-link { color: #8ecae6 !important; }
    [data-ogsc] .footer-text, [data-ogsc] .social-label,
    [data-ogsc] .imgblock-caption { color: #b0b0b0 !important; }
    [data-ogsc] .textblock-heading, [data-ogsc] .artcard-heading,
    [data-ogsc] .product-title, [data-ogsc] .hero-title { color: #e0e0e0 !important; }
    [data-ogsb] .textblock-body, [data-ogsb] .artcard-body,
    [data-ogsc] .hero-subtitle { color: #cccccc !important; }
    [data-ogsc] .product-price { color: #8ecae6 !important; }

    /* Outlook dark mode — interactive & decorative */
    [data-ogsc] .cta-btn { background-color: #4895ef !important; }
    [data-ogsc] .cta-ghost { border-color: #8ecae6 !important; }
    [data-ogsc] .divider-line { border-top-color: #444466 !important; }
  </style>
</head>
<body style="margin: 0; padding: 0; width: 100%; -webkit-text-size-adjust: 100%;">
  <div role="article" aria-roledescription="email" aria-label="Email" lang="en" style="font-size: 16px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
    <div data-slot="preheader" style="display: none; max-height: 0; overflow: hidden; mso-hide: all;">Preview text goes here</div>
    <!--[if mso]>
    <table role="presentation" cellpadding="0" cellspacing="0" width="600" align="center" style="border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt;"><tr><td>
    <![endif]-->
    <div class="dark-bg" data-slot="email_body" style="max-width: 600px; margin: 0 auto; background-color: #ffffff;">
      <!-- Components go here — all self-contained blocks (MSO wrapper + outer table) -->
    </div>
    <!--[if mso]>
    </td></tr></table>
    <![endif]-->
  </div>
</body>
</html>""",
        "css_source": None,
        "compatibility": _COMPAT_FULL,
        "slot_definitions": [
            {
                "slot_id": "email_title",
                "slot_type": "body",
                "selector": "[data-slot='email_title']",
                "required": False,
            },
            {
                "slot_id": "preheader",
                "slot_type": "body",
                "selector": "[data-slot='preheader']",
                "required": False,
            },
            {
                "slot_id": "email_body",
                "slot_type": "body",
                "selector": "[data-slot='email_body']",
                "required": True,
            },
        ],
        "default_tokens": {
            "colors": {
                "background": "#ffffff",
                "dark_background": "#1a1a2e",
                "text": "#333333",
                "dark_text": "#e0e0e0",
            },
            "fonts": {"body": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"},
            "font_sizes": {"base": "16px"},
        },
    },
    # ── 1. Email Header ──
    {
        "name": "Email Header",
        "slug": "email-header",
        "description": "Logo with optional navigation links. Full-width container with centered content.",
        "category": "structure",
        "html_source": """\
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
        "slot_definitions": None,
        "default_tokens": None,
    },
    # ── 2. Email Footer ──
    {
        "name": "Email Footer",
        "slug": "email-footer",
        "description": "Unsubscribe link, company address, and legal text. GDPR-compliant footer.",
        "category": "structure",
        "html_source": """\
<!--[if mso]>
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0" border="0"><tr><td>
<![endif]-->
<table role="presentation" class="footer-bg" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #f5f5f5;">
  <tr>
    <td data-slot="footer_content" style="padding: 32px 24px; text-align: center;">
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
        "slot_definitions": [
            {
                "slot_id": "footer_content",
                "slot_type": "body",
                "selector": "[data-slot='footer_content']",
                "required": False,
            },
        ],
        "default_tokens": None,
    },
    # ── 3. CTA Button (upgraded: ghost variant, slot_definitions) ──
    {
        "name": "CTA Button",
        "slug": "cta-button",
        "description": "Centered call-to-action button with VML fallback for Outlook. Supports filled and ghost (outline) variants.",
        "category": "action",
        "html_source": """\
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
            <a data-slot="cta_url" href="https://example.com/cta" style="color: #ffffff; text-decoration: none; font-family: Arial, sans-serif; font-size: 16px; font-weight: bold; display: inline-block;">
              <span data-slot="cta_text">Shop Now</span>
            </a>
          </td>
        </tr>
      </table>
      <!--<![endif]-->
    </td>
  </tr>
</table>""",
        "css_source": None,
        "compatibility": _COMPAT_FULL,
        "slot_definitions": [
            {
                "slot_id": "cta_url",
                "slot_type": "cta",
                "selector": "[data-slot='cta_url']",
                "required": True,
            },
            {
                "slot_id": "cta_text",
                "slot_type": "body",
                "selector": "[data-slot='cta_text']",
                "required": True,
            },
        ],
        "default_tokens": {
            "colors": {"cta": "#0066cc", "cta_text": "#ffffff", "dark_cta": "#4895ef"},
            "spacing": {"padding_v": "12px", "padding_h": "32px"},
        },
    },
    # ── 4. Hero Block (upgraded: slot_definitions, default_tokens) ──
    {
        "name": "Hero Block",
        "slug": "hero-block",
        "description": "Full-width hero with background image, headline, subtext, and CTA. VML background for Outlook.",
        "category": "content",
        "html_source": """\
<!--[if mso]>
<v:rect xmlns:v="urn:schemas-microsoft-com:vml" fill="true" stroke="false" style="width:600px;height:300px;">
  <v:fill type="frame" src="https://via.placeholder.com/600x300" />
  <v:textbox inset="0,0,0,0">
<![endif]-->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-image: url('https://via.placeholder.com/600x300'); background-size: cover; background-position: center;">
  <tr>
    <td class="hero-overlay" style="padding: 48px 24px; text-align: center; background-color: rgba(0,0,0,0.4);">
      <h1 data-slot="headline" class="hero-title" style="margin: 0 0 16px; font-family: Arial, sans-serif; font-size: 32px; font-weight: bold; color: #ffffff; line-height: 1.2;">
        Discover What's New
      </h1>
      <p data-slot="subtext" class="hero-subtitle" style="margin: 0 0 24px; font-family: Arial, sans-serif; font-size: 16px; color: #e0e0e0; line-height: 1.5;">
        Explore our latest collection curated just for you.
      </p>
      <a data-slot="cta_url" href="https://example.com" style="display: inline-block; padding: 12px 32px; background-color: #ffffff; color: #333333; text-decoration: none; font-family: Arial, sans-serif; font-size: 16px; font-weight: bold; border-radius: 4px;">
        <span data-slot="cta_text">Learn More</span>
      </a>
    </td>
  </tr>
</table>
<!--[if mso]>
  </v:textbox>
</v:rect>
<![endif]-->""",
        "css_source": None,
        "compatibility": _COMPAT_PARTIAL_SAMSUNG,
        "slot_definitions": [
            {
                "slot_id": "hero_image",
                "slot_type": "image",
                "selector": "table[style*='background-image']",
                "required": True,
            },
            {
                "slot_id": "headline",
                "slot_type": "headline",
                "selector": "[data-slot='headline']",
                "required": True,
            },
            {
                "slot_id": "subtext",
                "slot_type": "body",
                "selector": "[data-slot='subtext']",
                "required": False,
            },
            {
                "slot_id": "cta_url",
                "slot_type": "cta",
                "selector": "[data-slot='cta_url']",
                "required": False,
            },
            {
                "slot_id": "cta_text",
                "slot_type": "body",
                "selector": "[data-slot='cta_text']",
                "required": False,
            },
        ],
        "default_tokens": {
            "colors": {
                "headline": "#ffffff",
                "subtext": "#e0e0e0",
                "cta": "#ffffff",
                "cta_text": "#333333",
                "overlay": "rgba(0,0,0,0.4)",
            },
            "fonts": {"headline": "Arial, sans-serif", "body": "Arial, sans-serif"},
            "font_sizes": {"headline": "32px", "subtext": "16px"},
        },
    },
    # ── 5. Product Card ──
    {
        "name": "Product Card",
        "slug": "product-card",
        "description": "Product image with title, price, description, and CTA button. Table-based layout.",
        "category": "commerce",
        "html_source": """\
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
        "slot_definitions": None,
        "default_tokens": None,
    },
    # ── 6. Spacer (upgraded: mso-line-height-rule, slot_definitions) ──
    {
        "name": "Spacer",
        "slug": "spacer",
        "description": "Adjustable-height transparent spacer. Works consistently across all clients.",
        "category": "structure",
        "html_source": """\
<!--[if mso]>
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0" border="0" style="border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt;"><tr><td height="32" style="font-size:0;line-height:0;mso-line-height-rule:exactly;">&nbsp;</td></tr></table>
<![endif]-->
<!--[if !mso]><!-->
<div data-slot="spacer_height" style="height: 32px; line-height: 32px; font-size: 1px; mso-line-height-rule: exactly;">&nbsp;</div>
<!--<![endif]-->""",
        "css_source": None,
        "compatibility": _COMPAT_FULL,
        "slot_definitions": [
            {
                "slot_id": "spacer_height",
                "slot_type": "body",
                "selector": "[data-slot='spacer_height']",
                "required": True,
            },
        ],
        "default_tokens": {
            "spacing": {"height": "32px"},
        },
    },
    # ── 7. Social Icons ──
    {
        "name": "Social Icons",
        "slug": "social-icons",
        "description": "Row of social media icon links. Centered layout with consistent spacing.",
        "category": "social",
        "html_source": """\
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
        "slot_definitions": None,
        "default_tokens": None,
    },
    # ── 8. Image Block (upgraded: .bannerimg responsive class) ──
    {
        "name": "Image Block",
        "slug": "image-block",
        "description": "Responsive image with alt text, explicit dimensions, and optional caption.",
        "category": "content",
        "html_source": """\
<!--[if mso]>
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0" border="0"><tr><td>
<![endif]-->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
  <tr>
    <td style="padding: 0; text-align: center;">
      <img class="bannerimg" src="https://via.placeholder.com/600x400" alt="Descriptive alt text for the image" width="600" height="400" style="display: block; width: 100%; max-width: 600px; height: auto; border: 0;" />
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
        "slot_definitions": None,
        "default_tokens": None,
    },
    # ── 9. Text Block ──
    {
        "name": "Text Block",
        "slug": "text-block",
        "description": "Heading and paragraph text with configurable alignment. Core content component.",
        "category": "content",
        "html_source": """\
<!--[if mso]>
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0" border="0"><tr><td>
<![endif]-->
<table role="presentation" class="textblock-bg" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #ffffff;">
  <tr>
    <td style="padding: 24px;">
      <h2 data-slot="heading" class="textblock-heading" style="margin: 0 0 12px; font-family: Arial, sans-serif; font-size: 24px; font-weight: bold; color: #333333; line-height: 1.3;">
        Section Heading
      </h2>
      <p data-slot="body" class="textblock-body" style="margin: 0; font-family: Arial, sans-serif; font-size: 16px; color: #555555; line-height: 1.6;">
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
        "slot_definitions": [
            {
                "slot_id": "heading",
                "slot_type": "text",
                "selector": "[data-slot='heading']",
                "required": False,
            },
            {
                "slot_id": "body",
                "slot_type": "body",
                "selector": "[data-slot='body']",
                "required": False,
            },
        ],
        "default_tokens": None,
    },
    # ── 10. Divider ──
    {
        "name": "Divider",
        "slug": "divider",
        "description": "Horizontal line separator with configurable colour and spacing.",
        "category": "structure",
        "html_source": """\
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
        "slot_definitions": None,
        "default_tokens": None,
    },
    # ═══════════════════════════════════════════════════════════
    # NEW COMPONENTS — Extracted from Sublime snippets
    # ═══════════════════════════════════════════════════════════
    # ── 11. Column Layout 2 ──
    {
        "name": "Column Layout 2",
        "slug": "column-layout-2",
        "description": "Hybrid responsive 2-column layout. MSO ghost table + inline-block divs that stack on mobile.",
        "category": "structure",
        "html_source": """\
<!--[if mso]>
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0" border="0" style="border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt;"><tr><td>
<![endif]-->
<table role="presentation" class="col2-bg" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #ffffff;">
  <tr>
    <td style="font-size: 0; text-align: center; mso-line-height-rule: exactly;">
      <!--[if mso]>
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt;"><tr><td width="300" valign="top">
      <![endif]-->
      <div class="column" style="display: inline-block; max-width: 300px; width: 100%; vertical-align: top;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt;">
          <tr>
            <td data-slot="col_1" style="padding: 0; font-family: Arial, sans-serif; font-size: 16px; color: #333333;">
              Column 1 content
            </td>
          </tr>
        </table>
      </div>
      <!--[if mso]>
      </td><td width="300" valign="top">
      <![endif]-->
      <div class="column" style="display: inline-block; max-width: 300px; width: 100%; vertical-align: top;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt;">
          <tr>
            <td data-slot="col_2" style="padding: 0; font-family: Arial, sans-serif; font-size: 16px; color: #333333;">
              Column 2 content
            </td>
          </tr>
        </table>
      </div>
      <!--[if mso]>
      </td></tr></table>
      <![endif]-->
    </td>
  </tr>
</table>
<!--[if mso]>
</td></tr></table>
<![endif]-->""",
        "css_source": None,
        "compatibility": _COMPAT_FULL,
        "slot_definitions": [
            {
                "slot_id": "col_1",
                "slot_type": "body",
                "selector": "[data-slot='col_1']",
                "required": True,
            },
            {
                "slot_id": "col_2",
                "slot_type": "body",
                "selector": "[data-slot='col_2']",
                "required": True,
            },
        ],
        "default_tokens": {
            "colors": {"background": "#ffffff", "dark_background": "#1a1a2e"},
            "spacing": {"column_gap": "0", "padding": "0"},
        },
    },
    # ── 12. Column Layout 3 ──
    {
        "name": "Column Layout 3",
        "slug": "column-layout-3",
        "description": "Hybrid responsive 3-column layout. MSO ghost table + inline-block divs that stack on mobile.",
        "category": "structure",
        "html_source": """\
<!--[if mso]>
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0" border="0" style="border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt;"><tr><td>
<![endif]-->
<table role="presentation" class="col3-bg" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #ffffff;">
  <tr>
    <td style="font-size: 0; text-align: center; mso-line-height-rule: exactly;">
      <!--[if mso]>
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt;"><tr><td width="200" valign="top">
      <![endif]-->
      <div class="column" style="display: inline-block; max-width: 200px; width: 100%; vertical-align: top;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt;">
          <tr>
            <td data-slot="col_1" style="padding: 0; font-family: Arial, sans-serif; font-size: 16px; color: #333333;">
              Column 1 content
            </td>
          </tr>
        </table>
      </div>
      <!--[if mso]>
      </td><td width="200" valign="top">
      <![endif]-->
      <div class="column" style="display: inline-block; max-width: 200px; width: 100%; vertical-align: top;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt;">
          <tr>
            <td data-slot="col_2" style="padding: 0; font-family: Arial, sans-serif; font-size: 16px; color: #333333;">
              Column 2 content
            </td>
          </tr>
        </table>
      </div>
      <!--[if mso]>
      </td><td width="200" valign="top">
      <![endif]-->
      <div class="column" style="display: inline-block; max-width: 200px; width: 100%; vertical-align: top;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt;">
          <tr>
            <td data-slot="col_3" style="padding: 0; font-family: Arial, sans-serif; font-size: 16px; color: #333333;">
              Column 3 content
            </td>
          </tr>
        </table>
      </div>
      <!--[if mso]>
      </td></tr></table>
      <![endif]-->
    </td>
  </tr>
</table>
<!--[if mso]>
</td></tr></table>
<![endif]-->""",
        "css_source": None,
        "compatibility": _COMPAT_FULL,
        "slot_definitions": [
            {
                "slot_id": "col_1",
                "slot_type": "body",
                "selector": "[data-slot='col_1']",
                "required": True,
            },
            {
                "slot_id": "col_2",
                "slot_type": "body",
                "selector": "[data-slot='col_2']",
                "required": True,
            },
            {
                "slot_id": "col_3",
                "slot_type": "body",
                "selector": "[data-slot='col_3']",
                "required": True,
            },
        ],
        "default_tokens": {
            "colors": {"background": "#ffffff", "dark_background": "#1a1a2e"},
            "spacing": {"column_gap": "0", "padding": "0"},
        },
    },
    # ── 13. Column Layout 4 ──
    {
        "name": "Column Layout 4",
        "slug": "column-layout-4",
        "description": "Hybrid responsive 4-column layout. MSO ghost table + inline-block divs that stack on mobile.",
        "category": "structure",
        "html_source": """\
<!--[if mso]>
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0" border="0" style="border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt;"><tr><td>
<![endif]-->
<table role="presentation" class="col4-bg" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #ffffff;">
  <tr>
    <td style="font-size: 0; text-align: center; mso-line-height-rule: exactly;">
      <!--[if mso]>
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt;"><tr><td width="150" valign="top">
      <![endif]-->
      <div class="column" style="display: inline-block; max-width: 150px; width: 100%; vertical-align: top;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt;">
          <tr>
            <td data-slot="col_1" style="padding: 0; font-family: Arial, sans-serif; font-size: 16px; color: #333333;">
              Column 1
            </td>
          </tr>
        </table>
      </div>
      <!--[if mso]>
      </td><td width="150" valign="top">
      <![endif]-->
      <div class="column" style="display: inline-block; max-width: 150px; width: 100%; vertical-align: top;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt;">
          <tr>
            <td data-slot="col_2" style="padding: 0; font-family: Arial, sans-serif; font-size: 16px; color: #333333;">
              Column 2
            </td>
          </tr>
        </table>
      </div>
      <!--[if mso]>
      </td><td width="150" valign="top">
      <![endif]-->
      <div class="column" style="display: inline-block; max-width: 150px; width: 100%; vertical-align: top;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt;">
          <tr>
            <td data-slot="col_3" style="padding: 0; font-family: Arial, sans-serif; font-size: 16px; color: #333333;">
              Column 3
            </td>
          </tr>
        </table>
      </div>
      <!--[if mso]>
      </td><td width="150" valign="top">
      <![endif]-->
      <div class="column" style="display: inline-block; max-width: 150px; width: 100%; vertical-align: top;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt;">
          <tr>
            <td data-slot="col_4" style="padding: 0; font-family: Arial, sans-serif; font-size: 16px; color: #333333;">
              Column 4
            </td>
          </tr>
        </table>
      </div>
      <!--[if mso]>
      </td></tr></table>
      <![endif]-->
    </td>
  </tr>
</table>
<!--[if mso]>
</td></tr></table>
<![endif]-->""",
        "css_source": None,
        "compatibility": _COMPAT_FULL,
        "slot_definitions": [
            {
                "slot_id": "col_1",
                "slot_type": "body",
                "selector": "[data-slot='col_1']",
                "required": True,
            },
            {
                "slot_id": "col_2",
                "slot_type": "body",
                "selector": "[data-slot='col_2']",
                "required": True,
            },
            {
                "slot_id": "col_3",
                "slot_type": "body",
                "selector": "[data-slot='col_3']",
                "required": True,
            },
            {
                "slot_id": "col_4",
                "slot_type": "body",
                "selector": "[data-slot='col_4']",
                "required": True,
            },
        ],
        "default_tokens": {
            "colors": {"background": "#ffffff", "dark_background": "#1a1a2e"},
            "spacing": {"column_gap": "0", "padding": "0"},
        },
    },
    # ── 14. Reverse Column ──
    {
        "name": "Reverse Column",
        "slug": "reverse-column",
        "description": "RTL-trick reverse stacking layout. Image right on desktop, text stacks first on mobile.",
        "category": "structure",
        "html_source": """\
<!--[if mso]>
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0" border="0" style="border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt;"><tr><td>
<![endif]-->
<table role="presentation" class="revcol-bg" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #ffffff;">
  <tr>
    <td dir="rtl" style="font-size: 0; text-align: center; mso-line-height-rule: exactly;">
      <!--[if mso]>
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" dir="rtl" style="border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt;"><tr><td width="300" valign="top" dir="ltr">
      <![endif]-->
      <div class="column" dir="ltr" style="display: inline-block; max-width: 300px; width: 100%; vertical-align: top;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt;">
          <tr>
            <td data-slot="secondary_content" style="padding: 16px; font-family: Arial, sans-serif; font-size: 16px; color: #333333;">
              <img src="https://via.placeholder.com/280x200" alt="Image" width="280" style="display: block; width: 100%; height: auto; border: 0;" />
            </td>
          </tr>
        </table>
      </div>
      <!--[if mso]>
      </td><td width="300" valign="top" dir="ltr">
      <![endif]-->
      <div class="column" dir="ltr" style="display: inline-block; max-width: 300px; width: 100%; vertical-align: top;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt;">
          <tr>
            <td data-slot="primary_content" style="padding: 16px; font-family: Arial, sans-serif; font-size: 16px; color: #333333;">
              Primary content appears first on mobile
            </td>
          </tr>
        </table>
      </div>
      <!--[if mso]>
      </td></tr></table>
      <![endif]-->
    </td>
  </tr>
</table>
<!--[if mso]>
</td></tr></table>
<![endif]-->""",
        "css_source": None,
        "compatibility": _COMPAT_PARTIAL_SAMSUNG,
        "slot_definitions": [
            {
                "slot_id": "primary_content",
                "slot_type": "body",
                "selector": "[data-slot='primary_content']",
                "required": True,
            },
            {
                "slot_id": "secondary_content",
                "slot_type": "body",
                "selector": "[data-slot='secondary_content']",
                "required": True,
            },
        ],
        "default_tokens": {
            "colors": {"background": "#ffffff", "dark_background": "#1a1a2e"},
            "spacing": {"padding": "16px"},
        },
    },
    # ── 15. Full-Width Image ──
    {
        "name": "Full-Width Image",
        "slug": "full-width-image",
        "description": "Responsive full-width image with MSO fixed-width wrapper and optional link.",
        "category": "content",
        "html_source": """\
<!--[if mso]>
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0" border="0" style="border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt;"><tr><td>
<![endif]-->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt; max-width: 600px; margin: 0 auto;">
  <tr>
    <td style="padding: 0; text-align: center; font-size: 0; line-height: 0;">
      <a data-slot="link_url" href="https://example.com" style="text-decoration: none;">
        <img data-slot="image_url" class="bannerimg" src="https://via.placeholder.com/600x300" alt="Full width image" width="600" style="display: block; width: 100%; max-width: 600px; height: auto; border: 0;" />
      </a>
    </td>
  </tr>
</table>
<!--[if mso]>
</td></tr></table>
<![endif]-->""",
        "css_source": None,
        "compatibility": _COMPAT_FULL,
        "slot_definitions": [
            {
                "slot_id": "image_url",
                "slot_type": "image",
                "selector": "[data-slot='image_url']",
                "required": True,
            },
            {
                "slot_id": "image_alt",
                "slot_type": "body",
                "selector": "[data-slot='image_url']",
                "required": True,
            },
            {
                "slot_id": "link_url",
                "slot_type": "cta",
                "selector": "[data-slot='link_url']",
                "required": False,
            },
        ],
        "default_tokens": None,
    },
    # ── 16. Preheader ──
    {
        "name": "Preheader",
        "slug": "preheader",
        "description": "Hidden preheader text visible in inbox preview + 'View in browser' link.",
        "category": "structure",
        "html_source": """\
<!--[if mso]>
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0" border="0" style="border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt;"><tr><td>
<![endif]-->
<table role="presentation" class="preheader-bg" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #f8f8f8; border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt;">
  <tr>
    <td style="font-size: 0; text-align: center; mso-line-height-rule: exactly;">
      <!--[if mso]>
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td width="300" valign="top">
      <![endif]-->
      <div class="hide" style="display: inline-block; max-width: 300px; width: 100%; vertical-align: top;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
          <tr>
            <td style="padding: 8px 16px; font-family: Arial, sans-serif; font-size: 11px; color: #999999; line-height: 1.4;">
              <span data-slot="preheader_text" style="color: #999999;">Preview text shown in inbox list view.</span>
              <!--[if !mso]><!-->&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;<!--<![endif]-->
            </td>
          </tr>
        </table>
      </div>
      <!--[if mso]>
      </td><td width="300" valign="top">
      <![endif]-->
      <div style="display: inline-block; max-width: 300px; width: 100%; vertical-align: top;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
          <tr>
            <td style="padding: 8px 16px; text-align: right; font-family: Arial, sans-serif; font-size: 11px; line-height: 1.4;">
              <a data-slot="view_online_url" class="preheader-link" href="https://example.com/view-online" style="color: #666666; text-decoration: underline;">View in browser</a>
            </td>
          </tr>
        </table>
      </div>
      <!--[if mso]>
      </td></tr></table>
      <![endif]-->
    </td>
  </tr>
</table>
<!--[if mso]>
</td></tr></table>
<![endif]-->""",
        "css_source": None,
        "compatibility": _COMPAT_FULL,
        "slot_definitions": [
            {
                "slot_id": "preheader_text",
                "slot_type": "body",
                "selector": "[data-slot='preheader_text']",
                "required": True,
            },
            {
                "slot_id": "view_online_url",
                "slot_type": "cta",
                "selector": "[data-slot='view_online_url']",
                "required": False,
            },
        ],
        "default_tokens": None,
    },
    # ── 17. Article Card ──
    {
        "name": "Article Card",
        "slug": "article-card",
        "description": "Image + heading + body + CTA in hybrid 2-column layout with configurable image position.",
        "category": "content",
        "html_source": """\
<!--[if mso]>
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0" border="0" style="border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt;"><tr><td>
<![endif]-->
<table role="presentation" class="artcard-bg" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #ffffff; border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt;">
  <tr>
    <td style="font-size: 0; text-align: center; mso-line-height-rule: exactly;">
      <!--[if mso]>
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td width="280" valign="top">
      <![endif]-->
      <div class="column" style="display: inline-block; max-width: 280px; width: 100%; vertical-align: top;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
          <tr>
            <td style="padding: 0;">
              <img data-slot="image_url" src="https://via.placeholder.com/280x200" alt="Article image" width="280" style="display: block; width: 100%; height: auto; border: 0;" />
            </td>
          </tr>
        </table>
      </div>
      <!--[if mso]>
      </td><td width="320" valign="top">
      <![endif]-->
      <div class="column" style="display: inline-block; max-width: 320px; width: 100%; vertical-align: top;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
          <tr>
            <td style="padding: 20px;">
              <h2 data-slot="heading" class="artcard-heading" style="margin: 0 0 8px; font-family: Arial, sans-serif; font-size: 20px; font-weight: bold; color: #333333; line-height: 1.3;">
                Article Heading
              </h2>
              <p data-slot="body_text" class="artcard-body" style="margin: 0 0 16px; font-family: Arial, sans-serif; font-size: 14px; color: #555555; line-height: 1.5;">
                Article body text with a brief description of the content.
              </p>
              <a data-slot="cta_url" href="https://example.com/article" style="display: inline-block; padding: 10px 24px; background-color: #0066cc; color: #ffffff; text-decoration: none; font-family: Arial, sans-serif; font-size: 14px; font-weight: bold; border-radius: 4px;">
                <span data-slot="cta_text">Read More</span>
              </a>
            </td>
          </tr>
        </table>
      </div>
      <!--[if mso]>
      </td></tr></table>
      <![endif]-->
    </td>
  </tr>
</table>
<!--[if mso]>
</td></tr></table>
<![endif]-->""",
        "css_source": None,
        "compatibility": _COMPAT_FULL,
        "slot_definitions": [
            {
                "slot_id": "image_url",
                "slot_type": "image",
                "selector": "[data-slot='image_url']",
                "required": True,
            },
            {
                "slot_id": "image_alt",
                "slot_type": "body",
                "selector": "[data-slot='image_url']",
                "required": True,
            },
            {
                "slot_id": "heading",
                "slot_type": "headline",
                "selector": "[data-slot='heading']",
                "required": True,
            },
            {
                "slot_id": "body_text",
                "slot_type": "body",
                "selector": "[data-slot='body_text']",
                "required": True,
            },
            {
                "slot_id": "cta_text",
                "slot_type": "body",
                "selector": "[data-slot='cta_text']",
                "required": False,
            },
            {
                "slot_id": "cta_url",
                "slot_type": "cta",
                "selector": "[data-slot='cta_url']",
                "required": False,
            },
        ],
        "default_tokens": {
            "colors": {
                "heading": "#333333",
                "body": "#555555",
                "cta": "#0066cc",
                "cta_text": "#ffffff",
                "dark_heading": "#e0e0e0",
                "dark_body": "#cccccc",
            },
            "fonts": {"heading": "Arial, sans-serif", "body": "Arial, sans-serif"},
            "font_sizes": {"heading": "20px", "body": "14px"},
            "spacing": {"image_width": "280px", "text_padding": "20px"},
        },
    },
    # ── 18. Image Grid ──
    {
        "name": "Image Grid",
        "slug": "image-grid",
        "description": "2-column responsive image grid using hybrid pattern. Each cell is a linked image.",
        "category": "content",
        "html_source": """\
<!--[if mso]>
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0" border="0" style="border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt;"><tr><td>
<![endif]-->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt;">
  <tr>
    <td style="font-size: 0; text-align: center; mso-line-height-rule: exactly;">
      <!--[if mso]>
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td width="300" valign="top">
      <![endif]-->
      <div class="column" style="display: inline-block; max-width: 300px; width: 100%; vertical-align: top;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
          <tr>
            <td style="padding: 4px;">
              <a data-slot="link_1" href="https://example.com/1" style="text-decoration: none;">
                <img data-slot="image_1" class="bannerimg" src="https://via.placeholder.com/292x200" alt="Grid image 1" width="292" style="display: block; width: 100%; height: auto; border: 0;" />
              </a>
            </td>
          </tr>
        </table>
      </div>
      <!--[if mso]>
      </td><td width="300" valign="top">
      <![endif]-->
      <div class="column" style="display: inline-block; max-width: 300px; width: 100%; vertical-align: top;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
          <tr>
            <td style="padding: 4px;">
              <a data-slot="link_2" href="https://example.com/2" style="text-decoration: none;">
                <img data-slot="image_2" class="bannerimg" src="https://via.placeholder.com/292x200" alt="Grid image 2" width="292" style="display: block; width: 100%; height: auto; border: 0;" />
              </a>
            </td>
          </tr>
        </table>
      </div>
      <!--[if mso]>
      </td></tr></table>
      <![endif]-->
    </td>
  </tr>
</table>
<!--[if mso]>
</td></tr></table>
<![endif]-->""",
        "css_source": None,
        "compatibility": _COMPAT_FULL,
        "slot_definitions": [
            {
                "slot_id": "image_1",
                "slot_type": "image",
                "selector": "[data-slot='image_1']",
                "required": True,
            },
            {
                "slot_id": "image_2",
                "slot_type": "image",
                "selector": "[data-slot='image_2']",
                "required": True,
            },
            {
                "slot_id": "link_1",
                "slot_type": "cta",
                "selector": "[data-slot='link_1']",
                "required": False,
            },
            {
                "slot_id": "link_2",
                "slot_type": "cta",
                "selector": "[data-slot='link_2']",
                "required": False,
            },
        ],
        "default_tokens": None,
    },
    # ── 19. Logo Header ──
    {
        "name": "Logo Header",
        "slug": "logo-header",
        "description": "Centered logo image with MSO wrapper. Simpler than email-header (no nav links).",
        "category": "structure",
        "html_source": """\
<!--[if mso]>
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0" border="0" style="border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt;"><tr><td>
<![endif]-->
<table role="presentation" class="logoheader-bg" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #ffffff; border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt;">
  <tr>
    <td style="padding: 24px 0; text-align: center;">
      <img data-slot="logo_url" src="https://via.placeholder.com/180x48" alt="Company Logo" width="180" style="display: inline-block; border: 0; outline: none;" />
    </td>
  </tr>
</table>
<!--[if mso]>
</td></tr></table>
<![endif]-->""",
        "css_source": None,
        "compatibility": _COMPAT_FULL,
        "slot_definitions": [
            {
                "slot_id": "logo_url",
                "slot_type": "image",
                "selector": "[data-slot='logo_url']",
                "required": True,
            },
            {
                "slot_id": "logo_alt",
                "slot_type": "body",
                "selector": "[data-slot='logo_url']",
                "required": True,
            },
            {
                "slot_id": "logo_width",
                "slot_type": "body",
                "selector": "[data-slot='logo_url']",
                "required": True,
            },
        ],
        "default_tokens": {
            "colors": {"background": "#ffffff", "dark_background": "#1a1a2e"},
        },
    },
    # ── 20. Navigation Bar ──
    {
        "name": "Navigation Bar",
        "slug": "navigation-bar",
        "description": "Horizontal inline nav links, hidden on mobile. Use for desktop-focused navigation.",
        "category": "structure",
        "html_source": """\
<!--[if mso]>
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0" border="0" style="border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt;"><tr><td>
<![endif]-->
<table role="presentation" class="navbar-bg hide" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #ffffff; border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt;">
  <tr>
    <td data-slot="nav_links" style="padding: 12px 24px; text-align: center; font-family: Arial, sans-serif; font-size: 14px; line-height: 1.4;">
      <a class="navbar-link" href="https://example.com" style="color: #333333; text-decoration: none; padding: 0 12px;">Home</a>
      <a class="navbar-link" href="https://example.com/products" style="color: #333333; text-decoration: none; padding: 0 12px;">Products</a>
      <a class="navbar-link" href="https://example.com/about" style="color: #333333; text-decoration: none; padding: 0 12px;">About</a>
      <a class="navbar-link" href="https://example.com/contact" style="color: #333333; text-decoration: none; padding: 0 12px;">Contact</a>
    </td>
  </tr>
</table>
<!--[if mso]>
</td></tr></table>
<![endif]-->""",
        "css_source": None,
        "compatibility": _COMPAT_FULL,
        "slot_definitions": [
            {
                "slot_id": "nav_links",
                "slot_type": "body",
                "selector": "[data-slot='nav_links']",
                "required": True,
            },
        ],
        "default_tokens": {
            "colors": {
                "link": "#333333",
                "dark_link": "#8ecae6",
                "background": "#ffffff",
                "dark_background": "#1a1a2e",
            },
        },
    },
    # ── 22. Product Grid ──
    {
        "name": "Product Grid",
        "slug": "product-grid",
        "description": "2-column product card grid. Each cell has image, title, description, and CTA.",
        "category": "commerce",
        "html_source": """\
<!--[if mso]>
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0" border="0" style="border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt;"><tr><td>
<![endif]-->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt;">
  <tr>
    <td style="font-size: 0; text-align: center; mso-line-height-rule: exactly;">
      <!--[if mso]>
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td width="300" valign="top">
      <![endif]-->
      <div class="column" style="display: inline-block; max-width: 300px; width: 100%; vertical-align: top;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
          <tr>
            <td style="padding: 8px;">
              <img data-slot="product_1_image" src="https://via.placeholder.com/284x200" alt="Product 1" width="284" style="display: block; width: 100%; height: auto; border: 0;" />
              <h3 data-slot="product_1_title" style="margin: 12px 0 4px; font-family: Arial, sans-serif; font-size: 16px; font-weight: bold; color: #333333;">Product Title</h3>
              <p data-slot="product_1_desc" style="margin: 0 0 12px; font-family: Arial, sans-serif; font-size: 14px; color: #666666; line-height: 1.5;">Short description of this product.</p>
              <a data-slot="product_1_cta" href="https://example.com/product-1" style="display: inline-block; padding: 8px 20px; background-color: #0066cc; color: #ffffff; text-decoration: none; font-family: Arial, sans-serif; font-size: 13px; font-weight: bold; border-radius: 4px;">Shop Now</a>
            </td>
          </tr>
        </table>
      </div>
      <!--[if mso]>
      </td><td width="300" valign="top">
      <![endif]-->
      <div class="column" style="display: inline-block; max-width: 300px; width: 100%; vertical-align: top;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
          <tr>
            <td style="padding: 8px;">
              <img data-slot="product_2_image" src="https://via.placeholder.com/284x200" alt="Product 2" width="284" style="display: block; width: 100%; height: auto; border: 0;" />
              <h3 data-slot="product_2_title" style="margin: 12px 0 4px; font-family: Arial, sans-serif; font-size: 16px; font-weight: bold; color: #333333;">Product Title</h3>
              <p data-slot="product_2_desc" style="margin: 0 0 12px; font-family: Arial, sans-serif; font-size: 14px; color: #666666; line-height: 1.5;">Short description of this product.</p>
              <a data-slot="product_2_cta" href="https://example.com/product-2" style="display: inline-block; padding: 8px 20px; background-color: #0066cc; color: #ffffff; text-decoration: none; font-family: Arial, sans-serif; font-size: 13px; font-weight: bold; border-radius: 4px;">Shop Now</a>
            </td>
          </tr>
        </table>
      </div>
      <!--[if mso]>
      </td></tr></table>
      <![endif]-->
    </td>
  </tr>
</table>
<!--[if mso]>
</td></tr></table>
<![endif]-->""",
        "css_source": None,
        "compatibility": _COMPAT_FULL,
        "slot_definitions": [
            {
                "slot_id": "product_1_image",
                "slot_type": "image",
                "selector": "[data-slot='product_1_image']",
                "required": True,
            },
            {
                "slot_id": "product_1_title",
                "slot_type": "text",
                "selector": "[data-slot='product_1_title']",
                "required": True,
            },
            {
                "slot_id": "product_1_desc",
                "slot_type": "text",
                "selector": "[data-slot='product_1_desc']",
                "required": False,
            },
            {
                "slot_id": "product_1_cta",
                "slot_type": "cta",
                "selector": "[data-slot='product_1_cta']",
                "required": False,
            },
            {
                "slot_id": "product_2_image",
                "slot_type": "image",
                "selector": "[data-slot='product_2_image']",
                "required": True,
            },
            {
                "slot_id": "product_2_title",
                "slot_type": "text",
                "selector": "[data-slot='product_2_title']",
                "required": True,
            },
            {
                "slot_id": "product_2_desc",
                "slot_type": "text",
                "selector": "[data-slot='product_2_desc']",
                "required": False,
            },
            {
                "slot_id": "product_2_cta",
                "slot_type": "cta",
                "selector": "[data-slot='product_2_cta']",
                "required": False,
            },
        ],
        "default_tokens": {
            "colors": {
                "title": "#333333",
                "dark_title": "#f0f0f0",
                "description": "#666666",
                "dark_description": "#cccccc",
                "cta_bg": "#0066cc",
                "dark_cta_bg": "#3399ff",
                "cta_text": "#ffffff",
            },
        },
    },
    # ── 23. Category Nav ──
    {
        "name": "Category Nav",
        "slug": "category-nav",
        "description": "Vertical list of category labels or icon+label rows for content navigation.",
        "category": "structure",
        "html_source": """\
<!--[if mso]>
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0" border="0" style="border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt;"><tr><td>
<![endif]-->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #f8f8f8; border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt;">
  <tr>
    <td style="padding: 16px 24px;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td data-slot="nav_item_1" style="padding: 6px 0; font-family: Arial, sans-serif; font-size: 14px; color: #333333; line-height: 1.4;">
            <a href="#" style="color: #0066cc; text-decoration: none;">Category 1</a>
          </td>
        </tr>
        <tr>
          <td data-slot="nav_item_2" style="padding: 6px 0; font-family: Arial, sans-serif; font-size: 14px; color: #333333; line-height: 1.4;">
            <a href="#" style="color: #0066cc; text-decoration: none;">Category 2</a>
          </td>
        </tr>
        <tr>
          <td data-slot="nav_item_3" style="padding: 6px 0; font-family: Arial, sans-serif; font-size: 14px; color: #333333; line-height: 1.4;">
            <a href="#" style="color: #0066cc; text-decoration: none;">Category 3</a>
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
        "slot_definitions": [
            {
                "slot_id": "nav_item_1",
                "slot_type": "text",
                "selector": "[data-slot='nav_item_1']",
                "required": True,
            },
            {
                "slot_id": "nav_item_2",
                "slot_type": "text",
                "selector": "[data-slot='nav_item_2']",
                "required": True,
            },
            {
                "slot_id": "nav_item_3",
                "slot_type": "text",
                "selector": "[data-slot='nav_item_3']",
                "required": False,
            },
        ],
        "default_tokens": {
            "colors": {
                "link": "#0066cc",
                "dark_link": "#8ecae6",
                "background": "#f8f8f8",
                "dark_background": "#1a1a2e",
            },
        },
    },
    # ── 24. Image Gallery ──
    {
        "name": "Image Gallery",
        "slug": "image-gallery",
        "description": "3-column responsive image gallery. Each cell is a linked image with alt text.",
        "category": "content",
        "html_source": """\
<!--[if mso]>
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0" border="0" style="border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt;"><tr><td>
<![endif]-->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt;">
  <tr>
    <td style="font-size: 0; text-align: center; mso-line-height-rule: exactly;">
      <!--[if mso]>
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td width="200" valign="top">
      <![endif]-->
      <div class="column" style="display: inline-block; max-width: 200px; width: 100%; vertical-align: top;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
          <tr>
            <td style="padding: 4px;">
              <img data-slot="image_1" src="https://via.placeholder.com/192x192" alt="Gallery image 1" width="192" style="display: block; width: 100%; height: auto; border: 0;" />
            </td>
          </tr>
        </table>
      </div>
      <!--[if mso]>
      </td><td width="200" valign="top">
      <![endif]-->
      <div class="column" style="display: inline-block; max-width: 200px; width: 100%; vertical-align: top;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
          <tr>
            <td style="padding: 4px;">
              <img data-slot="image_2" src="https://via.placeholder.com/192x192" alt="Gallery image 2" width="192" style="display: block; width: 100%; height: auto; border: 0;" />
            </td>
          </tr>
        </table>
      </div>
      <!--[if mso]>
      </td><td width="200" valign="top">
      <![endif]-->
      <div class="column" style="display: inline-block; max-width: 200px; width: 100%; vertical-align: top;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
          <tr>
            <td style="padding: 4px;">
              <img data-slot="image_3" src="https://via.placeholder.com/192x192" alt="Gallery image 3" width="192" style="display: block; width: 100%; height: auto; border: 0;" />
            </td>
          </tr>
        </table>
      </div>
      <!--[if mso]>
      </td></tr></table>
      <![endif]-->
    </td>
  </tr>
</table>
<!--[if mso]>
</td></tr></table>
<![endif]-->""",
        "css_source": None,
        "compatibility": _COMPAT_FULL,
        "slot_definitions": [
            {
                "slot_id": "image_1",
                "slot_type": "image",
                "selector": "[data-slot='image_1']",
                "required": True,
            },
            {
                "slot_id": "image_2",
                "slot_type": "image",
                "selector": "[data-slot='image_2']",
                "required": True,
            },
            {
                "slot_id": "image_3",
                "slot_type": "image",
                "selector": "[data-slot='image_3']",
                "required": True,
            },
        ],
        "default_tokens": {
            "colors": {
                "background": "#ffffff",
                "dark_background": "#1a1a2e",
            },
        },
    },
]


def _build_all_seeds() -> list[dict[str, Any]]:
    """Combine inline seeds with file-based seeds from manifest.

    Inline seeds take precedence on slug collision.
    """
    from app.components.data.file_loader import load_file_components

    inline_slugs = {s["slug"] for s in _INLINE_SEEDS}
    file_seeds = load_file_components()
    merged = list(_INLINE_SEEDS)
    for fs in file_seeds:
        if fs["slug"] not in inline_slugs:
            merged.append(fs)
    return merged


COMPONENT_SEEDS: list[dict[str, Any]] = _build_all_seeds()
