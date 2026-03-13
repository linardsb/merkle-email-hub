---
level: L4
type: reference
domain: personalisation
platform: braze
qa_check: personalisation_syntax
version: "1.0"
---

# ESP: Braze — Liquid Personalisation Reference

**Language:** Liquid (Shopify, up to Liquid 5)
**Delimiters:** `{{ }}` output · `{% %}` logic
**Case-sensitive:** Yes
**Docs:** https://www.braze.com/docs/user_guide/personalization_and_dynamic_content/liquid

---

## SECTIONS
1. [Standard Profile Attributes](#1-standard-profile-attributes)
2. [Custom Attributes](#2-custom-attributes)
3. [Event & API Trigger Properties](#3-event--api-trigger-properties)
4. [Campaign & Canvas Metadata](#4-campaign--canvas-metadata)
5. [Subscription State](#5-subscription-state)
6. [Conditional Logic](#6-conditional-logic)
7. [Filters — String](#7-filters--string)
8. [Filters — Number](#8-filters--number)
9. [Filters — Date](#9-filters--date)
10. [Filters — Array](#10-filters--array)
11. [Variables — assign & capture](#11-variables--assign--capture)
12. [Loops — for](#12-loops--for)
13. [Connected Content](#13-connected-content)
14. [Catalog Lookups](#14-catalog-lookups)
15. [Content Blocks](#15-content-blocks)
16. [Abort Logic](#16-abort-logic)
17. [Random & A/B Logic](#17-random--ab-logic)
18. [Date Arithmetic](#18-date-arithmetic)
19. [Advanced Patterns](#19-advanced-patterns)
20. [Fallback Patterns](#20-fallback-patterns)
21. [Gotchas & Debugging](#21-gotchas--debugging)

---

## 1. Standard Profile Attributes

```liquid
{{ ${first_name} }}
{{ ${last_name} }}
{{ ${email_address} }}
{{ ${city} }}
{{ ${country} }}
{{ ${language} }}
{{ ${time_zone} }}
{{ ${gender} }}                  <!-- M / F / O / N / P / U -->
{{ ${phone_number} }}
{{ ${date_of_birth} }}
{{ ${date_of_first_session} }}
{{ ${date_of_last_session} }}
{{ ${most_recent_app_version} }}
{{ ${most_recent_locale} }}
{{ ${most_recent_os_version} }}
{{ ${user_id} }}                 <!-- external_id -->
{{ ${braze_id} }}
{{ ${random_bucket_number} }}    <!-- 0–9999, for cohort splitting -->
```

---

## 2. Custom Attributes

```liquid
{{ custom_attribute.${attribute_name} }}

<!-- Examples -->
{{ custom_attribute.${loyalty_tier} }}
{{ custom_attribute.${last_purchase_date} }}
{{ custom_attribute.${promo_code} }}
{{ custom_attribute.${account_status} }}
{{ custom_attribute.${preferred_store} }}
{{ custom_attribute.${total_spend} }}

<!-- Array custom attribute — access by index -->
{{ custom_attribute.${favorite_categories}[0] }}
{{ custom_attribute.${favorite_categories}[1] }}
```

---

## 3. Event & API Trigger Properties

```liquid
<!-- Action/event-triggered campaigns -->
{{ event_properties.${property_name} }}
{{ event_properties.${order_total} }}
{{ event_properties.${product_name} }}
{{ event_properties.${order_id} }}
{{ event_properties.${sku} }}

<!-- API-triggered campaigns -->
{{ api_trigger_properties.${attribute_key} }}
{{ api_trigger_properties.${discount_amount} }}
{{ api_trigger_properties.${product_url} }}

<!-- Canvas entry properties -->
{{ canvas_entry_properties.${property} }}
```

---

## 4. Campaign & Canvas Metadata

```liquid
{{ campaign.${name} }}
{{ campaign.${message_name} }}
{{ campaign.${api_id} }}
{{ campaign.${dispatch_id} }}

{{ canvas.${name} }}
{{ canvas.${api_id} }}
{{ canvas.${variation_name} }}
{{ canvas.${variation_api_id} }}
```

---

## 5. Subscription State

```liquid
{{ ${email_opted_in} }}          <!-- true / false -->
{{ ${push_opted_in} }}
{{ ${sms_opted_in} }}
{{ ${email_unsubscribed} }}
```

---

## 6. Conditional Logic

### if / elsif / else / endif

```liquid
{% if ${first_name} %}
  Hello, {{ ${first_name} }}!
{% elsif custom_attribute.${nickname} %}
  Hello, {{ custom_attribute.${nickname} }}!
{% else %}
  Hello, Valued Customer!
{% endif %}
```

### unless (inverse if)

```liquid
{% unless ${email_opted_in} %}
  Please opt in to receive exclusive offers.
{% endunless %}
```

### case / when

```liquid
{% case ${language} %}
  {% when 'en' %}Welcome!
  {% when 'fr' %}Bienvenue!
  {% when 'de' %}Willkommen!
  {% when 'es' %}¡Bienvenido!
  {% when 'pt' %}Bem-vindo!
  {% else %}Hello!
{% endcase %}
```

### Checking nil vs blank

```liquid
<!-- nil = attribute was never set -->
{% if ${first_name} == nil %}
  Name not on file.
{% endif %}

<!-- blank = empty string, false, or nil -->
{% if custom_attribute.${loyalty_tier} == blank %}
  No tier assigned.
{% endif %}
```

### Operators

| Operator | Meaning |
|----------|---------|
| `==` | Equal |
| `!=` | Not equal |
| `>` | Greater than |
| `<` | Less than |
| `>=` | Greater than or equal |
| `<=` | Less than or equal |
| `contains` | String or array contains value |
| `and` | Logical AND |
| `or` | Logical OR |

---

## 7. Filters — String

```liquid
{{ ${first_name} | capitalize }}              <!-- John -->
{{ ${first_name} | upcase }}                  <!-- JOHN -->
{{ ${first_name} | downcase }}                <!-- john -->
{{ ${first_name} | default: 'Friend' }}       <!-- Fallback if nil/empty -->
{{ custom_attribute.${bio} | truncate: 100, "…" }}
{{ custom_attribute.${bio} | strip_html }}
{{ custom_attribute.${bio} | escape }}
{{ custom_attribute.${text} | strip }}        <!-- Strip surrounding whitespace -->
{{ custom_attribute.${text} | lstrip }}
{{ custom_attribute.${text} | rstrip }}
{{ custom_attribute.${product} | prepend: "Buy: " }}
{{ custom_attribute.${tag} | append: " sale" }}
{{ custom_attribute.${sentence} | replace: "bad", "good" }}
{{ custom_attribute.${sentence} | remove: "unwanted" }}
{{ custom_attribute.${name} | slice: 0, 5 }}  <!-- First 5 chars -->
{{ custom_attribute.${csv} | split: "," }}    <!-- Returns array -->
{{ custom_attribute.${url} | url_encode }}
{{ custom_attribute.${html} | url_decode }}
{{ custom_attribute.${text} | size }}         <!-- Character count -->
```

---

## 8. Filters — Number

```liquid
{{ custom_attribute.${price} | round }}        <!-- 12 -->
{{ custom_attribute.${price} | round: 2 }}     <!-- 12.50 -->
{{ custom_attribute.${price} | ceil }}
{{ custom_attribute.${price} | floor }}
{{ custom_attribute.${price} | abs }}
{{ custom_attribute.${price} | plus: 5 }}
{{ custom_attribute.${price} | minus: 10 }}
{{ custom_attribute.${price} | times: 1.2 }}
{{ custom_attribute.${price} | divided_by: 100.0 }}
{{ custom_attribute.${price} | modulo: 3 }}
```

---

## 9. Filters — Date

```liquid
{{ ${date_of_first_session} | date: "%B %d, %Y" }}   <!-- January 15, 2024 -->
{{ ${date_of_first_session} | date: "%d/%m/%Y" }}    <!-- 15/01/2024 -->
{{ ${date_of_first_session} | date: "%Y-%m-%d" }}    <!-- 2024-01-15 -->
{{ ${date_of_first_session} | date: "%A, %B %d" }}   <!-- Monday, January 15 -->
{{ ${date_of_first_session} | date: "%B" }}           <!-- January -->
{{ ${date_of_first_session} | date: "%Y" }}           <!-- 2024 -->
{{ ${date_of_first_session} | date: "%s" }}           <!-- Unix timestamp -->
{{ 'now' | date: "%B %d, %Y" }}                       <!-- Today formatted -->
{{ 'now' | date: "%s" }}                              <!-- Current Unix timestamp -->
```

**PHP strftime format codes:**

| Code | Output |
|------|--------|
| `%Y` | 2024 |
| `%y` | 24 |
| `%m` | 01 |
| `%B` | January |
| `%b` | Jan |
| `%d` | 15 |
| `%A` | Monday |
| `%a` | Mon |
| `%H` | 14 (24h hour) |
| `%I` | 02 (12h hour) |
| `%M` | 30 (minutes) |
| `%S` | 00 (seconds) |
| `%s` | Unix timestamp |

---

## 10. Filters — Array

```liquid
{{ custom_attribute.${items} | first }}
{{ custom_attribute.${items} | last }}
{{ custom_attribute.${items} | size }}
{{ custom_attribute.${items} | join: ", " }}
{{ custom_attribute.${items} | sort }}
{{ custom_attribute.${items} | sort: 'price' }}
{{ custom_attribute.${items} | reverse }}
{{ custom_attribute.${items} | uniq }}
{{ custom_attribute.${items} | compact }}              <!-- Remove nil values -->
{{ custom_attribute.${items} | map: 'name' }}          <!-- Extract one field -->
{{ custom_attribute.${items} | where: 'active', true }} <!-- Filter by field -->
```

---

## 11. Variables — assign & capture

### assign

```liquid
{% assign full_name = ${first_name} | append: " " | append: ${last_name} %}
Hello, {{ full_name }}!

{% assign greeting = "Hello" %}
{% if ${language} == 'fr' %}{% assign greeting = "Bonjour" %}{% endif %}
{{ greeting }}, {{ ${first_name} | default: 'there' }}!
```

### capture (multi-line block)

```liquid
{% capture discount_text %}
  {% if custom_attribute.${loyalty_points} >= 500 %}
    20%
  {% elsif custom_attribute.${loyalty_points} >= 200 %}
    15%
  {% else %}
    10%
  {% endif %}
{% endcapture %}

You qualify for a {{ discount_text | strip }} discount.
```

> **Tip:** Save reusable assign blocks as a Content Block placed at the top of the message. Variables defined inside a Content Block are available in the parent message.

---

## 12. Loops — for

### Basic loop

```liquid
{% for item in custom_attribute.${favorite_categories} %}
  <li>{{ item }}</li>
{% endfor %}
```

### forloop variables

```liquid
{% for item in custom_attribute.${items} %}
  {{ forloop.index }}      <!-- 1-based position -->
  {{ forloop.index0 }}     <!-- 0-based position -->
  {{ forloop.first }}      <!-- true on first iteration -->
  {{ forloop.last }}       <!-- true on last iteration -->
  {{ forloop.length }}     <!-- total count -->
  {{ item }}
{% endfor %}
```

### limit & offset

```liquid
{% for item in custom_attribute.${items} limit: 5 %}
  {{ item }}
{% endfor %}

{% for item in custom_attribute.${items} limit: 3 offset: 2 %}
  {{ item }}
{% endfor %}
```

### break & continue

```liquid
{% for product in custom_attribute.${wishlist} %}
  {% if product == blank %}{% break %}{% endif %}
  <li>{{ product }}</li>
{% endfor %}
```

---

## 13. Connected Content

### Basic GET

```liquid
{% connected_content https://api.example.com/user/{{${user_id}}} :save response %}
{{ response.name }}
{{ response.offer_title }}
{{ response.recommendations[0].title }}
{{ response.recommendations[0].image_url }}
```

### With headers & cache

```liquid
{% connected_content https://api.example.com/offers
  :headers {"Authorization": "Bearer TOKEN", "Content-Type": "application/json"}
  :save offers
  :cache 300
%}
{% for offer in offers.items %}
  <p>{{ offer.title }}: {{ offer.discount }}</p>
{% endfor %}
```

### POST request

```liquid
{% connected_content https://api.example.com/personalize
  :method post
  :body user_id={{${user_id}}}&segment={{custom_attribute.${segment}}}
  :content_type application/x-www-form-urlencoded
  :save result
%}
{{ result.recommended_product }}
```

### Null handling from Connected Content

```liquid
{% if response.field != null and response.field != blank %}
  {{ response.field }}
{% else %}
  Default value
{% endif %}
```

---

## 14. Catalog Lookups

```liquid
<!-- Single item -->
{% catalog_items CatalogName item_id_variable %}
{{ items[0].title }}
{{ items[0].price }}
{{ items[0].image_url }}
{{ items[0].description }}

<!-- Multiple items -->
{% catalog_items CatalogName id1, id2, id3 %}
{{ items[0].name }} | {{ items[1].name }} | {{ items[2].name }}

<!-- From custom attribute -->
{% catalog_items Products custom_attribute.${last_viewed_product_id} %}
{% if items[0] %}
  <p>You recently viewed: {{ items[0].name }}</p>
{% endif %}
```

---

## 15. Content Blocks

```liquid
{{content_blocks.${BlockName}}}
```

> Content Blocks can contain full Liquid including variables. Variables defined in the parent are accessible inside the block. Variables defined inside a block do NOT automatically propagate back to the parent.

---

## 16. Abort Logic

```liquid
<!-- Abort the send entirely -->
{% if custom_attribute.${account_status} == 'suspended' %}
  {% abort_message('Account suspended') %}
{% endif %}

{% if ${email_address} == blank %}
  {% abort_message('No email address') %}
{% endif %}

<!-- Abort if Connected Content returned empty -->
{% connected_content https://api.example.com/offers :save offers %}
{% if offers == blank or offers.items.size == 0 %}
  {% abort_message('No offers available') %}
{% endif %}
```

---

## 17. Random & A/B Logic

```liquid
<!-- Split users into 2 buckets -->
{% assign bucket = ${random_bucket_number} | modulo: 2 %}
{% if bucket == 0 %}
  Version A content
{% else %}
  Version B content
{% endif %}

<!-- Split into 3 buckets (thirds) -->
{% assign bucket = ${random_bucket_number} | modulo: 3 %}
{% case bucket %}
  {% when 0 %}Version A
  {% when 1 %}Version B
  {% when 2 %}Version C
{% endcase %}
```

---

## 18. Date Arithmetic

```liquid
<!-- Days since signup -->
{% assign now_ts    = 'now' | date: '%s' | plus: 0 %}
{% assign signup_ts = ${date_of_first_session} | date: '%s' | plus: 0 %}
{% assign days_active = now_ts | minus: signup_ts | divided_by: 86400 %}
You've been with us for {{ days_active }} days!

<!-- Birthday check -->
{% assign today = 'now' | date: "%m-%d" %}
{% assign bday  = ${date_of_birth} | date: "%m-%d" %}
{% if today == bday %}
  Happy Birthday, {{ ${first_name} | default: 'there' }}! 🎂
{% endif %}

<!-- Countdown to expiry -->
{% assign expire_ts = custom_attribute.${offer_expiry} | date: "%s" | plus: 0 %}
{% assign now_ts    = 'now' | date: "%s" | plus: 0 %}
{% assign days_left = expire_ts | minus: now_ts | divided_by: 86400 %}
Your offer expires in {{ days_left }} days.

<!-- Add days to today (for future date display) -->
{% assign future_ts   = 'now' | date: '%s' | plus: 604800 %}  <!-- +7 days in seconds -->
{% assign future_date = future_ts | date: "%B %d, %Y" %}
Your order arrives by {{ future_date }}.
```

---

## 19. Advanced Patterns

### Loyalty tier content swap

```liquid
{% assign tier = custom_attribute.${loyalty_tier} | downcase %}
{% if tier == 'platinum' %}
  <div class="banner banner--platinum">Platinum exclusive offer</div>
{% elsif tier == 'gold' %}
  <div class="banner banner--gold">Gold member offer</div>
{% elsif tier == 'silver' %}
  <div class="banner banner--silver">Silver member offer</div>
{% else %}
  <div class="banner banner--standard">Join our loyalty programme</div>
{% endif %}
```

### Personalised subject line

```
Subject: {{ ${first_name} | default: 'Hey' }}, your order is ready 🎉
```

### Dynamic image URL

```liquid
<img src="{{ custom_attribute.${profile_image_url} | default: 'https://cdn.example.com/default-avatar.png' }}"
     alt="{{ ${first_name} | default: 'User' }}'s avatar" />
```

### Personalised CTA link

```liquid
<a href="https://app.example.com/account/{{ ${user_id} }}?promo={{ custom_attribute.${promo_code} | url_encode }}">
  Claim Your Offer
</a>
```

### Product recommendation loop (Catalog)

```liquid
{% catalog_items Recommendations custom_attribute.${reco_product_ids} %}
{% for item in items %}
  <div class="product-card">
    <img src="{{ item.image_url }}" alt="{{ item.name }}" />
    <p class="product-name">{{ item.name }}</p>
    <p class="product-price">£{{ item.price | round: 2 }}</p>
    <a href="{{ item.url }}">Shop Now</a>
  </div>
{% endfor %}
```

### Language / localisation block

```liquid
{% case ${language} %}
  {% when 'fr' %}
    Bonjour {{ ${first_name} | default: 'cher client' }} !
  {% when 'de' %}
    Hallo {{ ${first_name} | default: 'Kunde' }}!
  {% when 'es' %}
    Hola {{ ${first_name} | default: 'cliente' }}!
  {% else %}
    Hello {{ ${first_name} | default: 'there' }}!
{% endcase %}
```

### Gender / salutation

```liquid
{% if ${gender} == 'M' %}Dear Mr {{ ${last_name} }},
{% elsif ${gender} == 'F' %}Dear Ms {{ ${last_name} }},
{% else %}Dear {{ ${first_name} | default: 'Valued Customer' }},
{% endif %}
```

---

## 20. Fallback Patterns

| Scenario | Liquid |
|----------|--------|
| First name with fallback | `{{ ${first_name} \| default: 'Friend' }}` |
| Custom attribute fallback | `{{ custom_attribute.${tier} \| default: 'Standard' }}` |
| Capitalised with fallback | `{{ ${first_name} \| capitalize \| default: 'Friend' }}` |
| Nested fallback | `{% if ${first_name} %}{{ ${first_name} }}{% elsif custom_attribute.${nickname} %}{{ custom_attribute.${nickname} }}{% else %}Friend{% endif %}` |
| Fallback image URL | `{{ custom_attribute.${image_url} \| default: 'https://cdn.example.com/default.jpg' }}` |

---

## 21. Gotchas & Debugging

| Issue | Cause | Fix |
|-------|-------|-----|
| Tag renders blank | Attribute missing or wrong namespace | Add `\| default:` filter; verify attribute name in dashboard |
| Curly quotes break Liquid | Pasting from Word/Notion | Re-type quotes directly in Braze editor |
| `{% endif %}` error | Missing closing tag | Every `{% if %}` needs `{% endif %}` |
| Connected Content timeout | Slow API response | Add `:cache 300`; ensure API responds in < 2s |
| Content Block variable not accessible | Variable scope | Define variables inside each block |
| `{% abort_message %}` no effect | Used in preview, not send | abort_message only fires on actual send |
| Array index out of bounds | Array shorter than expected | Check `{% if array.size > 0 %}` before accessing `[0]` |
| Liquid code appears as literal text | Missing `{{ }}` delimiters | Ensure output tags wrap the variable |
| Date renders wrong timezone | Braze dates are UTC | Use `| date:` with explicit formatting |
| `forloop.first` always false | Wrong syntax | Must be inside `{% for %}` block |

> **Rule:** Always place Liquid code within the `<body>` tag only. Placing it in `<head>` may cause inconsistent rendering.

---

## QA Rule Mapping

This section maps the reference material above to executable QA engine rules.

### Rules Applied to Braze Liquid Templates

| Rule ID | Group | Check | Deduction | Applies When |
|---------|-------|-------|-----------|-------------|
| ps-delimiter-unbalanced | delimiter_balance | Delimiter pairs balanced | -0.15 | Unclosed `{{ }}` or `{% %}` |
| ps-conditional-unbalanced | delimiter_balance | Conditional blocks balanced | -0.15 | Unclosed `{% if %}…{% endif %}` |
| ps-fallback-missing | fallback_completeness | Output tags have defaults | -0.05 | Output tag without `| default:` filter |
| ps-fallback-empty | fallback_completeness | Fallback values non-empty | -0.03 | Empty string fallback `| default: ""` |
| ps-syntax-liquid | syntax_correctness | Liquid syntax well-formed | -0.10 | Dangling pipe, empty filter chain |
| ps-nesting-depth | best_practices | Nesting ≤ 3 levels | -0.03 | Nested `{% if %}` > 3 deep |
| ps-platform-mixed | platform_detection | Single platform | -0.30 | Multiple ESP syntaxes in one file |

### Score Examples

| Scenario | Tags | Issues | Deduction | Score |
|----------|------|--------|-----------|-------|
| Clean template | 12 | 0 | 0.00 | 1.00 |
| 3 tags missing fallbacks | 8 | 3 | -0.15 | 0.85 |
| 2 unbalanced + 1 missing fallback | 10 | 3 | -0.35 | 0.65 |
| Mixed with another ESP | 6 | 1 | -0.30 | 0.70 |

### Configuration Override

```yaml
personalisation_syntax:
  params:
    deduction_fallback_missing: 0.10    # Stricter for production
    max_nesting_depth: 2                # Tighter nesting limit
```
