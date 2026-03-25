"""Synthetic test data for the Dark Mode agent.

Each test case includes real-world HTML input that the agent must enhance
with dark mode support. HTML patterns sourced from production email templates
and email development best practices.
"""

from typing import Any

# ---------------------------------------------------------------------------
# Real-world HTML fragments used across test cases
# ---------------------------------------------------------------------------

# Simple single-column light theme email
SIMPLE_LIGHT_EMAIL = """\
<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Welcome Email</title>
<style>
  body { margin: 0; padding: 0; background-color: #f5f5f5; }
  .email-container { max-width: 600px; margin: 0 auto; background-color: #ffffff; }
  h1 { color: #1a1a1a; font-family: Arial, sans-serif; font-size: 28px; }
  p { color: #333333; font-family: Arial, sans-serif; font-size: 16px; line-height: 1.5; }
  a { color: #0066cc; }
  .cta-button { background-color: #0066cc; color: #ffffff; padding: 14px 28px;
    text-decoration: none; border-radius: 4px; font-family: Arial, sans-serif; }
  .footer { background-color: #f0f0f0; color: #666666; font-size: 12px; }
</style>
</head>
<body>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
  style="background-color: #f5f5f5;">
<tr><td align="center">
<table role="presentation" class="email-container" width="600" cellpadding="0"
  cellspacing="0" border="0" style="background-color: #ffffff;">
  <tr>
    <td style="padding: 40px 30px;">
      <img src="https://placehold.co/200x60" alt="Company Logo" width="200" height="60"
        style="display: block; border: 0;">
    </td>
  </tr>
  <tr>
    <td style="padding: 0 30px 20px;">
      <h1 style="color: #1a1a1a; margin: 0;">Welcome aboard!</h1>
    </td>
  </tr>
  <tr>
    <td style="padding: 0 30px 30px;">
      <p style="color: #333333; margin: 0;">We're thrilled to have you join us.
        Here's everything you need to get started with your new account.</p>
    </td>
  </tr>
  <tr>
    <td style="padding: 0 30px 40px;" align="center">
      <a href="https://example.com/start" class="cta-button"
        style="background-color: #0066cc; color: #ffffff; padding: 14px 28px;
        text-decoration: none; border-radius: 4px; font-family: Arial, sans-serif;
        font-size: 16px; display: inline-block;">Get Started</a>
    </td>
  </tr>
  <tr>
    <td class="footer" style="padding: 20px 30px; background-color: #f0f0f0;">
      <p style="color: #666666; font-size: 12px; margin: 0;">
        &copy; 2025 Company Inc. | <a href="https://example.com/unsub"
        style="color: #666666;">Unsubscribe</a>
      </p>
    </td>
  </tr>
</table>
</td></tr>
</table>
</body>
</html>"""

