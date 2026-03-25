"""Synthetic test data for the Accessibility Auditor agent.

Each test case provides HTML with specific accessibility violations.
The agent must fix the violations while preserving visual design.
"""

# Minimal email HTML base — each test case inserts specific violations
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

# 1. Missing alt text on multiple images (informative + decorative)
_MISSING_ALT_TEXT = _BASE_HTML.format(
    body_content="""\
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0">
  <tr>
    <td style="padding:20px; font-family:Arial,sans-serif;">
      <img src="https://placehold.co/600x200" width="600" height="200"
        style="display:block; width:100%; height:auto;">
      <h1>Spring Collection Launch</h1>
      <p>Discover our newest arrivals for the season.</p>
      <img src="https://placehold.co/200x200" width="200" height="200"
        style="display:block;">
      <img src="https://placehold.co/1x20"
        style="display:block; width:100%; height:20px;">
    </td>
  </tr>
</table>"""
)

# 2. Layout tables without role="presentation"
_TABLES_NO_ROLE = _BASE_HTML.format(
    body_content="""\
<table width="600" align="center" cellpadding="0" cellspacing="0">
  <tr>
    <td style="padding:20px; font-family:Arial,sans-serif;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td width="50%" style="padding:10px;">
            <h2>Left Column</h2>
            <p>Content for the left side.</p>
          </td>
          <td width="50%" style="padding:10px;">
            <h2>Right Column</h2>
            <p>Content for the right side.</p>
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>"""
)

# 3. Missing lang attribute on <html> + no <title>
_NO_LANG_NO_TITLE = """\
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0; padding:0; background-color:#ffffff;">
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0">
  <tr>
    <td style="padding:20px; font-family:Arial,sans-serif;">
      <img src="https://placehold.co/600x200" alt="Welcome banner" width="600" height="200"
        style="display:block; width:100%; height:auto;">
      <h1>Welcome to Our Newsletter</h1>
      <p>Stay updated with the latest news and offers.</p>
    </td>
  </tr>
</table>
</body>
</html>"""

# 4. Low contrast text (#999 on #fff = ~2.8:1, below 4.5:1)
_LOW_CONTRAST = _BASE_HTML.format(
    body_content="""\
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0">
  <tr>
    <td style="padding:20px; font-family:Arial,sans-serif; background-color:#ffffff;">
      <h1 style="color:#333333;">Important Update</h1>
      <p style="color:#999999; font-size:14px;">This paragraph text has insufficient
        contrast against the white background. The ratio is approximately 2.8:1
        which fails WCAG AA for normal text.</p>
      <p style="color:#aaaaaa; font-size:12px;">This smaller text is even worse
        at roughly 2.3:1 contrast ratio.</p>
      <a href="https://example.com" style="color:#88bbdd; text-decoration:none;">
        Read more about our changes</a>
    </td>
  </tr>
</table>"""
)

# 5. Skipped heading levels (h1 → h3 → h5)
_SKIPPED_HEADINGS = _BASE_HTML.format(
    body_content="""\
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0">
  <tr>
    <td style="padding:20px; font-family:Arial,sans-serif;">
      <h1>Company Newsletter</h1>
      <p>Welcome to our monthly roundup.</p>
      <h3>Featured Products</h3>
      <p>Check out what's new this month.</p>
      <h5>Product Details</h5>
      <p>Our flagship product is now available in new colors.</p>
      <h3>Upcoming Events</h3>
      <p>Join us for these exciting activities.</p>
    </td>
  </tr>
</table>"""
)

# 6. Non-descriptive links ("click here", "read more")
_BAD_LINK_TEXT = _BASE_HTML.format(
    body_content="""\
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0">
  <tr>
    <td style="padding:20px; font-family:Arial,sans-serif;">
      <h1>Monthly Newsletter</h1>
      <p>We have exciting news! <a href="https://example.com/news"
        style="color:#007bff;">Click here</a> to learn more.</p>
      <p>Our new product line is launching next week.
        <a href="https://example.com/products" style="color:#007bff;">Read more</a></p>
      <p>For details about our return policy,
        <a href="https://example.com/returns" style="color:#007bff;">here</a>.</p>
      <p><a href="https://example.com/unsubscribe"
        style="color:#007bff;">Click here to unsubscribe</a></p>
    </td>
  </tr>
</table>"""
)

