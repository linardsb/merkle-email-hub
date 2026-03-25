"""Synthetic test data for the Outlook Fixer agent.

Each test case provides HTML with a specific Outlook rendering issue.
The agent must fix the issue while preserving everything else.
"""

# Minimal email HTML base — each test case modifies this with specific issues
_BASE_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="color-scheme" content="light dark">
<title>Test Email</title>
<style>
  @media (prefers-color-scheme: dark) {{
    .dark-bg {{ background-color: #1a1a2e !important; }}
    .dark-text {{ color: #ffffff !important; }}
  }}
</style>
</head>
<body style="margin:0; padding:0; background-color:#ffffff;">
{body_content}
</body>
</html>"""


# ── Test Case HTML Fixtures ──

_TWO_COL_NO_GHOST = _BASE_HTML.format(
    body_content="""\
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0">
  <tr>
    <td>
      <div style="display:inline-block; width:290px; vertical-align:top;">
        <h2 style="font-family:Arial,sans-serif;">Left Column</h2>
        <p style="font-family:Arial,sans-serif;">Article summary content goes here.</p>
      </div>
      <div style="display:inline-block; width:290px; vertical-align:top;">
        <h2 style="font-family:Arial,sans-serif;">Right Column</h2>
        <p style="font-family:Arial,sans-serif;">Sidebar content here.</p>
      </div>
    </td>
  </tr>
</table>"""
)

_CSS_BG_IMAGE = _BASE_HTML.format(
    body_content="""\
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0">
  <tr>
    <td style="background-image:url('https://placehold.co/600x300');
      background-size:cover; background-position:center; height:300px;
      padding:40px; font-family:Arial,sans-serif; color:#ffffff;">
      <h1>Summer Sale</h1>
      <p>Up to 50% off all items</p>
    </td>
  </tr>
</table>"""
)

_CSS_ONLY_BUTTON = _BASE_HTML.format(
    body_content="""\
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0">
  <tr>
    <td style="padding:20px; font-family:Arial,sans-serif;">
      <p>Check out our latest collection.</p>
      <a href="https://example.com/shop"
        style="display:inline-block; padding:14px 28px; background-color:#007bff;
        color:#ffffff; text-decoration:none; border-radius:6px;
        font-family:Arial,sans-serif; font-size:16px; font-weight:bold;">
        Shop Now
      </a>
    </td>
  </tr>
</table>"""
)

_THREE_COL_NO_GHOST = _BASE_HTML.format(
    body_content="""\
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0">
  <tr>
    <td>
      <div style="display:inline-block; width:180px; vertical-align:top; padding:10px;">
        <img src="https://placehold.co/180x180" alt="Product 1"
          style="display:block; width:100%; height:auto;">
        <p style="font-family:Arial,sans-serif;">Product One - $29.99</p>
      </div>
      <div style="display:inline-block; width:180px; vertical-align:top; padding:10px;">
        <img src="https://placehold.co/180x180" alt="Product 2"
          style="display:block; width:100%; height:auto;">
        <p style="font-family:Arial,sans-serif;">Product Two - $39.99</p>
      </div>
      <div style="display:inline-block; width:180px; vertical-align:top; padding:10px;">
        <img src="https://placehold.co/180x180" alt="Product 3"
          style="display:block; width:100%; height:auto;">
        <p style="font-family:Arial,sans-serif;">Product Three - $49.99</p>
      </div>
    </td>
  </tr>
</table>"""
)

_FONT_NO_TD = _BASE_HTML.format(
    body_content="""\
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0"
  style="font-family:'Proxima Nova',Helvetica,Arial,sans-serif;">
  <tr>
    <td style="padding:20px;">
      <h1>Welcome to Our Newsletter</h1>
      <p style="line-height:24px;">This paragraph uses a web font with no explicit
        font-family on the td element. In Outlook, this will fall back to
        Times New Roman because Outlook ignores font inheritance.</p>
    </td>
  </tr>
</table>"""
)

_NO_DPI_FIX = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Test Email</title>
</head>
<body style="margin:0; padding:0;">
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0">
  <tr>
    <td style="padding:20px; font-family:Arial,sans-serif;">
      <img src="https://placehold.co/600x200" alt="Hero banner"
        style="display:block; width:100%; height:auto;">
      <h1>Product Launch</h1>
      <p>Introducing our newest line of products.</p>
    </td>
  </tr>
</table>
</body>
</html>"""

_BROKEN_MSO_COMMENTS = _BASE_HTML.format(
    body_content="""\
<!--[if mso]>
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0">
<tr><td>
<![endif]-->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"
  style="max-width:600px; margin:0 auto;">
  <tr>
    <td style="padding:20px; font-family:Arial,sans-serif;">
      <h1>Content Here</h1>
      <p>The MSO conditional above is opened but never closed.</p>
    </td>
  </tr>
</table>"""
)

_MISSING_VML_NS = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Test Email</title>
</head>
<body style="margin:0; padding:0;">
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0">
  <tr>
    <td style="padding:20px; font-family:Arial,sans-serif;">
      <!--[if mso]>
      <v:roundrect href="https://example.com/cta"
        style="height:44px; v-text-anchor:middle; width:200px;"
        arcsize="10%" fillcolor="#007bff" strokecolor="#007bff">
      <center style="color:#ffffff; font-family:Arial,sans-serif; font-size:16px;">
        Buy Now
      </center>
      </v:roundrect>
      <![endif]-->
      <!--[if !mso]><!-->
      <a href="https://example.com/cta"
        style="display:inline-block; padding:12px 24px; background-color:#007bff;
        color:#ffffff; text-decoration:none; border-radius:4px;">Buy Now</a>
      <!--<![endif]-->
    </td>
  </tr>
</table>
</body>
</html>"""

_TABLE_GAPS = _BASE_HTML.format(
    body_content="""\
<table role="presentation" width="600" align="center">
  <tr>
    <td style="background-color:#007bff; padding:30px; color:#ffffff;
      font-family:Arial,sans-serif;">
      <h1>Header Section</h1>
    </td>
  </tr>
  <tr>
    <td style="background-color:#ffffff; padding:30px;
      font-family:Arial,sans-serif;">
      <p>Body content section. There are visible gaps between these sections
        in Outlook due to missing table attributes.</p>
    </td>
  </tr>
  <tr>
    <td style="background-color:#333333; padding:20px; color:#ffffff;
      font-family:Arial,sans-serif;">
      <p>Footer section.</p>
    </td>
  </tr>
</table>"""
)

_IMG_NO_ATTRS = _BASE_HTML.format(
    body_content="""\
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0">
  <tr>
    <td style="padding:20px; font-family:Arial,sans-serif;">
      <img src="https://placehold.co/600x300" alt="Hero image"
        style="width:100%; height:auto;">
      <p>This image has CSS width but no HTML width/height attributes.
        Outlook will render it at its native size, ignoring CSS.</p>
    </td>
  </tr>
</table>"""
)

_LINE_HEIGHT = _BASE_HTML.format(
    body_content="""\
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0">
  <tr>
    <td style="padding:20px; font-family:Arial,sans-serif;">
      <p style="font-size:14px; line-height:22px;">
        This paragraph has a specific line-height of 22px, but Outlook's Word
        engine calculates line-height differently. Without mso-line-height-rule:
        exactly, the spacing will be inconsistent between Outlook and other clients.
      </p>
      <p style="font-size:14px; line-height:22px;">
        A second paragraph to demonstrate the compounding effect of line-height
        differences across multiple text blocks.
      </p>
    </td>
  </tr>
</table>"""
)

_MAX_WIDTH_NO_MSO = _BASE_HTML.format(
    body_content="""\
<div style="max-width:600px; margin:0 auto; background-color:#ffffff;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
    <tr>
      <td style="padding:20px; font-family:Arial,sans-serif;">
        <h1>Newsletter</h1>
        <p>This email uses max-width on a div for centering, which Outlook
          completely ignores. The email will stretch to full width.</p>
      </td>
    </tr>
  </table>
</div>"""
)


# ── Test Cases ──

OUTLOOK_FIXER_TEST_CASES: list[dict[str, object]] = [
    # 1. Two-column layout without ghost tables
    {
        "id": "outfix-001",
        "dimensions": {
            "issue_type": "ghost_table",
            "column_count": "two_column",
            "complexity": "standard",
        },
        "html_input": _TWO_COL_NO_GHOST,
        "expected_challenges": [
            "Add MSO conditional ghost table for 2-column layout",
            "Set explicit width attributes on ghost table cells",
            "Preserve existing inline-block responsive behavior",
        ],
    },
    # 2. Background image using only CSS (no VML)
    {
        "id": "outfix-002",
        "dimensions": {
            "issue_type": "vml_background",
            "element": "background_image",
            "complexity": "standard",
        },
        "html_input": _CSS_BG_IMAGE,
        "expected_challenges": [
            "Add VML v:rect with v:fill for background image",
            "Add xmlns:v namespace to html tag",
            "Preserve CSS background for non-Outlook clients",
            "Use v:textbox for content overlay",
        ],
    },
    # 3. Button without VML roundrect fallback
    {
        "id": "outfix-003",
        "dimensions": {
            "issue_type": "vml_button",
            "element": "bulletproof_button",
            "complexity": "standard",
        },
        "html_input": _CSS_ONLY_BUTTON,
        "expected_challenges": [
            "Add VML v:roundrect for bulletproof button",
            "Preserve CSS button for non-Outlook clients",
            "Match colors between VML and CSS versions",
            "Add xmlns:v namespace if missing",
        ],
    },
    # 4. Three-column layout without ghost tables
    {
        "id": "outfix-004",
        "dimensions": {
            "issue_type": "ghost_table",
            "column_count": "three_column",
            "complexity": "high",
        },
        "html_input": _THREE_COL_NO_GHOST,
        "expected_challenges": [
            "Add MSO conditional ghost table for 3-column layout",
            "Calculate correct width distribution with gutters",
            "Preserve product card content and images",
        ],
    },
    # 5. Font falling to Times New Roman
    {
        "id": "outfix-005",
        "dimensions": {
            "issue_type": "typography",
            "element": "font_stack",
            "complexity": "standard",
        },
        "html_input": _FONT_NO_TD,
        "expected_challenges": [
            "Add explicit font-family to td elements",
            "Add mso-font-alt for web font fallback",
            "Add MSO conditional style block for font override",
        ],
    },
    # 6. Missing DPI scaling fix
    {
        "id": "outfix-006",
        "dimensions": {
            "issue_type": "dpi_scaling",
            "element": "image",
            "complexity": "standard",
        },
        "html_input": _NO_DPI_FIX,
        "expected_challenges": [
            "Add xmlns:o namespace to html tag",
            "Add OfficeDocumentSettings with PixelsPerInch",
            "Add explicit width/height HTML attributes to images",
        ],
    },
    # 7. Broken MSO conditional comments (unclosed)
    {
        "id": "outfix-007",
        "dimensions": {
            "issue_type": "mso_conditional",
            "element": "comment_matching",
            "complexity": "high",
        },
        "html_input": _BROKEN_MSO_COMMENTS,
        "expected_challenges": [
            "Detect unclosed MSO conditional",
            "Add matching closing comment",
            "Preserve existing table structure",
        ],
    },
    # 8. VML without xmlns namespace
    {
        "id": "outfix-008",
        "dimensions": {
            "issue_type": "vml_namespace",
            "element": "namespace_declaration",
            "complexity": "standard",
        },
        "html_input": _MISSING_VML_NS,
        "expected_challenges": [
            "Add xmlns:v namespace to html tag",
            "Verify VML element is inside MSO conditional",
            "Preserve existing button structure",
        ],
    },
    # 9. Table gap / white lines between sections
    {
        "id": "outfix-009",
        "dimensions": {
            "issue_type": "table_gaps",
            "element": "table_spacing",
            "complexity": "standard",
        },
        "html_input": _TABLE_GAPS,
        "expected_challenges": [
            "Add cellpadding=0 cellspacing=0 to tables",
            "Add border-collapse:collapse",
            "Add mso-table-lspace:0pt; mso-table-rspace:0pt",
        ],
    },
    # 10. Image without HTML width/height attributes
    {
        "id": "outfix-010",
        "dimensions": {
            "issue_type": "image_sizing",
            "element": "image_attributes",
            "complexity": "standard",
        },
        "html_input": _IMG_NO_ATTRS,
        "expected_challenges": [
            "Add explicit width and height HTML attributes",
            "Add CSS width in pixels alongside percentage",
            "Preserve alt text and display:block",
        ],
    },
    # 11. Line height inconsistency
    {
        "id": "outfix-011",
        "dimensions": {
            "issue_type": "typography",
            "element": "line_height",
            "complexity": "standard",
        },
        "html_input": _LINE_HEIGHT,
        "expected_challenges": [
            "Add mso-line-height-rule: exactly to all line-height declarations",
            "Preserve existing line-height values",
        ],
    },
    # 12. Max-width without MSO wrapper
    {
        "id": "outfix-012",
        "dimensions": {
            "issue_type": "max_width",
            "element": "layout_constraint",
            "complexity": "standard",
        },
        "html_input": _MAX_WIDTH_NO_MSO,
        "expected_challenges": [
            "Add MSO conditional wrapper table with explicit width",
            "Preserve div-based centering for non-Outlook clients",
            "Set width=600 on MSO wrapper table",
        ],
    },
]
