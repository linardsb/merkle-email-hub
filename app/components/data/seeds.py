"""Seed data for pre-tested email components.

Dark mode CSS and Outlook dark mode selectors are consolidated
in the Email Shell component. Individual components contain
only HTML markup with slot markers and inline styles.
"""

from typing import Any

from app.components.data.compatibility_presets import COMPAT_PRESETS

_COMPAT_FULL: dict[str, str] = COMPAT_PRESETS["full"]

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
    # Remaining inline seeds removed — all converter components now loaded
    # from file-based HTML in email-templates/components/ via the manifest.
    # Only email-shell stays inline as it is the document wrapper, not a component.
]


def _build_all_seeds() -> list[dict[str, Any]]:
    """Build the unified seed list: inline shell + all file-based components.

    File-based components are the single source of truth for all
    non-shell components.  The manifest in ``component_manifest.yaml``
    defines metadata; HTML is read from ``email-templates/components/``.
    """
    from app.components.data.file_loader import load_file_components

    return list(_INLINE_SEEDS) + load_file_components()


COMPONENT_SEEDS: list[dict[str, Any]] = _build_all_seeds()