# Multi-column with MSO ghost tables (Outlook pattern)
MSO_GHOST_TABLE_EMAIL = """\
<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml"
  xmlns:v="urn:schemas-microsoft-com:vml"
  xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<!--[if gte mso 9]>
<xml>
<o:OfficeDocumentSettings>
<o:AllowPNG/>
<o:PixelsPerInch>96</o:PixelsPerInch>
</o:OfficeDocumentSettings>
</xml>
<![endif]-->
<title>Product Update</title>
<style>
  body { margin: 0; padding: 0; background-color: #ffffff; }
  .header-bar { background-color: #004E89; color: #ffffff; }
  h1 { color: #004E89; font-family: Georgia, serif; }
  h2 { color: #1a1a1a; font-family: Georgia, serif; }
  p { color: #444444; font-family: Arial, sans-serif; }
  .product-card { background-color: #fafafa; border: 1px solid #e0e0e0; }
</style>
</head>
<body>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
<tr><td align="center">

<!-- Header bar -->
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0">
  <tr>
    <td class="header-bar" style="background-color: #004E89; padding: 20px 30px;">
      <img src="https://placehold.co/150x40" alt="Logo" width="150" height="40"
        style="display: block; border: 0;">
    </td>
  </tr>
</table>

<!-- Two-column product section with MSO ghost tables -->
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0">
  <tr>
    <td style="padding: 30px 15px;">
      <!--[if mso]><table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%"><tr><td width="270" valign="top"><![endif]-->
      <div style="display: inline-block; width: 100%; max-width: 270px; vertical-align: top;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
          <tr>
            <td class="product-card" style="padding: 20px; background-color: #fafafa;
              border: 1px solid #e0e0e0;">
              <img src="https://placehold.co/230x230" alt="Product Alpha"
                width="230" height="230" style="display: block; border: 0; width: 100%;">
              <h2 style="color: #1a1a1a; font-family: Georgia, serif;
                margin: 15px 0 8px;">Product Alpha</h2>
              <p style="color: #444444; font-family: Arial, sans-serif;
                margin: 0 0 15px;">Revolutionary design meets everyday utility.</p>
              <p style="color: #004E89; font-weight: bold; margin: 0;">$149.00</p>
            </td>
          </tr>
        </table>
      </div>
      <!--[if mso]></td><td width="30">&nbsp;</td><td width="270" valign="top"><![endif]-->
      <div style="display: inline-block; width: 100%; max-width: 270px; vertical-align: top;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
          <tr>
            <td class="product-card" style="padding: 20px; background-color: #fafafa;
              border: 1px solid #e0e0e0;">
              <img src="https://placehold.co/230x230" alt="Product Beta"
                width="230" height="230" style="display: block; border: 0; width: 100%;">
              <h2 style="color: #1a1a1a; font-family: Georgia, serif;
                margin: 15px 0 8px;">Product Beta</h2>
              <p style="color: #444444; font-family: Arial, sans-serif;
                margin: 0 0 15px;">Engineered for performance and style.</p>
              <p style="color: #004E89; font-weight: bold; margin: 0;">$199.00</p>
            </td>
          </tr>
        </table>
      </div>
      <!--[if mso]></td></tr></table><![endif]-->
    </td>
  </tr>
</table>

<!-- Footer -->
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0">
  <tr>
    <td style="padding: 20px 30px; background-color: #f5f5f5;">
      <p style="color: #999999; font-size: 12px; font-family: Arial, sans-serif; margin: 0;">
        &copy; 2025 Company. <a href="#" style="color: #999999;">Unsubscribe</a> |
        <a href="#" style="color: #999999;">View in browser</a>
      </p>
    </td>
  </tr>
</table>

</td></tr>
</table>
</body>
</html>"""

# VML elements present (Outlook bulletproof button + background)
VML_HEAVY_EMAIL = """\
<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml"
  xmlns:v="urn:schemas-microsoft-com:vml"
  xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<!--[if gte mso 9]>
<xml>
<o:OfficeDocumentSettings>
<o:AllowPNG/>
<o:PixelsPerInch>96</o:PixelsPerInch>
</o:OfficeDocumentSettings>
</xml>
<![endif]-->
<title>Conference Invite</title>
<style>
  body { margin: 0; padding: 0; }
  h1 { color: #ffffff; font-family: Arial, sans-serif; }
  p { color: #333333; font-family: Arial, sans-serif; }
</style>
</head>
<body>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
<tr><td align="center">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0">

  <!-- Hero with VML background image -->
  <tr>
    <td>
      <!--[if gte mso 9]>
      <v:rect xmlns:v="urn:schemas-microsoft-com:vml" fill="true" stroke="false"
        style="width:600px;height:350px;">
      <v:fill type="frame" src="https://placehold.co/600x350" color="#1a1a2e" />
      <v:textbox inset="0,0,0,0">
      <![endif]-->
      <div style="background-image: url('https://placehold.co/600x350');
        background-color: #1a1a2e; background-size: cover; background-position: center;
        max-width: 600px;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
          <tr>
            <td style="padding: 80px 40px; text-align: center;">
              <h1 style="color: #ffffff; font-family: Arial, sans-serif; font-size: 36px;
                margin: 0 0 10px;">DevSummit 2025</h1>
              <p style="color: #cccccc; font-size: 18px; margin: 0;">
                March 15-17 | San Francisco</p>
            </td>
          </tr>
        </table>
      </div>
      <!--[if gte mso 9]>
      </v:textbox>
      </v:rect>
      <![endif]-->
    </td>
  </tr>

  <!-- Content -->
  <tr>
    <td style="padding: 40px 30px; background-color: #ffffff;">
      <p style="color: #333333; font-family: Arial, sans-serif; font-size: 16px;
        line-height: 1.6; margin: 0 0 30px;">
        Join 2,000+ developers for three days of talks, workshops, and networking.
      </p>

      <!-- VML Bulletproof Button -->
      <div align="center">
        <!--[if mso]>
        <v:roundrect xmlns:v="urn:schemas-microsoft-com:vml"
          xmlns:w="urn:schemas-microsoft-com:office:word"
          href="https://example.com/register"
          style="height:50px;v-text-anchor:middle;width:220px;"
          arcsize="8%" strokecolor="#FF6B35" fillcolor="#FF6B35">
        <w:anchorlock/>
        <center style="color:#ffffff;font-family:Arial,sans-serif;font-size:16px;
          font-weight:bold;">Register Now</center>
        </v:roundrect>
        <![endif]-->
        <!--[if !mso]><!-->
        <a href="https://example.com/register"
          style="background-color: #FF6B35; color: #ffffff; padding: 14px 40px;
          text-decoration: none; border-radius: 4px; font-family: Arial, sans-serif;
          font-size: 16px; font-weight: bold; display: inline-block;">Register Now</a>
        <!--<![endif]-->
      </div>
    </td>
  </tr>

  <!-- Footer -->
  <tr>
    <td style="padding: 20px 30px; background-color: #1a1a2e;">
      <p style="color: #999999; font-family: Arial, sans-serif; font-size: 12px; margin: 0;">
        &copy; 2025 DevSummit. <a href="#" style="color: #7f8fa4;">Unsubscribe</a>
      </p>
    </td>
  </tr>

</table>
</td></tr>
</table>
</body>
</html>"""