# 7. Complex multi-column with MSO conditionals, all issues combined
_COMPLEX_ALL_ISSUES = """\
<!DOCTYPE html>
<html xmlns:v="urn:schemas-microsoft-com:vml">
<head>
<meta charset="utf-8">
</head>
<body style="margin:0; padding:0; background-color:#ffffff;">
<!--[if mso]>
<table width="600" align="center"><tr><td>
<![endif]-->
<table width="600" align="center" cellpadding="0" cellspacing="0">
  <tr>
    <td style="background-color:#f0f0f0; padding:20px; font-family:Arial,sans-serif;">
      <img src="https://placehold.co/600x100" width="600" height="100"
        style="display:block; width:100%;">
      <h1 style="color:#333333;">Summer Sale</h1>
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td width="50%" style="padding:10px; vertical-align:top;">
            <h4>Category One</h4>
            <p style="color:#999999; font-size:13px;">Browse our selection of items
              in this category.</p>
            <a href="https://example.com/cat1" style="color:#007bff;">Click here</a>
          </td>
          <td width="50%" style="padding:10px; vertical-align:top;">
            <img src="https://placehold.co/250x250" width="250" height="250">
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>
<!--[if mso]></td></tr></table><![endif]-->
</body>
</html>"""

# 8. Functional images (linked images with no alt)
_FUNCTIONAL_IMAGES = _BASE_HTML.format(
    body_content="""\
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0">
  <tr>
    <td style="padding:20px; font-family:Arial,sans-serif;">
      <a href="https://example.com/home">
        <img src="https://placehold.co/200x60" width="200" height="60"
          style="display:block;">
      </a>
      <h1>Check Out Our Deals</h1>
      <a href="https://example.com/sale">
        <img src="https://placehold.co/600x300" width="600" height="300"
          style="display:block; width:100%; height:auto;">
      </a>
      <p>Don't miss out on these limited-time offers.</p>
      <a href="https://facebook.com/example">
        <img src="https://placehold.co/32x32" width="32" height="32">
      </a>
      <a href="https://twitter.com/example">
        <img src="https://placehold.co/32x32" width="32" height="32">
      </a>
    </td>
  </tr>
</table>"""
)

# 9. VML elements present, tables mixed layout+data, ARIA missing
_VML_MIXED_TABLES = """\
<!DOCTYPE html>
<html lang="en" xmlns:v="urn:schemas-microsoft-com:vml">
<head>
<meta charset="utf-8">
<title>Test Email</title>
</head>
<body style="margin:0; padding:0; background-color:#ffffff;">
<table width="600" align="center" cellpadding="0" cellspacing="0">
  <tr>
    <td style="padding:20px; font-family:Arial,sans-serif;">
      <!--[if mso]>
      <v:rect style="width:600px; height:200px;" fillcolor="#007bff" stroked="false">
      <v:textbox inset="20px,20px,20px,20px">
      <![endif]-->
      <div style="background-color:#007bff; padding:20px; color:#ffffff;">
        <h1>Featured Content</h1>
      </div>
      <!--[if mso]></v:textbox></v:rect><![endif]-->
      <table width="100%" cellpadding="5" cellspacing="0" border="1">
        <tr>
          <th>Product</th>
          <th>Price</th>
          <th>Rating</th>
        </tr>
        <tr>
          <td>Widget A</td>
          <td>$29.99</td>
          <td>4.5/5</td>
        </tr>
        <tr>
          <td>Widget B</td>
          <td>$39.99</td>
          <td>4.2/5</td>
        </tr>
      </table>
    </td>
  </tr>
</table>
</body>
</html>"""

