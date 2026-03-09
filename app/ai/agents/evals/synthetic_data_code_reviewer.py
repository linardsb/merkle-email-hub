"""Synthetic test data for Code Reviewer agent evaluation.

12 test cases covering: redundant code, unsupported CSS, invalid nesting,
file size issues, and clean HTML (false positive testing).
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

CODE_REVIEWER_TEST_CASES: list[dict] = [  # type: ignore[type-arg]
    # --- Redundant Code Cases ---
    {
        "id": "cr-001",
        "focus": "redundant_code",
        "dimensions": {
            "issue_category": "redundant_inline_styles",
            "html_complexity": "multi_column_tables",
            "expected_severity": "warning_dominant",
            "file_size_scenario": "under_60kb",
        },
        "html_input": _wrap("""
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0">
  <tr>
    <td style="font-family:Arial,Helvetica,sans-serif; font-size:14px; color:#333333; line-height:1.5; padding:20px;">
      <p style="font-family:Arial,Helvetica,sans-serif; font-size:14px; color:#333333; line-height:1.5;">First paragraph</p>
      <p style="font-family:Arial,Helvetica,sans-serif; font-size:14px; color:#333333; line-height:1.5;">Second paragraph</p>
      <p style="font-family:Arial,Helvetica,sans-serif; font-size:14px; color:#333333; line-height:1.5;">Third paragraph</p>
    </td>
  </tr>
  <tr>
    <td style="font-family:Arial,Helvetica,sans-serif; font-size:14px; color:#333333; line-height:1.5; padding:20px;">
      <p style="font-family:Arial,Helvetica,sans-serif; font-size:14px; color:#333333; line-height:1.5;">More repeated styles</p>
    </td>
  </tr>
</table>"""),
        "expected_challenges": ["Detect repeated inline style blocks across siblings"],
    },
    {
        "id": "cr-002",
        "focus": "redundant_code",
        "dimensions": {
            "issue_category": "dead_mso_conditional",
            "html_complexity": "heavy_mso_conditionals",
            "expected_severity": "info_only",
            "file_size_scenario": "under_60kb",
        },
        "html_input": _wrap("""
<!--[if mso]>
<table role="presentation" width="600"><tr><td>
<![endif]-->
<table role="presentation" width="100%" style="max-width:600px;">
  <tr><td style="padding:20px;">Content here</td></tr>
</table>
<!--[if mso]></td></tr></table><![endif]-->

<!--[if mso]>

<![endif]-->

<!--[if gte mso 9]>
  <!--[if gte mso 9]>
    <table><tr><td>Nested same-version MSO</td></tr></table>
  <![endif]-->
<![endif]-->
"""),
        "expected_challenges": ["Detect empty MSO conditional", "Detect nested same-version MSO"],
    },
    {
        "id": "cr-003",
        "focus": "redundant_code",
        "dimensions": {
            "issue_category": "unused_css_class",
            "html_complexity": "simple_single_column",
            "expected_severity": "info_only",
            "file_size_scenario": "under_60kb",
        },
        "html_input": f"""{_VALID_HEAD.replace("</head>", "")}\
