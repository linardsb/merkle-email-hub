---
level: L4
type: reference
domain: personalisation
platform: klaviyo
qa_check: personalisation_syntax
version: "1.0"
---

# ESP: Klaviyo — Personalisation Reference

**Language:** Django Template Language (with custom Klaviyo extensions)
**Delimiters:** `{{ }}` output · `{% %}` logic
**Case-sensitive:** Yes — property names must exactly match profile/event keys
**Docs:** https://developers.klaviyo.com/en/docs/django-message-design · https://help.klaviyo.com/hc/en-us/articles/4408802648731

---

## SECTIONS
1. [Profile Personalisation Tags](#1-profile-personalisation-tags)
2. [Custom Profile Properties](#2-custom-profile-properties)
3. [Event Variables (Flow Emails)](#3-event-variables-flow-emails)
4. [Organisation Tags](#4-organisation-tags)
5. [Link & Utility Tags](#5-link--utility-tags)
6. [Conditional Logic](#6-conditional-logic)
7. [Filters](#7-filters)
8. [For Loops — Iterating Arrays](#8-for-loops--iterating-arrays)
9. [Common Event Schemas](#9-common-event-schemas)
10. [Dynamic Content Blocks (Visual Editor)](#10-dynamic-content-blocks-visual-editor)
11. [Advanced Patterns](#11-advanced-patterns)
12. [Fallback Patterns](#12-fallback-patterns)
13. [Gotchas & Debugging](#13-gotchas--debugging)

---

## 1. Profile Personalisation Tags

### Standard Klaviyo properties

```django
{{ first_name }}
{{ last_name }}
{{ email }}
{{ phone_number }}

<!-- Via person object (same data) -->
{{ person.first_name }}
{{ person.last_name }}
{{ person.email }}
{{ person.city }}
{{ person.region }}                 <!-- state / county -->
{{ person.country }}
{{ person.zip }}
{{ person.phone_number }}
{{ person.organization }}           <!-- company name -->
```

---

## 2. Custom Profile Properties

```django
{{ person|lookup:'PropertyName' }}
{{ person|lookup:'LoyaltyTier' }}
{{ person|lookup:'TotalSpend' }}
{{ person|lookup:'Favorite Category' }}   <!-- spaces in name are fine -->
{{ person|lookup:'Last Purchase Date' }}
{{ person|lookup:'Account Status' }}
{{ person|lookup:'Member Since' }}
{{ person|lookup:'Referral Code' }}

<!-- With default fallback -->
{{ person|lookup:'LoyaltyTier'|default:'Standard' }}
{{ person|lookup:'NickName'|default:first_name }}
```

---

## 3. Event Variables (Flow Emails)

Event variables are only available in **flow emails triggered by a metric event** (e.g. Placed Order, Started Checkout, Viewed Product).

### Generic event access

```django
{{ event.value }}                        <!-- Primary event value (e.g. revenue) -->
{{ event.event_name }}                   <!-- Metric name -->
{{ event.EventDate }}                    <!-- Event timestamp -->
```

### Placed Order event

```django
{{ event.extra.OrderId }}
{{ event.value }}                        <!-- Order total -->
{{ event.extra.Subtotal }}
{{ event.extra.DiscountAmount }}
{{ event.extra.ShippingCost }}
{{ event.extra.TaxAmount }}

<!-- First item -->
{{ event.extra.Items.0.ProductName }}
{{ event.extra.Items.0.ProductURL }}
{{ event.extra.Items.0.ImageURL }}
{{ event.extra.Items.0.ItemPrice }}
{{ event.extra.Items.0.Quantity }}
{{ event.extra.Items.0.SKU }}
{{ event.extra.Items.0.Categories }}
{{ event.extra.Items.0.Brand }}

<!-- Shipping -->
{{ event.extra.ShippingAddress.FirstName }}
{{ event.extra.ShippingAddress.LastName }}
{{ event.extra.ShippingAddress.Address1 }}
{{ event.extra.ShippingAddress.City }}
{{ event.extra.ShippingAddress.Region }}
{{ event.extra.ShippingAddress.Zip }}
{{ event.extra.ShippingAddress.Country }}
```

### Started Checkout / Abandoned Cart event

```django
{{ event.extra.CheckoutURL }}
{{ event.extra.Items.0.ProductName }}
{{ event.extra.Items.0.ImageURL }}
{{ event.extra.Items.0.ItemPrice }}
{{ event.extra.ItemCount }}
{{ event.value }}                         <!-- Cart total -->
```

### Viewed Product event

```django
{{ event.extra.ProductName }}
{{ event.extra.ProductID }}
{{ event.extra.ImageURL }}
{{ event.extra.URL }}
{{ event.extra.Price }}
{{ event.extra.Brand }}
{{ event.extra.Categories }}
```

### Accessing items by index

```django
{{ event.extra.Items.0.ProductName }}    <!-- First item -->
{{ event.extra.Items.1.ProductName }}    <!-- Second item -->
{{ event.extra.Items.2.ProductName }}    <!-- Third item -->
```

---

## 4. Organisation Tags

```django
{{ organization.name }}
{{ organization.website }}
{{ organization.phone }}
{{ organization.email }}
{{ organization.address }}
{{ organization.city }}
{{ organization.state }}
{{ organization.zip }}
{{ organization.country }}
```

---

## 5. Link & Utility Tags

```django
{{ unsubscribe_link }}              <!-- Unsubscribe URL (required by law) -->
{{ preferences_link }}              <!-- Subscription preferences centre -->
{{ view_in_browser_link }}          <!-- Web/browser view link -->
{{ subscription_link }}             <!-- Resubscribe link -->
```

> These tags are **only supported in email templates**, not SMS.

---

## 6. Conditional Logic

### Basic if / else / endif

```django
{% if first_name %}
  Hello, {{ first_name }}!
{% else %}
  Hello there!
{% endif %}
```

### if / elif / else chain

```django
{% if person|lookup:'LoyaltyTier' == 'Platinum' %}
  <div class="tier-platinum">Platinum exclusive offer inside</div>
{% elif person|lookup:'LoyaltyTier' == 'Gold' %}
  <div class="tier-gold">Gold member deal</div>
{% elif person|lookup:'LoyaltyTier' == 'Silver' %}
  <div class="tier-silver">Silver member discount</div>
{% else %}
  <div class="tier-standard">Join our loyalty programme</div>
{% endif %}
```

### Check if custom property exists / has value

```django
{% if person|lookup:'FavoriteProduct' %}
  Based on your love of {{ person|lookup:'FavoriteProduct' }}, you might like…
{% endif %}
```

### Check event property exists

```django
{% if event.extra.DiscountCode %}
  Use code <strong>{{ event.extra.DiscountCode }}</strong> at checkout.
{% endif %}
```

### Numeric comparisons

```django
{% if event.value > 100 %}
  You qualify for free shipping on this order!
{% endif %}

{% if person|lookup:'TotalOrders'|default:0 >= 10 %}
  Thank you for being a loyal customer.
{% endif %}
```

### not operator

```django
{% if not person|lookup:'HasPurchased' %}
  First order? Get 10% off.
{% endif %}
```

---

## 7. Filters

### Text filters

```django
{{ first_name|default:'Friend' }}           <!-- Fallback value -->
{{ first_name|title }}                      <!-- Title Case -->
{{ first_name|upper }}                      <!-- UPPER CASE -->
{{ first_name|lower }}                      <!-- lower case -->
{{ first_name|capfirst }}                   <!-- First letter only -->
{{ person|lookup:'Bio'|truncatechars:150 }} <!-- Truncate with ellipsis -->
{{ event.extra.OrderId|truncatechars:10 }}
{{ first_name|striptags }}                  <!-- Remove HTML tags -->
{{ person|lookup:'Field'|linebreaks }}      <!-- Convert newlines to <br> -->
{{ event.extra.Description|wordwrap:50 }}
```

### Number filters

```django
{{ event.value|floatformat:2 }}             <!-- 12.50 -->
{{ event.value|floatformat:0 }}             <!-- 13 (rounded) -->
{{ event.value|floatformat:-2 }}            <!-- 12.50 (only if needed) -->
{{ person|lookup:'TotalOrders'|default:0 }}
```

### Date filters

```django
{{ event.EventDate|date:"F j, Y" }}         <!-- January 15, 2024 -->
{{ event.EventDate|date:"d/m/Y" }}          <!-- 15/01/2024 -->
{{ event.EventDate|date:"N j, Y" }}         <!-- Jan. 15, 2024 -->
{{ event.EventDate|date:"l, F j" }}         <!-- Monday, January 15 -->
{{ event.EventDate|date:"Y" }}              <!-- 2024 -->
{{ event.EventDate|date:"F" }}              <!-- January -->
{{ person|lookup:'MemberSince'|date:"F Y" }} <!-- January 2024 -->
```

**Django date format codes:**

| Code | Output |
|------|--------|
| `j` | Day without leading zero (1–31) |
| `d` | Day with leading zero (01–31) |
| `l` | Full weekday (Monday) |
| `D` | Short weekday (Mon) |
| `n` | Month without leading zero (1–12) |
| `m` | Month with leading zero (01–12) |
| `F` | Full month name (January) |
| `M` | Short month (Jan) |
| `N` | Abbreviated month with period (Jan.) |
| `Y` | 4-digit year (2024) |
| `y` | 2-digit year (24) |
| `G` | 24h hour without leading zero |
| `H` | 24h hour with leading zero |
| `i` | Minutes with leading zero |

### Array / list filters

```django
{{ event.extra.Items|length }}              <!-- Count items -->
{{ event.extra.Items|first }}               <!-- First item (object) -->
{{ event.extra.Items|last }}                <!-- Last item (object) -->
```

---

## 8. For Loops — Iterating Arrays

### Basic loop over order items

```django
{% for item in event.extra.Items %}
  <tr>
    <td><img src="{{ item.ImageURL }}" width="80" /></td>
    <td>{{ item.ProductName }}</td>
    <td>{{ item.Quantity }}</td>
    <td>£{{ item.ItemPrice|floatformat:2 }}</td>
  </tr>
{% endfor %}
```

### forloop variables

```django
{% for item in event.extra.Items %}
  {% if forloop.first %}<ul>{% endif %}
  <li>
    {{ forloop.counter }}.  <!-- 1-based position -->
    {{ item.ProductName }}
  </li>
  {% if forloop.last %}</ul>{% endif %}
{% endfor %}
```

| Variable | Value |
|----------|-------|
| `forloop.counter` | 1-based iteration count |
| `forloop.counter0` | 0-based iteration count |
| `forloop.revcounter` | Iterations remaining (1-based) |
| `forloop.first` | True on first iteration |
| `forloop.last` | True on last iteration |

### Loop with limit (slice filter)

```django
<!-- Only show first 3 items -->
{% for item in event.extra.Items|slice:":3" %}
  {{ item.ProductName }}
{% endfor %}
```

### Empty loop fallback

```django
{% for item in event.extra.Items %}
  {{ item.ProductName }}
{% empty %}
  No items found.
{% endfor %}
```

---

## 9. Common Event Schemas

| Integration | Key Event | Top Properties |
|-------------|-----------|----------------|
| Shopify | `Placed Order` | `Items`, `OrderId`, `SubTotal`, `ShippingAddress` |
| Shopify | `Started Checkout` | `Items`, `CheckoutURL`, `ItemCount`, `value` |
| WooCommerce | `Placed Order` | `Items`, `OrderId`, `Billing` |
| Klaviyo JS | `Viewed Product` | `ProductName`, `ImageURL`, `URL`, `Price` |
| Custom | Varies | Defined by your API payload |

> **Finding your exact schema:** In the flow editor, click **Preview & Test** → select a real event → expand **Event Properties** to see all available keys.

---

## 10. Dynamic Content Blocks (Visual Editor)

In Klaviyo's drag-and-drop editor, add a **Conditional** block or use **Content Repeat** for arrays.

### Hide/show condition syntax (for visual Display Conditions)

```
person|lookup:"LoyaltyTier" == "Gold"
event.value > 100
first_name
not person|lookup:"HasPurchased"
```

### Content Repeat (no-code loop)

Configure a **Content Repeat** block in the editor by:
1. Drag a block into the email
2. Set **Repeat source** to the array variable (e.g. `event.extra.Items`)
3. Inside the block, use `{{ item.ProductName }}` etc.

The block automatically repeats for each item in the array.

---

## 11. Advanced Patterns

### Personalised subject line

```
Subject: {{ first_name|default:'Hey' }}, you left something behind 👀
```

### Dynamic image URL

```django
<img src="{{ person|lookup:'ProfileImageURL'|default:'https://cdn.example.com/default.png' }}"
     alt="{{ first_name|default:'User' }}" />
```

### Personalised CTA link

```django
<a href="{{ event.extra.CheckoutURL }}">Complete Your Order</a>

<a href="https://app.example.com/account?ref={{ person|lookup:'ReferralCode' }}">
  Share Your Link
</a>
```

### Order receipt table

```django
<table>
  <thead>
    <tr><th>Product</th><th>Qty</th><th>Price</th></tr>
  </thead>
  <tbody>
    {% for item in event.extra.Items %}
    <tr>
      <td>{{ item.ProductName }}</td>
      <td>{{ item.Quantity }}</td>
      <td>£{{ item.ItemPrice|floatformat:2 }}</td>
    </tr>
    {% endfor %}
  </tbody>
  <tfoot>
    <tr><td colspan="2">Total</td><td>£{{ event.value|floatformat:2 }}</td></tr>
  </tfoot>
</table>
```

### Gender salutation

```django
{% if person|lookup:'Gender' == 'M' %}
  Dear Mr {{ last_name }},
{% elif person|lookup:'Gender' == 'F' %}
  Dear Ms {{ last_name }},
{% else %}
  Dear {{ first_name|default:'Customer' }},
{% endif %}
```

### Language-based content

```django
{% if person|lookup:'Language' == 'fr' %}
  Bonjour {{ first_name|default:'cher client' }} !
{% elif person|lookup:'Language' == 'de' %}
  Hallo {{ first_name|default:'Kunde' }}!
{% else %}
  Hello {{ first_name|default:'there' }}!
{% endif %}
```

### Countdown / days-since calculation

Klaviyo does not have built-in date arithmetic in templates. Handle this logic in a **Flow filter** or use a Klaviyo Calculated Property, then reference it as a custom property:

```django
{{ person|lookup:'DaysUntilExpiry'|default:0 }} days remaining on your offer.
```

---

## 12. Fallback Patterns

| Scenario | Tag |
|----------|-----|
| First name | `{{ first_name\|default:'Friend' }}` |
| Custom property | `{{ person\|lookup:'Tier'\|default:'Standard' }}` |
| Event value | `{{ event.value\|default:0\|floatformat:2 }}` |
| Image URL | `{{ item.ImageURL\|default:'https://cdn.example.com/placeholder.jpg' }}` |
| Date | `{{ event.EventDate\|date:"F j, Y"\|default:'recently' }}` |
| Nested fallback | `{% if first_name %}{{ first_name }}{% else %}there{% endif %}` |

---

## 13. Gotchas & Debugging

| Issue | Cause | Fix |
|-------|-------|-----|
| Event variable shows blank | Flow not triggered by that event | Confirm flow trigger metric; use Preview & Test → Event Properties |
| `person\|lookup` returns empty | Property name case/spelling mismatch | Tags are case-sensitive — copy exact key from Klaviyo profile |
| Array index blank | Items array shorter than expected | Check `{% if event.extra.Items %}` before accessing `.0` |
| Loop not rendering | Event not a list/array at that path | Use Preview to inspect exact data structure |
| `|date` filter not working | Value is a string, not a datetime | Klaviyo only parses ISO-format datetimes |
| Conditional block not hiding | Display condition syntax error | Test condition against a real profile in flow preview |
| `{{ organization }}` blank | Company info not set in account | Fill in Settings > Organization > Contact Information |
| Custom property blank in campaign | Property not set on profile | Verify property exists on test profile |
| `forloop.first` never true | forloop variables only in `{% for %}` | Must be inside `{% for %}` block |
| Tags visible in preview | Preview using profile with no data | Use a profile with real data in Preview & Test |

---

## QA Rule Mapping

This section maps the reference material above to executable QA engine rules.

### Rules Applied to Klaviyo Django Templates

| Rule ID | Group | Check | Deduction | Applies When |
|---------|-------|-------|-----------|-------------|
| ps-delimiter-unbalanced | delimiter_balance | Delimiter pairs balanced | -0.15 | Unclosed `{{ }}` or `{% %}` |
| ps-conditional-unbalanced | delimiter_balance | Conditional blocks balanced | -0.15 | Unclosed `{% if %}…{% endif %}` |
| ps-fallback-missing | fallback_completeness | Output tags have defaults | -0.05 | Output tag without `|default:` filter |
| ps-fallback-empty | fallback_completeness | Fallback values non-empty | -0.03 | Empty string fallback `|default:""` |
| ps-syntax-liquid | syntax_correctness | Django/Liquid syntax well-formed | -0.10 | Dangling pipe, empty filter chain |
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