# 10. Color-only information (red/green status indicators)
_COLOR_ONLY_INFO = _BASE_HTML.format(
    body_content="""\
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0">
  <tr>
    <td style="padding:20px; font-family:Arial,sans-serif;">
      <h1>Order Status Update</h1>
      <table role="presentation" width="100%" cellpadding="10" cellspacing="0">
        <tr>
          <td>Order #12345</td>
          <td style="color:#00cc00; font-weight:bold;">Delivered</td>
        </tr>
        <tr>
          <td>Order #12346</td>
          <td style="color:#ff0000; font-weight:bold;">Cancelled</td>
        </tr>
        <tr>
          <td>Order #12347</td>
          <td style="color:#ff9900; font-weight:bold;">Processing</td>
        </tr>
      </table>
      <p style="font-size:12px; color:#666666;">Status is indicated by color.</p>
    </td>
  </tr>
</table>"""
)


# 11. Logo images with company name — should use name only, never "logo image"
_LOGO_WITH_TEXT = _BASE_HTML.format(
    body_content="""\
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0">
  <tr>
    <td style="padding:20px; font-family:Arial,sans-serif;">
      <a href="https://example.com">
        <img src="https://placehold.co/200x60" width="200" height="60"
          alt="Acme Corp logo image" style="display:block;">
      </a>
      <h1>Welcome to Our Newsletter</h1>
      <p>Your weekly dose of inspiration and deals.</p>
      <img src="https://placehold.co/100x40" width="100" height="40"
        alt="Image of Partner Inc logo" style="display:inline;">
      <p>In partnership with Partner Inc.</p>
    </td>
  </tr>
</table>"""
)

# 12. Complex infographic / chart that needs aria-describedby
_COMPLEX_INFOGRAPHIC = _BASE_HTML.format(
    body_content="""\
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0">
  <tr>
    <td style="padding:20px; font-family:Arial,sans-serif;">
      <h1>Q3 Performance Report</h1>
      <img src="https://placehold.co/600x400" width="600" height="400"
        style="display:block; width:100%; height:auto;">
      <p>Revenue grew 15% quarter-over-quarter, driven by expansion in EMEA.</p>
      <img src="https://placehold.co/600x300" width="600" height="300"
        alt="data table" style="display:block; width:100%; height:auto;">
      <p>Customer satisfaction scores improved across all regions.</p>
    </td>
  </tr>
</table>"""
)

# 13. Decorative images with wrong (non-empty) alt text
_DECORATIVE_WRONG_ALT = _BASE_HTML.format(
    body_content="""\
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0">
  <tr>
    <td style="padding:20px; font-family:Arial,sans-serif;">
      <img src="https://placehold.co/600x20/spacer.gif" width="600" height="20"
        alt="spacer image" style="display:block;">
      <h1>Important Announcement</h1>
      <p>We have exciting news to share with you.</p>
      <img src="https://placehold.co/600x2/divider.png" width="600" height="2"
        alt="divider" style="display:block;">
      <p>More details coming soon.</p>
      <img src="https://placehold.co/1x1/tracking.gif" width="1" height="1"
        alt="tracking" style="display:none;">
      <img src="https://placehold.co/600x3/border.png" width="600" height="3"
        alt="decorative border line" style="display:block;">
    </td>
  </tr>
</table>"""
)

# 14. Missing landmark roles + generic alt text
_MISSING_LANDMARKS = _BASE_HTML.format(
    body_content="""\
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0">
  <tr>
    <td style="padding:10px; font-family:Arial,sans-serif; background-color:#f5f5f5;">
      <img src="https://placehold.co/150x50" width="150" height="50"
        alt="image" style="display:block;">
    </td>
  </tr>
  <tr>
    <td style="padding:20px; font-family:Arial,sans-serif;">
      <h1>Monthly Newsletter</h1>
      <img src="https://placehold.co/600x300" width="600" height="300"
        alt="photo" style="display:block; width:100%; height:auto;">
      <p>This month we're thrilled to share our latest updates.</p>
    </td>
  </tr>
  <tr>
    <td style="padding:10px; font-family:Arial,sans-serif; font-size:12px; color:#666666;">
      <p>© 2024 Example Corp. All rights reserved.</p>
      <a href="https://example.com/unsubscribe">Unsubscribe</a>
    </td>
  </tr>
</table>"""
)


# ── Test Cases ──

