"""Synthetic test data for the Personalisation agent evaluation.

12 test cases: 4 per ESP platform x varying complexity.
Each case exercises a different combination of variable complexity,
conditional logic, and fallback handling.
"""

from typing import Any

_BASE_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="color-scheme" content="light dark">
<title>Email</title>
<style>
  body {{ margin: 0; padding: 0; background-color: #f5f5f5; }}
  .container {{ max-width: 600px; margin: 0 auto; background-color: #ffffff; }}
</style>
</head>
<body>
<!--[if mso]><table role="presentation" width="600" align="center"><tr><td><![endif]-->
<table role="presentation" class="container" width="100%">
{body_content}
</table>
<!--[if mso]></td></tr></table><![endif]-->
</body>
</html>"""

# ---------------------------------------------------------------------------
# Body content fixtures — realistic email sections with static placeholders
# ---------------------------------------------------------------------------

_GREETING_ROW = """\
<tr>
  <td style="padding: 20px; font-family: Arial, sans-serif; font-size: 16px; color: #333333;">
    <h1 style="margin: 0 0 10px;">Hi Friend,</h1>
    <p>Welcome to our latest newsletter. We have exciting updates for you.</p>
  </td>
</tr>"""

_VIP_SECTIONS = """\
<tr>
  <td style="padding: 20px; font-family: Arial, sans-serif;">
    <h1 style="margin: 0 0 10px;">Hello Customer,</h1>
    <p>Thank you for being a valued member.</p>
  </td>
</tr>
<tr>
  <td style="padding: 20px; background-color: #ffd700; font-family: Arial, sans-serif;">
    <h2 style="margin: 0 0 8px;">VIP Exclusive Offer</h2>
    <p>As a premium member, enjoy 30% off your next purchase.</p>
    <a href="https://example.com/vip" style="display: inline-block; padding: 12px 24px; background-color: #333; color: #fff; text-decoration: none;">Shop VIP</a>
  </td>
</tr>
<tr>
  <td style="padding: 20px; font-family: Arial, sans-serif;">
    <h2 style="margin: 0 0 8px;">Standard Offer</h2>
    <p>Check out our latest collection with free shipping on orders over $50.</p>
    <a href="https://example.com/shop" style="display: inline-block; padding: 12px 24px; background-color: #007bff; color: #fff; text-decoration: none;">Shop Now</a>
  </td>
</tr>"""

_PRODUCT_GRID = """\
<tr>
  <td style="padding: 20px; font-family: Arial, sans-serif;">
    <h2 style="margin: 0 0 12px;">Recommended For You</h2>
  </td>
</tr>
<tr>
  <td style="padding: 0 20px;">
    <table role="presentation" width="100%">
      <tr>
        <td width="50%" style="padding: 8px;">
          <img src="https://example.com/product1.jpg" alt="Product 1" width="260" style="display: block;">
          <p style="font-family: Arial, sans-serif; font-size: 14px;">Product Name - $29.99</p>
        </td>
        <td width="50%" style="padding: 8px;">
          <img src="https://example.com/product2.jpg" alt="Product 2" width="260" style="display: block;">
          <p style="font-family: Arial, sans-serif; font-size: 14px;">Product Name - $39.99</p>
        </td>
      </tr>
    </table>
  </td>
</tr>"""

_CONTENT_BLOCK_ROW = """\
<tr>
  <td style="padding: 20px; font-family: Arial, sans-serif;">
    <h2 style="margin: 0 0 10px;">Weekly Digest</h2>
    <p>Published on January 15, 2026</p>
    <div style="border-top: 1px solid #eee; padding-top: 12px; margin-top: 12px;">
      <p>This week's top stories and editor picks curated just for you.</p>
    </div>
  </td>
</tr>"""

_SUBSCRIBER_GREETING = """\
<tr>
  <td style="padding: 20px; font-family: Arial, sans-serif; font-size: 16px; color: #333333;">
    <h1 style="margin: 0 0 10px;">Dear Valued Customer,</h1>
    <p>We appreciate your continued loyalty to our brand.</p>
  </td>
</tr>"""

_SEGMENT_SHOWCASE = """\
<tr>
  <td style="padding: 20px; font-family: Arial, sans-serif;">
    <h1 style="margin: 0 0 10px;">Hello Subscriber,</h1>
    <p>Based on your preferences, we think you'll love these picks.</p>
  </td>
</tr>
<tr>
  <td style="padding: 20px; background-color: #f0f8ff; font-family: Arial, sans-serif;">
    <h2 style="margin: 0 0 8px;">Just For You</h2>
    <p>Explore products in Electronics that match your interests.</p>
    <a href="https://example.com/segment" style="display: inline-block; padding: 12px 24px; background-color: #28a745; color: #fff; text-decoration: none;">Explore</a>
  </td>
</tr>"""

_PURCHASE_HISTORY = """\
<tr>
  <td style="padding: 20px; font-family: Arial, sans-serif;">
    <h2 style="margin: 0 0 12px;">Your Recent Orders</h2>
  </td>
</tr>
<tr>
  <td style="padding: 0 20px;">
    <table role="presentation" width="100%" style="border-collapse: collapse;">
      <tr style="border-bottom: 1px solid #eee;">
        <td style="padding: 8px; font-family: Arial, sans-serif; font-size: 14px;">Order #12345</td>
        <td style="padding: 8px; font-family: Arial, sans-serif; font-size: 14px;">Widget Pro</td>
        <td style="padding: 8px; font-family: Arial, sans-serif; font-size: 14px;">$49.99</td>
      </tr>
      <tr style="border-bottom: 1px solid #eee;">
        <td style="padding: 8px; font-family: Arial, sans-serif; font-size: 14px;">Order #12346</td>
        <td style="padding: 8px; font-family: Arial, sans-serif; font-size: 14px;">Gadget Plus</td>
        <td style="padding: 8px; font-family: Arial, sans-serif; font-size: 14px;">$79.99</td>
      </tr>
    </table>
  </td>
</tr>"""

_LOYALTY_STATUS = """\
<tr>
  <td style="padding: 20px; font-family: Arial, sans-serif;">
    <h1 style="margin: 0 0 10px;">Hello Member,</h1>
    <p>Your current status: Standard</p>
    <p>Points balance: 500</p>
  </td>
</tr>
<tr>
  <td style="padding: 20px; font-family: Arial, sans-serif;">
    <table role="presentation" width="100%">
      <tr>
        <td style="padding: 8px; text-align: center; background-color: #cd7f32; color: #fff;">Bronze</td>
        <td style="padding: 8px; text-align: center; background-color: #c0c0c0; color: #333;">Silver</td>
        <td style="padding: 8px; text-align: center; background-color: #ffd700; color: #333;">Gold</td>
        <td style="padding: 8px; text-align: center; background-color: #e5e4e2; color: #333;">Platinum</td>
      </tr>
    </table>
  </td>
</tr>"""

_ADOBE_GREETING = """\
<tr>
  <td style="padding: 20px; font-family: Arial, sans-serif; font-size: 16px; color: #333333;">
    <h1 style="margin: 0 0 10px;">Dear Friend,</h1>
    <p>We're glad to have you with us. Here's what's new this month.</p>
  </td>
</tr>"""

_DYNAMIC_IMAGES = """\
<tr>
  <td style="padding: 20px; font-family: Arial, sans-serif;">
    <h2 style="margin: 0 0 12px;">Your Personalized Picks</h2>
  </td>
</tr>
<tr>
  <td style="padding: 0 20px;">
    <table role="presentation" width="100%">
      <tr>
        <td width="50%" style="padding: 8px;">
          <img src="https://example.com/default-hero.jpg" alt="Featured item" width="260" style="display: block;">
          <p style="font-family: Arial, sans-serif; font-size: 14px;">Featured Item</p>
        </td>
        <td width="50%" style="padding: 8px;">
          <img src="https://example.com/default-secondary.jpg" alt="Secondary item" width="260" style="display: block;">
          <p style="font-family: Arial, sans-serif; font-size: 14px;">Secondary Item</p>
        </td>
      </tr>
    </table>
  </td>
</tr>"""

_COLLECTION_ITERATION = """\
<tr>
  <td style="padding: 20px; font-family: Arial, sans-serif;">
    <h2 style="margin: 0 0 12px;">Your Wishlist</h2>
    <p>Items you've saved for later:</p>
  </td>
</tr>
<tr>
  <td style="padding: 0 20px;">
    <table role="presentation" width="100%">
      <tr>
        <td style="padding: 8px; font-family: Arial, sans-serif; font-size: 14px; border-bottom: 1px solid #eee;">
          Item 1 - Placeholder Product
        </td>
      </tr>
      <tr>
        <td style="padding: 8px; font-family: Arial, sans-serif; font-size: 14px; border-bottom: 1px solid #eee;">
          Item 2 - Placeholder Product
        </td>
      </tr>
    </table>
  </td>
</tr>"""

_MIXED_CTA = """\
<tr>
  <td style="padding: 20px; font-family: Arial, sans-serif;">
    <h1 style="margin: 0 0 10px;">Hey there,</h1>
    <p>Don't miss out on these exclusive deals.</p>
  </td>
</tr>
<tr>
  <td style="padding: 20px; text-align: center; font-family: Arial, sans-serif;">
    <a href="https://example.com/deal" style="display: inline-block; padding: 14px 28px; background-color: #dc3545; color: #fff; text-decoration: none; font-weight: bold;">Claim Your Deal</a>
    <p style="margin-top: 12px; font-size: 12px; color: #999;">This offer expires January 31, 2026</p>
  </td>
</tr>"""

# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

PERSONALISATION_TEST_CASES: list[dict[str, Any]] = [
    # ── Braze (4 cases) ──
    {
        "id": "pers-001",
        "platform": "braze",
        "dimensions": {
            "esp_platform": "braze",
            "variable_complexity": "basic_field",
            "conditional_complexity": "simple_if_else",
            "fallback_challenge": "simple_default",
        },
        "html_input": _BASE_HTML.format(body_content=_GREETING_ROW),
        "requirements": (
            "Add first name greeting with 'there' as fallback. "
            "Replace 'Hi Friend' with 'Hi {{first_name}}' using Braze Liquid, "
            "defaulting to 'Hi there' if first_name is blank."
        ),
        "expected_challenges": [
            "Correct {{ }} Liquid syntax",
            "Default filter for missing first_name",
            "Preserve all existing HTML structure",
        ],
    },
    {
        "id": "pers-002",
        "platform": "braze",
        "dimensions": {
            "esp_platform": "braze",
            "variable_complexity": "custom_attribute",
            "conditional_complexity": "nested_conditional",
            "fallback_challenge": "section_hiding",
        },
        "html_input": _BASE_HTML.format(body_content=_VIP_SECTIONS),
        "requirements": (
            "Show the VIP Exclusive Offer section only for users with "
            "custom_attributes.loyalty_tier == 'premium' or 'gold'. "
            "Show the Standard Offer section for all other users. "
            "Personalise the greeting with first_name, fallback to 'Customer'."
        ),
        "expected_challenges": [
            "Nested if/elsif conditionals for tier checking",
            "Section-level show/hide with {% if %}",
            "Custom attribute dot notation",
            "Fallback for greeting",
        ],
    },
    {
        "id": "pers-003",
        "platform": "braze",
        "dimensions": {
            "esp_platform": "braze",
            "variable_complexity": "connected_content",
            "conditional_complexity": "multi_condition_chain",
            "fallback_challenge": "conditional_fallback",
        },
        "html_input": _BASE_HTML.format(body_content=_PRODUCT_GRID),
        "requirements": (
            "Use Braze Connected Content to fetch product recommendations from "
            "https://api.example.com/recs?user_id={{user_id}}. "
            "Display up to 2 products from the API response. "
            "If the API fails or returns empty, show the static product placeholders. "
            "Use :save parameter and check response status."
        ),
        "expected_challenges": [
            "{% connected_content %} with :save syntax",
            "Response status check before rendering",
            "Fallback to static content on failure",
            "Multi-condition chain for response validation",
        ],
    },
    {
        "id": "pers-004",
        "platform": "braze",
        "dimensions": {
            "esp_platform": "braze",
            "variable_complexity": "content_block",
            "conditional_complexity": "filter_chain",
            "fallback_challenge": "null_handling",
        },
        "html_input": _BASE_HTML.format(body_content=_CONTENT_BLOCK_ROW),
        "requirements": (
            "Replace the static date with the current date formatted as 'Month Day, Year' "
            "using Braze date filters. Insert a content block named 'weekly_digest_header' "
            "above the digest content. Handle null values for any missing content gracefully."
        ),
        "expected_challenges": [
            "{% content_blocks.${weekly_digest_header} %} syntax",
            "Date filter chain: | date: '%B %d, %Y'",
            "Null handling for missing content",
            "Preserve existing structure",
        ],
    },
    # ── SFMC (4 cases) ──
    {
        "id": "pers-005",
        "platform": "sfmc",
        "dimensions": {
            "esp_platform": "sfmc",
            "variable_complexity": "basic_field",
            "conditional_complexity": "simple_if_else",
            "fallback_challenge": "simple_default",
        },
        "html_input": _BASE_HTML.format(body_content=_SUBSCRIBER_GREETING),
        "requirements": (
            "Add subscriber first name using AMPscript SET and output. "
            "Use %%=v(@firstName)=%% for inline output. "
            "Default to 'Valued Customer' if the FirstName field is empty."
        ),
        "expected_challenges": [
            "%%[SET @firstName = ...]%% block syntax",
            "%%=v(@variable)=%% inline output",
            "IIF or IF/ELSE for empty check",
            "Proper AMPscript casing",
        ],
    },
    {
        "id": "pers-006",
        "platform": "sfmc",
        "dimensions": {
            "esp_platform": "sfmc",
            "variable_complexity": "data_extension_lookup",
            "conditional_complexity": "nested_conditional",
            "fallback_challenge": "section_hiding",
        },
        "html_input": _BASE_HTML.format(body_content=_SEGMENT_SHOWCASE),
        "requirements": (
            "Use AMPscript Lookup() to fetch the subscriber's preferred category "
            "from the 'UserPreferences' data extension using SubscriberKey. "
            "Show the personalized section only if a preference exists. "
            "Personalise the category name in the explore section."
        ),
        "expected_challenges": [
            "Lookup() function with DE name and key",
            "Nested IF for section visibility",
            "Data Extension field references",
            "Section hiding when no preference found",
        ],
    },
    {
        "id": "pers-007",
        "platform": "sfmc",
        "dimensions": {
            "esp_platform": "sfmc",
            "variable_complexity": "nested_object",
            "conditional_complexity": "loop_iteration",
            "fallback_challenge": "empty_array",
        },
        "html_input": _BASE_HTML.format(body_content=_PURCHASE_HISTORY),
        "requirements": (
            "Use AMPscript LookupRows() to fetch the subscriber's recent orders "
            "from the 'OrderHistory' data extension. Iterate over the rows using "
            "FOR loop to display order number, product name, and price. "
            "If no orders exist, show a 'No recent orders' message instead."
        ),
        "expected_challenges": [
            "LookupRows() for multi-row retrieval",
            "FOR @i = 1 TO RowCount(@rows) loop",
            "Field() function to extract row values",
            "Empty rowset handling",
        ],
    },
    {
        "id": "pers-008",
        "platform": "sfmc",
        "dimensions": {
            "esp_platform": "sfmc",
            "variable_complexity": "custom_attribute",
            "conditional_complexity": "multi_condition_chain",
            "fallback_challenge": "type_mismatch",
        },
        "html_input": _BASE_HTML.format(body_content=_LOYALTY_STATUS),
        "requirements": (
            "Fetch the subscriber's loyalty points and tier from profile attributes. "
            "Use a multi-condition IF/ELSEIF chain to highlight the correct tier cell "
            "in the tier table. Display actual points balance. "
            "Handle cases where points value might be non-numeric."
        ),
        "expected_challenges": [
            "Multi-condition IF/ELSEIF/ELSE chain",
            "AttributeValue() for profile fields",
            "Type checking for numeric points",
            "Correct tier cell highlighting",
        ],
    },
    # ── Adobe Campaign (3 cases) ──
    {
        "id": "pers-009",
        "platform": "adobe_campaign",
        "dimensions": {
            "esp_platform": "adobe_campaign",
            "variable_complexity": "basic_field",
            "conditional_complexity": "simple_if_else",
            "fallback_challenge": "simple_default",
        },
        "html_input": _BASE_HTML.format(body_content=_ADOBE_GREETING),
        "requirements": (
            "Add recipient first name greeting using Adobe Campaign recipient fields. "
            "Use <%= recipient.firstName %> for output. "
            "Default to 'Friend' if the firstName field is missing or empty."
        ),
        "expected_challenges": [
            "<%= %> output tag syntax",
            "recipient.field dot notation",
            "Ternary or if-block for fallback",
            "Preserve existing content",
        ],
    },
    {
        "id": "pers-010",
        "platform": "adobe_campaign",
        "dimensions": {
            "esp_platform": "adobe_campaign",
            "variable_complexity": "nested_object",
            "conditional_complexity": "nested_conditional",
            "fallback_challenge": "conditional_fallback",
        },
        "html_input": _BASE_HTML.format(body_content=_DYNAMIC_IMAGES),
        "requirements": (
            "Replace the static product images with dynamic images based on the "
            "recipient's profile category (recipient.category). "
            "Use recipient.preferredImageUrl for the hero image. "
            "If no preferred image exists, keep the default image. "
            "Show category-specific alt text using recipient.categoryName."
        ),
        "expected_challenges": [
            "Nested object access: recipient.preferredImageUrl",
            "Conditional image swapping with fallback",
            "Dynamic alt text from profile data",
            "<% if %> blocks for nested conditions",
        ],
    },
    {
        "id": "pers-011",
        "platform": "adobe_campaign",
        "dimensions": {
            "esp_platform": "adobe_campaign",
            "variable_complexity": "custom_attribute",
            "conditional_complexity": "loop_iteration",
            "fallback_challenge": "null_handling",
        },
        "html_input": _BASE_HTML.format(body_content=_COLLECTION_ITERATION),
        "requirements": (
            "Use Adobe Campaign JavaScript to iterate over the recipient's wishlist "
            "collection (recipient.wishlist). Display each item name. "
            "Add null guard before iteration — if wishlist is null or empty, "
            "show 'Your wishlist is empty' message. Limit display to 5 items."
        ),
        "expected_challenges": [
            "<% for (var i=0; i<items.length; i++) %> loop",
            "Null guard before iteration",
            "Collection length check and limit",
            "Server-side JS in <% %> blocks",
        ],
    },
    # ── Mixed / edge case ──
    {
        "id": "pers-012",
        "platform": "braze",
        "dimensions": {
            "esp_platform": "braze",
            "variable_complexity": "basic_field",
            "conditional_complexity": "simple_if_else",
            "fallback_challenge": "simple_default",
        },
        "html_input": _BASE_HTML.format(body_content=_MIXED_CTA),
        "requirements": (
            "Personalise the greeting with first_name (fallback 'there'). "
            "Make the CTA link dynamic using a custom attribute deal_url. "
            "If deal_url is blank, use {% abort_message('no deal') %} to prevent sending. "
            "Replace the static expiry date with the deal_expiry attribute."
        ),
        "expected_challenges": [
            "abort_message for send prevention",
            "Dynamic href from custom attribute",
            "Multiple variable injections in one template",
            "Date attribute rendering",
        ],
    },
]
