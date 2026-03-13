---
level: L4
type: reference
domain: personalisation
platform: iterable
qa_check: personalisation_syntax
version: "1.0"
---

# ESP: Iterable — Handlebars Personalisation Reference

**Language:** Handlebars.js (extended with Iterable custom helpers)
**Delimiters:** `{{ }}` user/event data · `[[ ]]` data feed / catalog data
**Case-sensitive:** Yes
**Docs:** https://support.iterable.com/hc/en-us/articles/205480365-Handlebars-in-Iterable

---

## SECTIONS
1. [User Profile Fields](#1-user-profile-fields)
2. [Special Field Name Syntax](#2-special-field-name-syntax)
3. [Built-in System Variables](#3-built-in-system-variables)
4. [Event / Trigger Data](#4-event--trigger-data)
5. [Conditional Logic](#5-conditional-logic)
6. [Comparison Helpers](#6-comparison-helpers)
7. [String Helpers](#7-string-helpers)
8. [Date Helpers](#8-date-helpers)
9. [Number & Math Helpers](#9-number--math-helpers)
10. [Array / List Helpers](#10-array--list-helpers)
11. [Loops — each](#11-loops--each)
12. [Data Feeds & Catalog](#12-data-feeds--catalog)
13. [Snippets (Reusable Blocks)](#13-snippets-reusable-blocks)
14. [Skip Send Logic](#14-skip-send-logic)
15. [Whitespace Control](#15-whitespace-control)
16. [Advanced Patterns](#16-advanced-patterns)
17. [Fallback Patterns](#17-fallback-patterns)
18. [Gotchas & Debugging](#18-gotchas--debugging)

---

## 1. User Profile Fields

Standard fields from the user's Iterable profile:

```handlebars
{{firstName}}
{{lastName}}
{{email}}
{{userId}}
{{phoneNumber}}

<!-- Explicit profile namespace (same data) -->
{{profile.firstName}}
{{profile.lastName}}
{{profile.email}}
{{profile.phoneNumber}}

<!-- Custom profile fields -->
{{profile.loyaltyTier}}
{{profile.totalSpend}}
{{profile.accountStatus}}
{{profile.preferredStore}}
{{profile.referralCode}}
{{profile.memberSince}}
{{profile.country}}
{{profile.city}}
{{profile.language}}
```

---

## 2. Special Field Name Syntax

When a field name contains **spaces, starts with a number, or uses reserved characters**, wrap in `[fieldname]`:

```handlebars
{{[First Name]}}               <!-- Space in field name -->
{{[Last Name]}}
{{[1stOrderDate]}}             <!-- Starts with a number -->
{{profile.[Loyalty Tier]}}     <!-- Custom profile field with spaces -->
{{profile.[member-since]}}     <!-- Hyphen in field name -->
{{dataFields.[order-id]}}      <!-- Event data field with hyphen -->
```

---

## 3. Built-in System Variables

Available in all Iterable message types:

```handlebars
{{campaignName}}               <!-- Name of the campaign -->
{{campaignId}}                 <!-- Campaign ID (numeric) -->
{{templateName}}               <!-- Template name -->
{{templateId}}                 <!-- Template ID (numeric) -->
{{messageId}}                  <!-- Unique message ID for this send -->
{{now}}                        <!-- Current datetime (UTC) -->
{{companyName}}                <!-- From Iterable project settings -->
{{unsubscribeUrl}}             <!-- Unsubscribe link (required) -->
```

---

## 4. Event / Trigger Data

When a campaign is triggered by an event (custom event, Iterable event, or purchase), the event's data is available under `dataFields`:

```handlebars
<!-- Generic access -->
{{dataFields.fieldName}}

<!-- Order / purchase event -->
{{dataFields.orderId}}
{{dataFields.total}}
{{dataFields.discountCode}}
{{dataFields.shippingAddress}}

<!-- Items array (first item) -->
{{dataFields.items.[0].name}}
{{dataFields.items.[0].price}}
{{dataFields.items.[0].imageUrl}}
{{dataFields.items.[0].url}}
{{dataFields.items.[0].quantity}}
{{dataFields.items.[0].sku}}

<!-- Cart / abandon event -->
{{dataFields.cartTotal}}
{{dataFields.cartUrl}}
{{dataFields.itemCount}}

<!-- Browse / view event -->
{{dataFields.productName}}
{{dataFields.productUrl}}
{{dataFields.productImageUrl}}
{{dataFields.productPrice}}
```

---

## 5. Conditional Logic

### Basic if / else

```handlebars
{{#if firstName}}
  Hello, {{firstName}}!
{{else}}
  Hello, Valued Customer!
{{/if}}
```

### unless (inverse of if)

```handlebars
{{#unless profile.emailOptOut}}
  <p>You're receiving exclusive email offers.</p>
{{/unless}}
```

### Nested conditionals

```handlebars
{{#if profile.loyaltyTier}}
  {{#ifEq profile.loyaltyTier "Platinum"}}
    <div class="tier-platinum">Platinum member benefit</div>
  {{else}}
    <div class="tier-standard">Loyalty member offer</div>
  {{/ifEq}}
{{else}}
  <div class="tier-none">Join our loyalty programme</div>
{{/if}}
```

---

## 6. Comparison Helpers

All comparison helpers follow the pattern: `{{#helperName a b}}…{{else}}…{{/helperName}}`

### ifEq — equal

```handlebars
{{#ifEq profile.loyaltyTier "Gold"}}
  Gold member exclusive
{{else}}
  Standard offer
{{/ifEq}}

{{#ifEq profile.country "GB"}}
  <p>Free UK delivery on orders over £50.</p>
{{/ifEq}}
```

### ifGt — greater than

```handlebars
{{#ifGt dataFields.total 100}}
  Free shipping included!
{{else}}
  Add more to qualify for free shipping.
{{/ifGt}}
```

### ifLt — less than

```handlebars
{{#ifLt profile.loyaltyPoints 100}}
  You're {{subtract 100 profile.loyaltyPoints}} points away from Silver tier.
{{/ifLt}}
```

### ifGte — greater than or equal

```handlebars
{{#ifGte profile.totalOrders 10}}
  Thank you for your continued loyalty.
{{/ifGte}}
```

### ifLte — less than or equal

```handlebars
{{#ifLte dataFields.itemsRemaining 5}}
  Only {{dataFields.itemsRemaining}} left in stock — hurry!
{{/ifLte}}
```

### All comparison helpers

| Helper | Operator | Example |
|--------|----------|---------|
| `{{#ifEq a b}}` | `a == b` | String or number equality |
| `{{#ifNotEq a b}}` | `a != b` | Not equal |
| `{{#ifGt a b}}` | `a > b` | Greater than |
| `{{#ifGte a b}}` | `a >= b` | Greater than or equal |
| `{{#ifLt a b}}` | `a < b` | Less than |
| `{{#ifLte a b}}` | `a <= b` | Less than or equal |

---

## 7. String Helpers

```handlebars
{{capitalize firstName}}                        <!-- john → John -->
{{upper firstName}}                             <!-- john → JOHN -->
{{lower firstName}}                             <!-- JOHN → john -->
{{slugify profile.productName}}                 <!-- "Blue Shoes" → "blue-shoes" -->
{{truncate profile.bio 150}}                    <!-- Truncate at 150 chars -->
{{trim profile.rawField}}                       <!-- Strip surrounding whitespace -->
{{replace profile.text "old" "new"}}            <!-- String replace -->
{{join dataFields.tags ", "}}                   <!-- Array to comma-separated string -->
{{encode profile.trackingParam}}                <!-- URL-encode -->
{{encodeBase64 profile.rawValue}}               <!-- Base64 encode -->
{{decodeBase64 profile.encoded}}                <!-- Base64 decode -->
{{md5 profile.email}}                           <!-- MD5 hash (for Gravatar etc.) -->
{{sha256 profile.value}}                        <!-- SHA-256 hash -->
{{formatNumber profile.memberNumber 6}}         <!-- Zero-pad to 6 digits: 000042 -->
{{length dataFields.items}}                     <!-- Array length -->
{{lookup dataFields.items 0}}                   <!-- Get item at index -->

<!-- Conditional text helpers -->
{{defaultIfEmpty firstName "Friend"}}           <!-- Fallback if empty -->
{{#ifEq profile.gender "M"}}Mr{{else}}Ms{{/ifEq}} <!-- Inline gender salutation -->
```

---

## 8. Date Helpers

```handlebars
<!-- Format a profile or event date field -->
{{formatDate profile.memberSince "MMMM d, yyyy"}}    <!-- January 15, 2024 -->
{{formatDate profile.memberSince "dd/MM/yyyy"}}       <!-- 15/01/2024 -->
{{formatDate profile.memberSince "MMMM yyyy"}}        <!-- January 2024 -->
{{formatDate profile.memberSince "EEE, MMM d"}}       <!-- Mon, Jan 15 -->
{{formatDate dataFields.orderDate "MMMM d"}}

<!-- Format system date (now) -->
{{formatDate now "MMMM d, yyyy"}}
{{formatDate now "yyyy"}}
{{formatDate now "MMMM"}}

<!-- Date arithmetic -->
{{addDays now 7}}                              <!-- Date 7 days from now -->
{{addDays now -30}}                            <!-- Date 30 days ago -->
{{subtractDays now 14}}                        <!-- 14 days ago -->
{{addDays dataFields.orderDate 5}}             <!-- 5 days after order date -->

<!-- Combine arithmetic and formatting -->
{{formatDate (addDays now 7) "MMMM d, yyyy"}} <!-- e.g. "March 20, 2026" -->

<!-- Days between two dates -->
{{daysBetween profile.memberSince now}}        <!-- Integer days since signup -->
{{daysBetween now dataFields.expiryDate}}      <!-- Days until expiry -->
```

**Java SimpleDateFormat codes:**

| Code | Output |
|------|--------|
| `yyyy` | 2024 |
| `yy` | 24 |
| `MM` | 01 |
| `MMM` | Jan |
| `MMMM` | January |
| `dd` | 15 |
| `d` | 15 (no leading zero) |
| `EEE` | Mon |
| `EEEE` | Monday |
| `HH` | 14 (24h) |
| `hh` | 02 (12h) |
| `mm` | 30 |
| `ss` | 00 |
| `a` | AM/PM |

---

## 9. Number & Math Helpers

```handlebars
{{formatNumber dataFields.price 2}}            <!-- 12.50 (2 decimal places) -->
{{formatNumber dataFields.price 0}}            <!-- 13 (rounded, no decimals) -->
{{formatCurrency dataFields.price "USD"}}      <!-- $12.50 -->
{{formatCurrency dataFields.price "GBP"}}      <!-- £12.50 -->
{{formatCurrency dataFields.price "EUR"}}      <!-- €12.50 -->

{{math dataFields.qty '*' dataFields.price}}   <!-- Multiply -->
{{math dataFields.total '-' dataFields.discount}} <!-- Subtract -->
{{math dataFields.total '+' 10}}               <!-- Add -->
{{math dataFields.total '/' 100}}              <!-- Divide -->
{{math dataFields.total '%' 3}}                <!-- Modulo -->

{{round dataFields.rating}}                    <!-- Round to nearest int -->
{{ceil dataFields.partial}}                    <!-- Round up -->
{{floor dataFields.partial}}                   <!-- Round down -->
{{abs dataFields.difference}}                  <!-- Absolute value -->

{{add a b}}                                    <!-- Alias for math a '+' b -->
{{subtract a b}}                               <!-- Alias for math a '-' b -->
{{multiply a b}}                               <!-- Alias for math a '*' b -->
{{divide a b}}                                 <!-- Alias for math a '/' b -->
```

---

## 10. Array / List Helpers

```handlebars
{{length dataFields.items}}                    <!-- Count of items in array -->
{{lookup dataFields.items 0}}                  <!-- Get item at index (returns object) -->

<!-- Min/max helpers (find item with lowest/highest value of a field) -->
{{#minInList dataFields.items "price"}}
  Lowest priced item: {{name}} at £{{formatNumber price 2}}
{{/minInList}}

{{#maxInList dataFields.items "price"}}
  Most expensive: {{name}} at £{{formatNumber price 2}}
{{/maxInList}}

<!-- First/last -->
{{#each (slice dataFields.items 0 1)}}
  {{name}}                                     <!-- First item name -->
{{/each}}
```

---

## 11. Loops — each

### Basic product loop

```handlebars
{{#each dataFields.items}}
  <tr>
    <td><img src="{{imageUrl}}" width="80" /></td>
    <td>{{name}}</td>
    <td>{{quantity}}</td>
    <td>£{{formatNumber price 2}}</td>
  </tr>
{{/each}}
```

### @index for position

```handlebars
{{#each dataFields.items}}
  <p>{{@index}}. {{name}}</p>     <!-- @index is 0-based -->
{{/each}}
```

### Limit to first N items (slice)

```handlebars
{{#each (slice dataFields.items 0 3)}}
  {{name}}
{{/each}}
```

### Check if array is not empty

```handlebars
{{#if dataFields.items}}
  {{#each dataFields.items}}
    <li>{{name}}</li>
  {{/each}}
{{else}}
  <p>No items to display.</p>
{{/if}}
```

### Nested loop (array within array)

```handlebars
{{#each dataFields.orders}}
  <p>Order {{orderId}}</p>
  {{#each items}}
    <p>— {{name}}</p>
  {{/each}}
{{/each}}
```

---

## 12. Data Feeds & Catalog

Data feeds (external content via API) and Catalog (Iterable's product catalog) use `[[ ]]` double square bracket delimiters to distinguish them from user/event data.

### Catalog item access

```handlebars
[[catalog_item.field_name]]
[[catalog_item.productName]]
[[catalog_item.price]]
[[catalog_item.imageUrl]]
[[catalog_item.productUrl]]
[[catalog_item.description]]
[[catalog_item.category]]
[[catalog_item.stockLevel]]
```

### Data feed access

```handlebars
[[feed_name.fieldName]]
[[recommendations.items.[0].productName]]
[[recommendations.items.[0].imageUrl]]
[[recommendations.items.[0].price]]
```

### Loop over data feed items

```handlebars
{{#each recommendations.items}}
  <div class="reco-card">
    <img src="[[recommendations.items.{{@index}}.imageUrl]]" />
    <p>[[recommendations.items.{{@index}}.name]]</p>
  </div>
{{/each}}
```

> **Note:** Data feed and catalog data are fetched at **send time** and injected before Handlebars renders. `{{ }}` and `[[ ]]` tags are processed sequentially — feed data resolves first.

---

## 13. Snippets (Reusable Blocks)

Snippets are reusable content blocks stored in Iterable (**Content > Snippets**). They support full Handlebars + HTML + CSS.

### Using a snippet in a template

```handlebars
{{snippet "snippetName"}}

<!-- With data -->
{{snippet "productCard" productName=dataFields.productName imageUrl=dataFields.imageUrl}}
```

### Inside a snippet — variables are passed via context

```handlebars
<!-- Inside snippet "productCard" -->
<div class="product-card">
  <img src="{{imageUrl}}" alt="{{productName}}" />
  <p>{{productName}}</p>
</div>
```

---

## 14. Skip Send Logic

Suppress the send for this specific user without aborting the campaign:

```handlebars
<!-- Skip if user has no email opt-in -->
{{#unless profile.emailOptIn}}
  {{sendSkip cause="Not opted in"}}
{{/unless}}

<!-- Skip if critical data is missing -->
{{#unless dataFields.orderId}}
  {{sendSkip cause="No order ID"}}
{{/unless}}

<!-- Skip if order was too long ago -->
{{#ifGt (daysBetween dataFields.orderDate now) 30}}
  {{sendSkip cause="Order older than 30 days"}}
{{/ifGt}}
```

---

## 15. Whitespace Control

Add `~` immediately inside braces to strip surrounding whitespace:

```handlebars
{{~firstName~}}            <!-- No whitespace before or after -->
{{~#if profile.tier~}}     <!-- No whitespace around block tags -->
  Tier content
{{~/if~}}

<!-- Useful for generating clean CSV or URL strings -->
{{firstName}}{{~','~}}{{lastName}}{{~','~}}{{email}}
```

---

## 16. Advanced Patterns

### Personalised subject line

```
Subject: {{firstName}}, you left something in your cart 🛒
```

### Dynamic hero image by loyalty tier

```handlebars
{{#ifEq profile.loyaltyTier "Platinum"}}
  <img src="https://cdn.example.com/hero-platinum.jpg" alt="Platinum offer" />
{{else}}
  {{#ifEq profile.loyaltyTier "Gold"}}
    <img src="https://cdn.example.com/hero-gold.jpg" alt="Gold offer" />
  {{else}}
    <img src="https://cdn.example.com/hero-standard.jpg" alt="Offer" />
  {{/ifEq}}
{{/ifEq}}
```

### Order receipt

```handlebars
<p>Order #{{dataFields.orderId}} — {{formatDate dataFields.orderDate "MMMM d, yyyy"}}</p>

<table>
  <thead>
    <tr><th>Product</th><th>Qty</th><th>Price</th></tr>
  </thead>
  <tbody>
    {{#each dataFields.items}}
    <tr>
      <td>{{name}}</td>
      <td>{{quantity}}</td>
      <td>{{formatCurrency price "GBP"}}</td>
    </tr>
    {{/each}}
  </tbody>
  <tfoot>
    <tr>
      <td colspan="2"><strong>Total</strong></td>
      <td><strong>{{formatCurrency dataFields.total "GBP"}}</strong></td>
    </tr>
  </tfoot>
</table>
```

### Days since signup / loyalty message

```handlebars
{{#ifGte (daysBetween profile.signupDate now) 365}}
  🎉 Happy 1-year anniversary, {{firstName}}!
{{else}}
  {{#ifGte (daysBetween profile.signupDate now) 30}}
    You've been with us for {{daysBetween profile.signupDate now}} days!
  {{/ifGte}}
{{/ifGte}}
```

### Estimated delivery date

```handlebars
<p>Estimated delivery: <strong>{{formatDate (addDays now 5) "EEEE, MMMM d"}}</strong></p>
```

### Language-based greeting

```handlebars
{{#ifEq profile.language "fr"}}
  Bonjour {{defaultIfEmpty firstName "cher client"}} !
{{else}}
  {{#ifEq profile.language "de"}}
    Hallo {{defaultIfEmpty firstName "Kunde"}}!
  {{else}}
    Hello {{defaultIfEmpty firstName "there"}}!
  {{/ifEq}}
{{/ifEq}}
```

---

## 17. Fallback Patterns

| Scenario | Handlebars |
|----------|-----------|
| First name | `{{defaultIfEmpty firstName "Friend"}}` |
| Profile field | `{{defaultIfEmpty profile.loyaltyTier "Standard"}}` |
| Event field | `{{defaultIfEmpty dataFields.orderId "N/A"}}` |
| Nested fallback | `{{#if firstName}}{{firstName}}{{else}}there{{/if}}` |
| Image URL | `{{defaultIfEmpty dataFields.imageUrl "https://cdn.example.com/default.jpg"}}` |
| Price | `{{formatCurrency (defaultIfEmpty dataFields.price 0) "GBP"}}` |

---

## 18. Gotchas & Debugging

| Issue | Cause | Fix |
|-------|-------|-----|
| Field renders blank | Wrong field name or case | Field names are case-sensitive — copy exact key from user profile |
| `[[ ]]` data not populating | Feed not connected to campaign | Configure Data Feed in campaign settings |
| Array index out of bounds | Items array shorter than expected | Check `{{#if dataFields.items}}` before accessing `.[0]` |
| `@index` not available | Outside `{{#each}}` block | Only available inside an `{{#each}}` loop |
| `sendSkip` not firing | Placed outside Handlebars | Must be inside `{{ }}` tags, not inside HTML comment |
| Date format wrong | Using wrong format codes | Iterable uses Java SimpleDateFormat — not PHP or Moment.js |
| Comparison helper not working | Spaces or quotes issue | Ensure string literals are in quotes: `{{#ifEq a "value"}}` |
| Snippet not rendering | Wrong snippet name | Names are case-sensitive — match exactly |
| `{{ }}` and `[[ ]]` conflict | Feed data referencing user data keys | Keep feed data keys distinct from user profile keys |
| Whitespace in output | No whitespace control | Add `~` to tags: `{{~field~}}` |

---

## QA Rule Mapping

This section maps the reference material above to executable QA engine rules.

### Rules Applied to Iterable Handlebars Templates

| Rule ID | Group | Check | Deduction | Applies When |
|---------|-------|-------|-----------|-------------|
| ps-delimiter-unbalanced | delimiter_balance | Delimiter pairs balanced | -0.15 | Unclosed `{{ }}` or `{{# }}…{{/ }}` |
| ps-conditional-unbalanced | delimiter_balance | Conditional blocks balanced | -0.15 | Unclosed `{{#if}}…{{/if}}` |
| ps-fallback-missing | fallback_completeness | Output tags have defaults | -0.05 | Output tag without `{{defaultIfEmpty}}` helper |
| ps-fallback-empty | fallback_completeness | Fallback values non-empty | -0.03 | Empty string fallback `{{defaultIfEmpty "" ""}}` |
| ps-syntax-other | syntax_correctness | Handlebars syntax well-formed | -0.10 | Malformed helper invocations |
| ps-nesting-depth | best_practices | Nesting ≤ 3 levels | -0.03 | Nested `{{#if}}` > 3 deep |
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
