"""Synthetic test data for Visual QA agent evaluation.

10 test cases covering rendering defect detection across email clients.
Each case simulates VLM analysis of screenshots (without actual images).
"""

# -- Base HTML fragments (reused across cases) --

_VALID_HEAD = """\
<!DOCTYPE html>
<html lang="en" xmlns:v="urn:schemas-microsoft-com:vml">
<head>
<meta charset="utf-8">
<meta name="color-scheme" content="light dark">
<title>Test Email</title>
</head>"""

_VALID_BODY_OPEN = '<body style="margin:0; padding:0; background-color:#ffffff;">'
_VALID_BODY_CLOSE = "</body></html>"


def _wrap(body_content: str, head: str = _VALID_HEAD) -> str:
    return f"{head}\n{_VALID_BODY_OPEN}\n{body_content}\n{_VALID_BODY_CLOSE}"


# -- Test Cases --

VISUAL_QA_TEST_CASES: list[dict] = [  # type: ignore[type-arg]
    # 1. Perfect rendering — no defects expected
    {
        "id": "vqa-001",
        "scenario": "perfect_rendering",
        "dimensions": {
            "defect_type": "none",
            "client_coverage": "full",
            "expected_severity": "none",
        },
        "html_input": _wrap("""
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" align="center">
  <tr>
    <td style="padding:20px; font-family:Arial,sans-serif; font-size:16px; color:#333333;">
      <h1 style="margin:0 0 16px; font-size:24px;">Welcome</h1>
      <p style="margin:0 0 16px;">Simple table-based email with inline styles.</p>
      <a href="https://example.com" style="display:inline-block; padding:12px 24px; background-color:#0066cc; color:#ffffff; text-decoration:none; font-weight:bold;">Click Here</a>
    </td>
  </tr>
</table>"""),
        "clients": ["gmail_web", "outlook_2019", "apple_mail"],
        "expected_challenges": [
            "No defects — this is a well-formed table-based email with inline styles",
            "Agent should report overall_rendering_score close to 1.0",
            "Agent should report zero or near-zero defects",
        ],
    },
    # 2. Outlook flexbox collapse (critical)
    {
        "id": "vqa-002",
        "scenario": "outlook_flexbox_collapse",
        "dimensions": {
            "defect_type": "layout_collapse",
            "client_coverage": "outlook_specific",
            "expected_severity": "critical",
        },
        "html_input": _wrap("""
<div style="display:flex; justify-content:space-between; max-width:600px; margin:0 auto;">
  <div style="flex:1; padding:20px;">
    <h2>Column 1</h2>
    <p>Content for the first column.</p>
  </div>
  <div style="flex:1; padding:20px;">
    <h2>Column 2</h2>
    <p>Content for the second column.</p>
  </div>
  <div style="flex:1; padding:20px;">
    <h2>Column 3</h2>
    <p>Content for the third column.</p>
  </div>
</div>"""),
        "clients": ["gmail_web", "outlook_2019", "apple_mail"],
        "expected_challenges": [
            "Outlook 2019 does not support flexbox — columns will stack vertically",
            "Agent should detect layout collapse in Outlook screenshot",
            "Fix should suggest table-based layout replacement",
            "Severity should be critical for Outlook",
        ],
    },
    # 3. Gmail style stripping (critical)
    {
        "id": "vqa-003",
        "scenario": "gmail_style_stripping",
        "dimensions": {
            "defect_type": "style_loss",
            "client_coverage": "gmail_specific",
            "expected_severity": "critical",
        },
        "html_input": (
            "<!DOCTYPE html><html><head><style>"
            ".header { background-color: #0066cc; color: white; padding: 40px; text-align: center; }"
            ".content { padding: 20px; font-family: Arial; }"
            ".cta { background-color: #ff6600; color: white; padding: 15px 30px; border-radius: 5px; }"
            "</style></head><body>"
            '<div class="header"><h1>Newsletter</h1></div>'
            '<div class="content"><p>Content here</p>'
            '<a href="#" class="cta">Buy Now</a></div>'
            "</body></html>"
        ),
        "clients": ["gmail_web", "outlook_2019", "apple_mail"],
        "expected_challenges": [
            "Gmail strips <style> blocks — all class-based styling will be lost",
            "Header background color, CTA styling will disappear in Gmail",
            "Fix should suggest inlining all CSS styles",
            "Severity should be critical for Gmail",
        ],
    },
    # 4. Dark mode logo inversion (warning)
    {
        "id": "vqa-004",
        "scenario": "dark_mode_inversion",
        "dimensions": {
            "defect_type": "color_inversion",
            "client_coverage": "dark_mode_clients",
            "expected_severity": "warning",
        },
        "html_input": _wrap("""
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" align="center">
  <tr>
    <td style="background-color:#ffffff; padding:20px; text-align:center;">
      <img src="https://example.com/logo-dark-text.png" alt="Brand" width="200" style="display:block; margin:0 auto;">
    </td>
  </tr>
  <tr>
    <td style="padding:20px; color:#333333; font-family:Arial,sans-serif;">
      <p>Dark text on white background with a dark logo.</p>
    </td>
  </tr>
</table>"""),
        "clients": ["gmail_web", "outlook_dark", "apple_mail"],
        "expected_challenges": [
            "Dark mode clients may invert the dark-text logo making it invisible",
            "Background inversion makes dark text hard to read",
            "Fix should suggest data-ogsc/data-ogsb attributes or transparent PNG with light version",
            "Severity should be warning (content still present but hard to read)",
        ],
    },
    # 5. Responsive layout break on mobile (critical)
    {
        "id": "vqa-005",
        "scenario": "responsive_breakage",
        "dimensions": {
            "defect_type": "responsive_failure",
            "client_coverage": "mobile_clients",
            "expected_severity": "critical",
        },
        "html_input": _wrap("""
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0">
  <tr>
    <td width="300" style="padding:10px;">
      <img src="https://example.com/hero.jpg" width="280" style="display:block;">
    </td>
    <td width="300" style="padding:10px; font-family:Arial,sans-serif;">
      <h2>Product Feature</h2>
      <p>Detailed description of the product feature that spans multiple lines.</p>
      <a href="#" style="display:inline-block; padding:10px 20px; background:#0066cc; color:#fff;">Learn More</a>
    </td>
  </tr>
</table>"""),
        "clients": ["gmail_web", "apple_mail", "ios_mail"],
        "expected_challenges": [
            "Fixed 600px width table overflows on mobile screens",
            "No media queries for responsive stacking",
            "Content may be cut off or require horizontal scrolling on mobile",
            "Severity should be critical for mobile clients",
        ],
    },
    # 6. Font fallback visible (info)
    {
        "id": "vqa-006",
        "scenario": "font_fallback",
        "dimensions": {
            "defect_type": "font_rendering",
            "client_coverage": "full",
            "expected_severity": "info",
        },
        "html_input": _wrap("""
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" align="center">
  <tr>
    <td style="padding:20px; font-family:'Playfair Display',Georgia,serif; font-size:32px; color:#333;">
      <h1 style="margin:0;">Elegant Heading</h1>
    </td>
  </tr>
  <tr>
    <td style="padding:0 20px 20px; font-family:'Montserrat',Arial,sans-serif; font-size:16px; color:#666;">
      <p>Body text in a custom web font that may not be available in all clients.</p>
    </td>
  </tr>
</table>"""),
        "clients": ["gmail_web", "outlook_2019", "apple_mail"],
        "expected_challenges": [
            "Custom web fonts (Playfair Display, Montserrat) not available in Outlook",
            "Fallback to Georgia/Arial is expected and acceptable",
            "Severity should be info — this is cosmetic, not broken",
            "Agent should NOT flag this as critical or warning",
        ],
    },
    # 7. Border-radius not rendering in Outlook (warning)
    {
        "id": "vqa-007",
        "scenario": "outlook_border_radius",
        "dimensions": {
            "defect_type": "css_unsupported",
            "client_coverage": "outlook_specific",
            "expected_severity": "warning",
        },
        "html_input": _wrap("""
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" align="center">
  <tr>
    <td style="padding:30px; text-align:center;">
      <a href="https://example.com" style="display:inline-block; padding:16px 32px; background-color:#ff6600; color:#ffffff; text-decoration:none; font-family:Arial,sans-serif; font-weight:bold; border-radius:8px;">
        Shop Now
      </a>
    </td>
  </tr>
  <tr>
    <td style="padding:20px;">
      <div style="background:#f5f5f5; border-radius:12px; padding:20px;">
        <p style="font-family:Arial,sans-serif; margin:0;">Card content with rounded corners</p>
      </div>
    </td>
  </tr>
</table>"""),
        "clients": ["gmail_web", "outlook_2019", "apple_mail"],
        "expected_challenges": [
            "Outlook 2019 ignores border-radius — buttons and cards will have square corners",
            "Fix should suggest VML roundrect for the CTA button",
            "Severity should be warning (functional but visually degraded)",
            "css_property should be border-radius",
        ],
    },
    # 8. Image sizing issues across clients (warning)
    {
        "id": "vqa-008",
        "scenario": "image_sizing",
        "dimensions": {
            "defect_type": "image_rendering",
            "client_coverage": "full",
            "expected_severity": "warning",
        },
        "html_input": _wrap("""
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" align="center">
  <tr>
    <td style="padding:0;">
      <img src="https://example.com/hero-2x.jpg" style="display:block; max-width:100%;" alt="Hero banner">
    </td>
  </tr>
  <tr>
    <td style="padding:20px;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td width="50%"><img src="https://example.com/product1.jpg" style="width:100%;" alt="Product 1"></td>
          <td width="50%"><img src="https://example.com/product2.jpg" style="width:100%;" alt="Product 2"></td>
        </tr>
      </table>
    </td>
  </tr>
</table>"""),
        "clients": ["gmail_web", "outlook_2019", "apple_mail"],
        "expected_challenges": [
            "Missing explicit width/height attributes on images",
            "Outlook may not respect max-width:100% or width:100% on images",
            "Retina images (2x) may display at full resolution in some clients",
            "Fix should suggest adding explicit width/height attributes",
        ],
    },
    # 9. Multiple concurrent defects (critical + warning)
    {
        "id": "vqa-009",
        "scenario": "multiple_defects",
        "dimensions": {
            "defect_type": "mixed",
            "client_coverage": "full",
            "expected_severity": "critical_and_warning",
        },
        "html_input": (
            "<!DOCTYPE html><html><head><style>"
            ".wrapper { display: flex; max-width: 600px; }"
            ".col { flex: 1; padding: 20px; }"
            ".btn { border-radius: 25px; padding: 15px; background: #0066cc; color: white; }"
            "</style></head><body>"
            '<div class="wrapper">'
            '<div class="col"><h2>Left</h2><p>Content</p></div>'
            '<div class="col"><h2>Right</h2><a href="#" class="btn">CTA</a></div>'
            "</div></body></html>"
        ),
        "clients": ["gmail_web", "outlook_2019", "apple_mail"],
        "expected_challenges": [
            "Gmail: style block stripped — all class-based styling lost (critical)",
            "Outlook: flexbox not supported — layout collapses (critical)",
            "Outlook: border-radius on CTA ignored (warning)",
            "Agent should detect multiple defects across different clients",
            "overall_rendering_score should be low (< 0.5)",
        ],
    },
    # 10. VML background not rendering (critical)
    {
        "id": "vqa-010",
        "scenario": "vml_background_failure",
        "dimensions": {
            "defect_type": "vml_rendering",
            "client_coverage": "outlook_specific",
            "expected_severity": "critical",
        },
        "html_input": _wrap("""
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" align="center">
  <tr>
    <td>
      <!--[if mso]>
      <v:rect xmlns:v="urn:schemas-microsoft-com:vml" fill="true" stroke="false" style="width:600px;height:300px;">
        <v:fill type="tile" src="https://example.com/bg-pattern.jpg" color="#0066cc"/>
        <v:textbox style="mso-fit-shape-to-text:true" inset="20px,20px,20px,20px">
      <![endif]-->
      <div style="background-image:url('https://example.com/bg-pattern.jpg'); background-color:#0066cc; background-size:cover; padding:60px 20px; text-align:center;">
        <h1 style="color:#ffffff; font-family:Arial,sans-serif; font-size:28px; margin:0;">Hero Section</h1>
        <p style="color:#ffffff; font-family:Arial,sans-serif; font-size:16px;">With background image</p>
      </div>
      <!--[if mso]>
        </v:textbox>
      </v:rect>
      <![endif]-->
    </td>
  </tr>
</table>"""),
        "clients": ["gmail_web", "outlook_2019", "apple_mail"],
        "expected_challenges": [
            "VML background may not render if image URL is broken or blocked",
            "Outlook uses VML for background images — verify v:rect renders correctly",
            "Background-color fallback should be visible if image fails",
            "Agent should verify VML markup is complete and well-formed",
        ],
    },
]