# Already partially dark-themed email
ALREADY_DARK_EMAIL = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Dark Theme Email</title>
<style>
  body { margin: 0; padding: 0; background-color: #0d1117; }
  .container { background-color: #161b22; }
  h1 { color: #f0f6fc; font-family: Arial, sans-serif; }
  p { color: #8b949e; font-family: Arial, sans-serif; }
  a { color: #58a6ff; }
  .badge { background-color: #238636; color: #ffffff; padding: 4px 12px;
    border-radius: 12px; font-size: 12px; }
  .divider { border-top: 1px solid #30363d; }
  .code-block { background-color: #0d1117; border: 1px solid #30363d;
    padding: 16px; font-family: 'Courier New', monospace; color: #c9d1d9; }
</style>
</head>
<body style="background-color: #0d1117;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
  style="background-color: #0d1117;">
<tr><td align="center">
<table role="presentation" class="container" width="600" cellpadding="0" cellspacing="0"
  border="0" style="background-color: #161b22;">
  <tr>
    <td style="padding: 30px;">
      <img src="https://placehold.co/120x30" alt="Logo" width="120" height="30"
        style="display: block; border: 0;">
    </td>
  </tr>
  <tr>
    <td style="padding: 0 30px 15px;">
      <h1 style="color: #f0f6fc; margin: 0;">New Release Available</h1>
    </td>
  </tr>
  <tr>
    <td style="padding: 0 30px 20px;">
      <span class="badge" style="background-color: #238636; color: #ffffff;
        padding: 4px 12px; border-radius: 12px; font-size: 12px;">v3.2.0</span>
    </td>
  </tr>
  <tr>
    <td style="padding: 0 30px 20px;">
      <p style="color: #8b949e; line-height: 1.6; margin: 0;">
        We've shipped new features including improved dark mode support,
        faster rendering, and better accessibility.</p>
    </td>
  </tr>
  <tr>
    <td style="padding: 0 30px 30px;">
      <div class="code-block" style="background-color: #0d1117; border: 1px solid #30363d;
        padding: 16px; font-family: 'Courier New', monospace; color: #c9d1d9;">
        npm install @company/sdk@3.2.0
      </div>
    </td>
  </tr>
  <tr>
    <td style="padding: 0 30px 30px;" align="center">
      <a href="https://example.com/changelog"
        style="background-color: #238636; color: #ffffff; padding: 12px 24px;
        text-decoration: none; border-radius: 6px; font-family: Arial, sans-serif;
        font-size: 14px; display: inline-block;">View Changelog</a>
    </td>
  </tr>
  <tr>
    <td class="divider" style="border-top: 1px solid #30363d; padding: 20px 30px;">
      <p style="color: #484f58; font-size: 12px; margin: 0;">
        &copy; 2025 Company. <a href="#" style="color: #58a6ff;">Unsubscribe</a>
      </p>
    </td>
  </tr>
</table>
</td></tr>
</table>
</body>
</html>"""

# Heavy inline styles with brand colors
BRAND_HEAVY_EMAIL = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Brand Promo</title>
</head>
<body style="margin: 0; padding: 0; background-color: #FFF8F0;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
  style="background-color: #FFF8F0;">
<tr><td align="center">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0">
  <!-- Brand color header -->
  <tr>
    <td style="background-color: #E85D04; padding: 25px 30px;">
      <img src="https://placehold.co/140x45" alt="Brand Logo" width="140" height="45"
        style="display: block; border: 0;">
    </td>
  </tr>
  <!-- Hero with brand gradient simulated by stacked rows -->
  <tr>
    <td style="background-color: #DC2F02; padding: 50px 30px; text-align: center;">
      <h1 style="color: #ffffff; font-family: Georgia, serif; font-size: 32px;
        margin: 0 0 10px;">Autumn Collection</h1>
      <p style="color: #FFEDD8; font-family: Arial, sans-serif; font-size: 18px;
        margin: 0;">Warmth meets elegance</p>
    </td>
  </tr>
  <!-- Product on warm background -->
  <tr>
    <td style="background-color: #FFEDD8; padding: 40px 30px;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td width="200" valign="top">
            <img src="https://placehold.co/200x250" alt="Cashmere Scarf" width="200"
              height="250" style="display: block; border: 0;">
          </td>
          <td width="20">&nbsp;</td>
          <td valign="top" style="padding-top: 10px;">
            <h2 style="color: #370617; font-family: Georgia, serif; font-size: 22px;
              margin: 0 0 10px;">Cashmere Blend Scarf</h2>
            <p style="color: #6A040F; font-family: Arial, sans-serif; font-size: 14px;
              line-height: 1.5; margin: 0 0 15px;">
              Luxuriously soft, ethically sourced cashmere in our signature autumn palette.</p>
            <p style="color: #E85D04; font-family: Arial, sans-serif; font-size: 20px;
              font-weight: bold; margin: 0 0 20px;">$89.00</p>
            <a href="https://example.com/scarf"
              style="background-color: #E85D04; color: #ffffff; padding: 12px 24px;
              text-decoration: none; font-family: Arial, sans-serif; font-size: 14px;
              display: inline-block;">Shop Now</a>
          </td>
        </tr>
      </table>
    </td>
  </tr>
  <!-- Footer -->
  <tr>
    <td style="background-color: #370617; padding: 20px 30px;">
      <p style="color: #FFEDD8; font-family: Arial, sans-serif; font-size: 12px; margin: 0;">
        &copy; 2025 Brand Co. <a href="#" style="color: #E85D04;">Unsubscribe</a>
      </p>
    </td>
  </tr>
</table>
</td></tr>
</table>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

DARK_MODE_TEST_CASES: list[dict[str, Any]] = [
    # -------------------------------------------------------------------------
    # 1. Simple light email — baseline dark mode conversion
    # -------------------------------------------------------------------------
    {
        "id": "dark-001",
        "dimensions": {
            "input_html_complexity": "simple_single_column",
            "color_scenario": "standard_light_theme",
            "outlook_challenge": "no_outlook_issues",
            "image_scenario": "logo_on_white_background",
        },
        "html_input": SIMPLE_LIGHT_EMAIL,
        "color_overrides": None,
        "preserve_colors": None,
        "expected_challenges": [
            "add meta color-scheme tags",
            "add prefers-color-scheme media query",
            "remap #ffffff bg to dark",
            "remap #1a1a1a/#333333 text to light",
            "remap #f5f5f5 outer bg to dark",
            "preserve CTA button contrast",
            "maintain WCAG AA 4.5:1 contrast",
        ],
    },
    # -------------------------------------------------------------------------
    # 2. MSO ghost table email — must preserve all conditionals
    # -------------------------------------------------------------------------
    {
        "id": "dark-002",
        "dimensions": {
            "input_html_complexity": "mso_conditional_comments",
            "color_scenario": "standard_light_theme",
            "outlook_challenge": "mso_conditional_preservation",
            "image_scenario": "many_product_images",
        },
        "html_input": MSO_GHOST_TABLE_EMAIL,
        "color_overrides": None,
        "preserve_colors": None,
        "expected_challenges": [
            "preserve ALL MSO conditional comments intact",
            "preserve DPI scaling XML block",
            "add dark mode CSS without breaking ghost tables",
            "add [data-ogsc] and [data-ogsb] selectors",
            "remap product card backgrounds",
            "preserve xmlns:v and xmlns:o namespaces",
        ],
    },
    # -------------------------------------------------------------------------
    # 3. VML-heavy email — must not touch VML elements
    # -------------------------------------------------------------------------
    {
        "id": "dark-003",
        "dimensions": {
            "input_html_complexity": "vml_elements_present",
            "color_scenario": "standard_light_theme",
            "outlook_challenge": "vml_color_preservation",
            "image_scenario": "no_images",
        },
        "html_input": VML_HEAVY_EMAIL,
        "color_overrides": None,
        "preserve_colors": None,
        "expected_challenges": [
            "preserve VML v:rect and v:fill elements",
            "preserve VML v:roundrect button",
            "preserve w:anchorlock",
            "do NOT modify colors inside VML blocks",
            "add dark mode for non-VML content only",
            "preserve <!--[if !mso]><!--> pattern",
        ],
    },
    # -------------------------------------------------------------------------
    # 4. Already dark email — should not double-darken
    # -------------------------------------------------------------------------
    {
        "id": "dark-004",
        "dimensions": {
            "input_html_complexity": "simple_single_column",
            "color_scenario": "already_dark_themed",
            "outlook_challenge": "data_ogsc_text_override",
            "image_scenario": "no_images",
        },
        "html_input": ALREADY_DARK_EMAIL,
        "color_overrides": None,
        "preserve_colors": None,
        "expected_challenges": [
            "detect already-dark color palette",
            "add meta tags for dark mode declaration",
            "minimal or no color remapping needed",
            "add [data-ogsc] to prevent Outlook overriding text colors",
            "preserve code-block styling",
            "do not invert already-light-on-dark text",
        ],
    },
    # -------------------------------------------------------------------------
    # 5. Brand-heavy email with custom color overrides
    # -------------------------------------------------------------------------
    {
        "id": "dark-005",
        "dimensions": {
            "input_html_complexity": "heavy_inline_styles",
            "color_scenario": "brand_colors_dominant",
            "outlook_challenge": "data_ogsb_background_override",
            "image_scenario": "many_product_images",
        },
        "html_input": BRAND_HEAVY_EMAIL,
        "color_overrides": {
            "#FFF8F0": "#1a1a1a",
            "#FFEDD8": "#2d1f0e",
            "#E85D04": "#FF8C42",
            "#DC2F02": "#8B1A01",
            "#370617": "#1a0308",
        },
        "preserve_colors": ["#ffffff"],
        "expected_challenges": [
            "apply custom color overrides exactly",
            "preserve #ffffff where specified",
            "handle brand color #E85D04 remapping",
            "add [data-ogsb] for Outlook background overrides",
            "maintain contrast with remapped brand palette",
            "heavy inline styles must be overridden via CSS specificity",
        ],
    },
    # -------------------------------------------------------------------------
    # 6. Logo on white background — needs image swap pattern
    # -------------------------------------------------------------------------
    {
        "id": "dark-006",
        "dimensions": {
            "input_html_complexity": "simple_single_column",
            "color_scenario": "standard_light_theme",
            "outlook_challenge": "no_outlook_issues",
            "image_scenario": "logo_on_white_background",
        },
        "html_input": SIMPLE_LIGHT_EMAIL,
        "color_overrides": None,
        "preserve_colors": None,
        "expected_challenges": [
            "suggest dark mode image swap pattern for logo",
            "implement: .dark-img { display:none } / .light-img pattern",
            "add [data-ogsc] .dark-img selector for Outlook",
            "preserve existing image attributes",
            "add dark mode CSS:\n"
            "  .dark-img { display:none !important; }\n"
            "  @media (prefers-color-scheme: dark) {\n"
            "    .dark-img { display:block !important; }\n"
            "    .light-img { display:none !important; }\n"
            "  }\n"
            "  [data-ogsc] .dark-img { display:block !important; }\n"
            "  [data-ogsc] .light-img { display:none !important; }",
        ],
    },
    # -------------------------------------------------------------------------
    # 7. Mixed MSO + modern — comprehensive dark mode
    # -------------------------------------------------------------------------
    {
        "id": "dark-007",
        "dimensions": {
            "input_html_complexity": "mixed_mso_and_modern",
            "color_scenario": "many_unique_colors",
            "outlook_challenge": "data_ogsc_text_override",
            "image_scenario": "icons_need_inversion",
        },
        "html_input": MSO_GHOST_TABLE_EMAIL,
        "color_overrides": {
            "#004E89": "#1a3a5c",
            "#fafafa": "#2a2a2a",
            "#e0e0e0": "#404040",
        },
        "preserve_colors": ["#ffffff", "#004E89"],
        "expected_challenges": [
            "multiple color remappings with overrides",
            "preserve specified colors",
            "handle conflict: #004E89 in overrides AND preserve list",
            "suggest filter:invert for icon images",
            "add both prefers-color-scheme AND [data-ogsc]",
            "preserve MSO ghost table structure exactly",
        ],
    },
    # -------------------------------------------------------------------------
    # 8. Outlook Android dark mode targeting
    # -------------------------------------------------------------------------
    {
        "id": "dark-008",
        "dimensions": {
            "input_html_complexity": "simple_single_column",
            "color_scenario": "standard_light_theme",
            "outlook_challenge": "outlook_android_dark",
            "image_scenario": "transparent_png_logo",
        },
        "html_input": SIMPLE_LIGHT_EMAIL,
        "color_overrides": None,
        "preserve_colors": None,
        "expected_challenges": [
            "add [data-ogsc] selectors (Outlook Android uses these)",
            "add [data-ogsb] for background targeting",
            "transparent PNG logo should work in dark mode",
            "add both @media and attribute selectors:\n"
            "  @media (prefers-color-scheme: dark) { ... }\n"
            "  [data-ogsc] .dark-text { color: #ffffff !important; }\n"
            "  [data-ogsb] .dark-bg { background-color: #121212 !important; }",
        ],
    },
    # -------------------------------------------------------------------------
    # 9. Low contrast original — needs careful remapping
    # -------------------------------------------------------------------------
    {
        "id": "dark-009",
        "dimensions": {
            "input_html_complexity": "heavy_inline_styles",
            "color_scenario": "low_contrast_original",
            "outlook_challenge": "no_outlook_issues",
            "image_scenario": "no_images",
        },
        "html_input": SIMPLE_LIGHT_EMAIL.replace(
            "#333333",
            "#999999",  # deliberately low contrast text
        ).replace(
            "#1a1a1a",
            "#aaaaaa",  # heading also low contrast
        ),
        "color_overrides": None,
        "preserve_colors": None,
        "expected_challenges": [
            "detect low-contrast input colors",
            "remap to dark mode with IMPROVED contrast",
            "ensure dark mode meets WCAG AA 4.5:1",
            "do not just invert — compute proper contrast pairs",
        ],
    },
    # -------------------------------------------------------------------------
    # 10. Gradient simulation with stacked colored rows
    # -------------------------------------------------------------------------
    {
        "id": "dark-010",
        "dimensions": {
            "input_html_complexity": "heavy_inline_styles",
            "color_scenario": "gradient_backgrounds",
            "outlook_challenge": "data_ogsb_background_override",
            "image_scenario": "dark_images_need_swap",
        },
        "html_input": BRAND_HEAVY_EMAIL,
        "color_overrides": None,
        "preserve_colors": None,
        "expected_challenges": [
            "remap gradient-like stacked background colors cohesively",
            "maintain visual progression in dark mode",
            "each background shade needs a dark equivalent",
            "add [data-ogsb] for each background color",
            "suggest dark version image swap for product shots",
        ],
    },
]