ACCESSIBILITY_TEST_CASES: list[dict[str, object]] = [
    # 1. Missing alt text on multiple images
    {
        "id": "a11y-001",
        "dimensions": {
            "violation_category": "missing_alt_text",
            "html_complexity": "simple_single_column",
            "image_scenario": "informative_no_alt",
            "severity": "multiple_moderate",
        },
        "html_input": _MISSING_ALT_TEXT,
        "expected_challenges": [
            "Add descriptive alt text to informative hero image",
            "Add descriptive alt text to product image",
            "Add empty alt='' to decorative spacer image",
            "Distinguish informative from decorative images",
        ],
    },
    # 2. Layout tables without role="presentation"
    {
        "id": "a11y-002",
        "dimensions": {
            "violation_category": "layout_table_no_role",
            "html_complexity": "multi_column_tables",
            "image_scenario": "no_images",
            "severity": "multiple_moderate",
        },
        "html_input": _TABLES_NO_ROLE,
        "expected_challenges": [
            "Add role='presentation' to outer layout table",
            "Add role='presentation' to inner layout table",
            "Preserve table structure and widths",
        ],
    },
    # 3. Missing lang attribute and title
    {
        "id": "a11y-003",
        "dimensions": {
            "violation_category": "missing_lang_attribute",
            "html_complexity": "simple_single_column",
            "image_scenario": "informative_no_alt",
            "severity": "single_critical",
        },
        "html_input": _NO_LANG_NO_TITLE,
        "expected_challenges": [
            "Add lang='en' attribute to <html> element",
            "Add <title> element in <head>",
            "Preserve all existing structure and content",
        ],
    },
    # 4. Low contrast text
    {
        "id": "a11y-004",
        "dimensions": {
            "violation_category": "low_contrast_text",
            "html_complexity": "simple_single_column",
            "image_scenario": "no_images",
            "severity": "mixed_severity",
        },
        "html_input": _LOW_CONTRAST,
        "expected_challenges": [
            "Fix #999999 on #ffffff (2.8:1 → need 4.5:1)",
            "Fix #aaaaaa on #ffffff (2.3:1 → need 4.5:1)",
            "Fix #88bbdd link on #ffffff",
            "Maintain visual hierarchy while improving contrast",
        ],
    },
    # 5. Skipped heading levels
    {
        "id": "a11y-005",
        "dimensions": {
            "violation_category": "skipped_heading_levels",
            "html_complexity": "simple_single_column",
            "image_scenario": "no_images",
            "severity": "multiple_moderate",
        },
        "html_input": _SKIPPED_HEADINGS,
        "expected_challenges": [
            "Fix h1 → h3 gap (should be h1 → h2)",
            "Fix h3 → h5 gap (should be h2 → h3)",
            "Maintain visual appearance via inline styles if needed",
            "Keep consistent heading style hierarchy",
        ],
    },
    # 6. Non-descriptive link text
    {
        "id": "a11y-006",
        "dimensions": {
            "violation_category": "non_descriptive_links",
            "html_complexity": "simple_single_column",
            "image_scenario": "no_images",
            "severity": "many_minor",
        },
        "html_input": _BAD_LINK_TEXT,
        "expected_challenges": [
            "Replace 'Click here' with descriptive link text",
            "Replace 'Read more' with descriptive link text",
            "Replace bare 'here' with descriptive link text",
            "Preserve link URLs and styling",
        ],
    },
    # 7. Complex multi-column with all issues combined
    {
        "id": "a11y-007",
        "dimensions": {
            "violation_category": "missing_alt_text",
            "html_complexity": "mso_conditional_heavy",
            "image_scenario": "informative_no_alt",
            "severity": "mixed_severity",
        },
        "html_input": _COMPLEX_ALL_ISSUES,
        "expected_challenges": [
            "Add lang attribute to <html>",
            "Add <title> to <head>",
            "Add role='presentation' to layout tables",
            "Add alt text to images",
            "Fix low contrast #999999 text",
            "Fix 'Click here' link text",
            "Fix heading hierarchy (h1 → h4 skip)",
            "Preserve MSO conditionals",
        ],
    },
    # 8. Functional images (linked images with no alt)
    {
        "id": "a11y-008",
        "dimensions": {
            "violation_category": "missing_alt_text",
            "html_complexity": "simple_single_column",
            "image_scenario": "functional_link_image",
            "severity": "multiple_moderate",
        },
        "html_input": _FUNCTIONAL_IMAGES,
        "expected_challenges": [
            "Add alt text describing logo link destination",
            "Add alt text for sale banner describing action",
            "Add alt text for social media icons describing platform",
            "Functional images must describe action, not image content",
        ],
    },
    # 9. VML elements, mixed layout+data tables, ARIA
    {
        "id": "a11y-009",
        "dimensions": {
            "violation_category": "missing_table_role",
            "html_complexity": "vml_elements_present",
            "image_scenario": "no_images",
            "severity": "mixed_severity",
        },
        "html_input": _VML_MIXED_TABLES,
        "expected_challenges": [
            "Add role='presentation' to outer layout table",
            "Keep data table semantic (no role='presentation')",
            "Ensure data table has proper scope attributes on th",
            "Preserve VML inside MSO conditionals",
            "VML must be ignored by screen readers",
        ],
    },
    # 10. Color-only information
    {
        "id": "a11y-010",
        "dimensions": {
            "violation_category": "color_only_information",
            "html_complexity": "simple_single_column",
            "image_scenario": "no_images",
            "severity": "multiple_moderate",
        },
        "html_input": _COLOR_ONLY_INFO,
        "expected_challenges": [
            "Add non-color indicator for Delivered status (e.g., checkmark)",
            "Add non-color indicator for Cancelled status (e.g., X symbol)",
            "Add non-color indicator for Processing status (e.g., clock symbol)",
            "Preserve existing color coding as supplementary cue",
            "Ensure status text is readable without color perception",
        ],
    },
    # 11. Logo images with text — agent should use company name only as alt
    {
        "id": "a11y-011",
        "dimensions": {
            "violation_category": "missing_alt_text",
            "html_complexity": "simple_single_column",
            "image_scenario": "logo_with_text",
            "severity": "multiple_moderate",
        },
        "html_input": _LOGO_WITH_TEXT,
        "expected_challenges": [
            "Logo alt should be company name only, not 'Acme Corp logo image'",
            "Alt text must not start with 'Image of' or 'Logo of'",
            "Secondary logo should also follow logo classification rules",
            "Preserve visual layout of logos alongside text",
        ],
    },
    # 12. Complex infographic needing aria-describedby pattern
    {
        "id": "a11y-012",
        "dimensions": {
            "violation_category": "missing_alt_text",
            "html_complexity": "simple_single_column",
            "image_scenario": "complex_infographic",
            "severity": "mixed_severity",
        },
        "html_input": _COMPLEX_INFOGRAPHIC,
        "expected_challenges": [
            "Add brief alt text summarising chart conclusion",
            "Add aria-describedby linking to detailed text description",
            "Create visually hidden description div for screen readers",
            "Data table image needs full data in accessible text",
        ],
    },
    # 13. Decorative images with wrong non-empty alt text
    {
        "id": "a11y-013",
        "dimensions": {
            "violation_category": "decorative_img_no_empty_alt",
            "html_complexity": "simple_single_column",
            "image_scenario": "decorative_missing_empty_alt",
            "severity": "many_minor",
        },
        "html_input": _DECORATIVE_WRONG_ALT,
        "expected_challenges": [
            "Convert spacer alt='spacer image' to alt=''",
            "Convert divider alt='divider' to alt=''",
            "Convert tracking pixel alt='tracking' to alt=''",
            "Identify border images as decorative and empty their alt",
        ],
    },
    # 14. Missing landmark roles + generic alt text
    {
        "id": "a11y-014",
        "dimensions": {
            "violation_category": "landmark_roles",
            "html_complexity": "simple_single_column",
            "image_scenario": "informative_no_alt",
            "severity": "mixed_severity",
        },
        "html_input": _MISSING_LANDMARKS,
        "expected_challenges": [
            "Add role='banner' to header section",
            "Add role='main' to primary content area",
            "Add role='contentinfo' to footer section",
            "Fix generic alt text 'image' and 'photo' on content images",
        ],
    },
]