<style>
  .hero-title {{ font-size: 24px; }}
  .hero-subtitle {{ font-size: 16px; }}
  .cta-button {{ background-color: #007bff; }}
  .unused-class-a {{ color: red; }}
  .unused-class-b {{ margin: 10px; }}
</style>
</head>
{_VALID_BODY_OPEN}
<table role="presentation">
  <tr><td class="hero-title">Welcome</td></tr>
  <tr><td><a href="https://example.com" class="cta-button">Click</a></td></tr>
</table>
{_VALID_BODY_CLOSE}""",
        "expected_challenges": [
            "Detect unused CSS classes (unused-class-a, unused-class-b, hero-subtitle)"
        ],
    },
    # --- CSS Support Cases ---
    {
        "id": "cr-004",
        "focus": "css_support",
        "dimensions": {
            "issue_category": "unsupported_css_property",
            "html_complexity": "simple_single_column",
            "expected_severity": "critical_only",
            "file_size_scenario": "under_60kb",
        },
        "html_input": _wrap("""
<table role="presentation" width="600">
  <tr>
    <td style="display:flex; justify-content:space-between; align-items:center;">
      <div style="flex:1; padding:10px;">Column 1</div>
      <div style="flex:1; padding:10px;">Column 2</div>
    </td>
  </tr>
  <tr>
    <td style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
      <div>Grid item 1</div>
      <div>Grid item 2</div>
    </td>
  </tr>
</table>"""),
        "expected_challenges": ["Flag display:flex", "Flag display:grid", "Flag gap property"],
    },
    {
        "id": "cr-005",
        "focus": "css_support",
        "dimensions": {
            "issue_category": "unsupported_css_property",
            "html_complexity": "mixed_layout",
            "expected_severity": "mixed_severity",
            "file_size_scenario": "under_60kb",
        },
        "html_input": _wrap("""
<table role="presentation" width="600">
  <tr>
    <td style="border-radius:8px; box-shadow:0 2px 4px rgba(0,0,0,0.1); position:relative;">
      <img src="https://placehold.co/600x200" alt="Banner" width="600" height="200"
           style="display:block; object-fit:cover; clip-path:circle(50%);">
      <div style="position:absolute; top:10px; left:10px; background:var(--brand-color);">
        Overlay text with CSS custom property
      </div>
    </td>
  </tr>
  <tr>
    <td style="max-width:600px; margin:0 auto;">
      <p style="line-height:1.5">Text with unitless line-height</p>
    </td>
  </tr>
</table>"""),
        "expected_challenges": [
            "Flag position:absolute",
            "Flag object-fit",
            "Flag clip-path",
            "Flag var(--brand-color)",
            "Note border-radius partial support",
            "Note box-shadow partial support",
            "Note max-width needs MSO fallback",
        ],
    },
    # --- Nesting Cases ---
    {
        "id": "cr-006",
        "focus": "nesting",
        "dimensions": {
            "issue_category": "invalid_nesting",
            "html_complexity": "multi_column_tables",
            "expected_severity": "critical_only",
            "file_size_scenario": "under_60kb",
        },
        "html_input": _wrap("""
<table role="presentation" width="600">
  <td style="padding:20px;">Content without tr</td>
  <tr>
    <table role="presentation"><tr><td>Table directly in tr</td></tr></table>
  </tr>
  <tr>
    <td>
      <span><div>Block inside inline</div></span>
      <p>First paragraph<p>Nested paragraph (invalid)</p></p>
    </td>
  </tr>
</table>"""),
        "expected_challenges": [
            "Detect td outside tr",
            "Detect table directly in tr",
            "Detect div inside span",
            "Detect p inside p",
        ],
    },
    {
        "id": "cr-007",
        "focus": "nesting",
        "dimensions": {
            "issue_category": "excessive_table_depth",
            "html_complexity": "heavy_mso_conditionals",
            "expected_severity": "warning_dominant",
            "file_size_scenario": "under_60kb",
        },
        "html_input": _wrap("""
<table role="presentation"><tr><td>
  <table role="presentation"><tr><td>
    <table role="presentation"><tr><td>
      <table role="presentation"><tr><td>
        <table role="presentation"><tr><td>
          <table role="presentation"><tr><td>
            <table role="presentation"><tr><td>
              Deeply nested content (7 levels)
            </td></tr></table>
          </td></tr></table>
        </td></tr></table>
      </td></tr></table>
    </td></tr></table>
  </td></tr></table>
</td></tr></table>"""),
        "expected_challenges": ["Detect excessive table nesting depth (>6)"],
    },
    # --- File Size Cases ---
    {
        "id": "cr-008",
        "focus": "file_size",
        "dimensions": {
            "issue_category": "gmail_clip_risk",
            "html_complexity": "production_template",
            "expected_severity": "critical_only",
            "file_size_scenario": "over_102kb_clipping",
        },
        "html_input": _wrap(
            '<table role="presentation">'
            + "\n".join(
                f'<tr><td style="font-family:Arial,sans-serif; font-size:14px; color:#333; '
                f'line-height:1.5; padding:10px 20px;">Row {i} with enough content to bulk up the '
                f"file size past the Gmail clipping threshold. This is test content repeated to "
                f"create a realistically large email template. Lorem ipsum dolor sit amet.</td></tr>"
                for i in range(350)
            )
            + "</table>"
        ),
        "expected_challenges": ["Detect file size >102KB", "Suggest minification"],
    },
    {
        "id": "cr-009",
        "focus": "file_size",
        "dimensions": {
            "issue_category": "base64_embedded_image",
            "html_complexity": "simple_single_column",
            "expected_severity": "critical_only",
            "file_size_scenario": "bloated_base64",
        },
        "html_input": _wrap(f"""
<table role="presentation" width="600">
  <tr>
    <td>
      <img src="data:image/png;base64,{"A" * 5000}" alt="Embedded image" width="200" height="200">
      <p>Email with base64 embedded image</p>
    </td>
  </tr>
</table>"""),
        "expected_challenges": ["Detect base64 embedded image", "Suggest external hosting"],
    },
    # --- Mixed Issues Cases ---
    {
        "id": "cr-010",
        "focus": "all",
        "dimensions": {
            "issue_category": "mixed_issues",
            "html_complexity": "production_template",
            "expected_severity": "mixed_severity",
            "file_size_scenario": "near_threshold_80kb",
        },
        "html_input": _wrap("""
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0">
  <tr>
    <td style="display:flex; padding:20px; font-family:Arial,sans-serif;">
      <div style="font-family:Arial,sans-serif; color:#333;">
        <span><div>Nested block in inline</div></span>
      </div>
    </td>
  </tr>
  <tr>
    <td style="font-family:Arial,sans-serif; color:#333; padding:20px;">
      <p style="font-family:Arial,sans-serif; color:#333;">Repeated styles</p>
      <p style="font-family:Arial,sans-serif; color:#333;">Same styles again</p>
    </td>
  </tr>
</table>"""),
        "expected_challenges": [
            "Flag display:flex (critical)",
            "Detect div inside span (critical)",
            "Detect repeated inline styles (warning)",
        ],
    },
    # --- Clean HTML (False Positive Testing) ---
    {
        "id": "cr-011",
        "focus": "all",
        "dimensions": {
            "issue_category": "mixed_issues",
            "html_complexity": "production_template",
            "expected_severity": "clean_no_issues",
            "file_size_scenario": "under_60kb",
        },
        "html_input": f"""{_VALID_HEAD.replace("</head>", "")}\
<style>
  @media (prefers-color-scheme: dark) {{
    .dark-bg {{ background-color: #1a1a2e !important; }}
  }}
  [data-ogsc] .dark-text {{ color: #ffffff !important; }}
</style>
</head>
{_VALID_BODY_OPEN}
<!--[if mso]>
<table role="presentation" width="600" align="center"><tr><td>
<![endif]-->
<table role="presentation" width="100%" style="max-width:600px; margin:0 auto;">
  <tr>
    <td style="padding:20px; font-family:Arial,Helvetica,sans-serif; color:#333333;">
      <img src="https://placehold.co/600x200" alt="Spring collection banner showing new arrivals"
           width="600" height="200" style="display:block; width:100%; height:auto;">
      <h1 style="font-size:24px; margin:20px 0 10px;">Welcome to Our Store</h1>
      <p style="font-size:14px; line-height:22px;">Quality email template content.</p>
      <a href="https://example.com/shop" style="display:inline-block; padding:12px 24px;
         background-color:#007bff; color:#ffffff; text-decoration:none;
         mso-padding-alt:12px 24px;">Shop Now</a>
    </td>
  </tr>
</table>
<!--[if mso]></td></tr></table><![endif]-->
{_VALID_BODY_CLOSE}""",
        "expected_challenges": ["Clean HTML — should report zero or minimal issues (info only)"],
    },
    {
        "id": "cr-012",
        "focus": "all",
        "dimensions": {
            "issue_category": "mixed_issues",
            "html_complexity": "vml_elements_present",
            "expected_severity": "clean_no_issues",
            "file_size_scenario": "under_60kb",
        },
        "html_input": _wrap("""
<!--[if mso]>
<v:rect xmlns:v="urn:schemas-microsoft-com:vml" fill="true" stroke="false"
        style="width:600px; height:300px;">
  <v:fill type="frame" src="https://placehold.co/600x300" />
  <v:textbox inset="0,0,0,0">
<![endif]-->
<table role="presentation" width="600" style="background-image:url('https://placehold.co/600x300'); background-size:cover;">
  <tr>
    <td style="padding:40px; font-family:Arial,sans-serif; color:#ffffff;">
      <h1 style="font-size:28px; margin:0 0 10px;">VML Background Hero</h1>
      <p style="font-size:16px; line-height:24px;">Content over background image with Outlook VML fallback.</p>
    </td>
  </tr>
</table>
<!--[if mso]>
  </v:textbox>
</v:rect>
<![endif]-->"""),
        "expected_challenges": ["VML elements and MSO comments are valid — should NOT be flagged"],
    },
]
