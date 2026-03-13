---
level: L4
type: reference
domain: personalisation
platform: mailchimp
qa_check: personalisation_syntax
version: "1.0"
---

# ESP: Mailchimp — Merge Tags Personalisation Reference

**Language:** Mailchimp Merge Language (proprietary) + Handlebars (Transactional only)
**Delimiters:** `*|TAG|*` — asterisk + pipe
**Case-sensitive:** Yes — merge tags must match exactly
**Docs:** https://mailchimp.com/help/all-the-merge-tags-cheat-sheet/ · https://mailchimp.com/help/use-conditional-merge-tag-blocks/

---

## SECTIONS
1. [Contact / Subscriber Tags](#1-contact--subscriber-tags)
2. [Audience & Account Tags](#2-audience--account-tags)
3. [System & Campaign Tags](#3-system--campaign-tags)
4. [Date Tags](#4-date-tags)
5. [Conditional Merge Tags](#5-conditional-merge-tags)
6. [Group-Based Conditionals](#6-group-based-conditionals)
7. [Automation Email Tags](#7-automation-email-tags)
8. [RSS Feed Tags](#8-rss-feed-tags)
9. [Content Encoding Tags](#9-content-encoding-tags)
10. [Custom Field Tags](#10-custom-field-tags)
11. [Transactional (Mandrill) — Merge Language](#11-transactional-mandrill--merge-language)
12. [Transactional (Mandrill) — Handlebars](#12-transactional-mandrill--handlebars)
13. [Advanced Patterns](#13-advanced-patterns)
14. [Fallback Patterns](#14-fallback-patterns)
15. [Gotchas & Debugging](#15-gotchas--debugging)

---

## 1. Contact / Subscriber Tags

```
*|FNAME|*           <!-- First name -->
*|LNAME|*           <!-- Last name -->
*|EMAIL|*           <!-- Email address -->
*|PHONE|*           <!-- Phone number -->
*|ADDRESS|*         <!-- Full formatted postal address -->
*|ADDR1|*           <!-- Address line 1 -->
*|ADDR2|*           <!-- Address line 2 -->
*|CITY|*            <!-- City -->
*|STATE|*           <!-- State / region -->
*|ZIP|*             <!-- Postal code -->
*|COUNTRY|*         <!-- Country -->
*|BIRTHDAY|*        <!-- Birthday (if collected as BIRTHDAY field) -->
*|MMERGE1|*         <!-- First custom merge field -->
*|MMERGE2|*         <!-- Second custom merge field (and so on) -->
```

> Custom audience fields automatically get a merge tag based on their label. You can rename them in **Audience > Settings > Audience fields & tags**.

---

## 2. Audience & Account Tags

```
*|LIST:NAME|*               <!-- Audience/list name -->
*|LIST:COMPANY|*            <!-- Company in audience admin settings -->
*|LIST:PHONE|*              <!-- Phone in audience admin settings -->
*|LIST:ADDRESS|*            <!-- Address in audience admin settings -->
*|LIST:EMAIL|*              <!-- Email in audience admin settings -->
*|LIST:URL|*                <!-- Website URL in audience settings -->
*|LIST:DESCRIPTION|*        <!-- Audience description -->
*|LIST:SUBSCRIBE|*          <!-- Subscribe link -->
*|LIST:UNSUB|*              <!-- Unsubscribe URL (for footer) -->
*|MC_PREVIEW_TEXT|*         <!-- Email preview / preheader text -->
*|MC_SUBJECT|*              <!-- Email subject line -->
*|MC_LANGUAGE|*             <!-- Contact's language setting (e.g. en, fr, de) -->
*|MC_TOT_EMAILS|*           <!-- Total emails sent to this contact -->
*|MC_TOT_SENT|*             <!-- Total campaign emails sent (list-wide) -->
```

---

## 3. System & Campaign Tags

```
*|ARCHIVE|*                 <!-- View in browser / view online link -->
*|UNSUBSCRIBE|*             <!-- Unsubscribe link -->
*|UPDATE_PROFILE|*          <!-- Update profile / preferences link -->
*|UNSUB_LINK_SHORT|*        <!-- Short unsubscribe URL -->
*|FORWARD|*                 <!-- Forward to a friend link -->
*|REWARDS|*                 <!-- MonkeyRewards referral link -->
*|PROMO_CODE|*              <!-- Promo code (from Promo Code feature) -->
*|COUPON:|*                 <!-- WooCommerce coupon code -->
*|POLL:RATING:N|*           <!-- Star rating poll link (N = number of stars, 1–10) -->
*|SURVEY:|*                 <!-- Survey link -->
*|UNSUB_MAILTO:|*           <!-- Unsubscribe via email link -->
*|ABUSE_EMAIL|*             <!-- Abuse reporting email address -->
*|ACCOUNT_COMPANY|*         <!-- Company from administrator account settings -->
*|ACCOUNT_EMAIL|*           <!-- Admin email from account settings -->
*|ACCOUNT_URL|*             <!-- Admin website URL -->
*|ACCOUNT_PHONE|*           <!-- Admin phone number -->
*|ACCOUNT_ADDRESS|*         <!-- Admin postal address -->
```

---

## 4. Date Tags

```
*|DATE:F j, Y|*             <!-- January 15, 2024 -->
*|DATE:d/m/Y|*              <!-- 15/01/2024 -->
*|DATE:m/d/Y|*              <!-- 01/15/2024 -->
*|DATE:Y-m-d|*              <!-- 2024-01-15 (ISO) -->
*|DATE:l, F j|*             <!-- Monday, January 15 -->
*|DATE:F Y|*                <!-- January 2024 -->
*|DATE:D, d M Y|*           <!-- Mon, 15 Jan 2024 -->
*|CURRENT_YEAR|*            <!-- 2024 (just the year) -->
```

**Uses PHP date format codes:**

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
| `Y` | 4-digit year (2024) |
| `y` | 2-digit year (24) |
| `H` | 24h hour with leading zero |
| `G` | 24h hour without leading zero |
| `i` | Minutes (00–59) |

---

## 5. Conditional Merge Tags

Mailchimp supports `IF`, `ELSEIF`, `ELSE`, `IFNOT` conditional logic.

### Basic IF / ELSE

```
*|IF:FNAME|*
  Hello, *|FNAME|*!
*|ELSE:|*
  Hello, Friend!
*|END:IF|*
```

### IF with value comparison (equality)

```
*|IF:MC_LANGUAGE=fr|*
  Bonjour !
*|ELSEIF:MC_LANGUAGE=de|*
  Guten Tag!
*|ELSEIF:MC_LANGUAGE=es|*
  ¡Hola!
*|ELSE:|*
  Hello!
*|END:IF|*
```

### IF with numeric comparison

```
*|IF:TRANSACTIONS >= 20|*
  You're a VIP! Enjoy 40% off: *|COUPON40|*
*|ELSEIF:TRANSACTIONS >= 10|*
  Thanks for loyalty! 20% off: *|COUPON20|*
*|ELSE:|*
  Welcome! 10% off: *|COUPON10|*
*|END:IF|*
```

### IF with not-equal

```
*|IF:COUNTRY != US|*
  International shipping available!
*|ELSE:|*
  Free US shipping on orders over $50.
*|END:IF|*
```

### IFNOT (negative)

```
*|IFNOT:FNAME|*
  Please update your profile — we'd love to know your name!
*|END:IF|*
```

### Nested conditionals

```
*|IF:TRANSACTIONS >= 10|*
  *|IF:COUNTRY=US|*
    US VIP shipping included.
  *|ELSE:|*
    International VIP rate applies.
  *|END:IF|*
*|ELSE:|*
  Standard shipping rates apply.
*|END:IF|*
```

### Supported operators

| Operator | Use |
|----------|-----|
| *(no operator)* | Check if field has any value |
| `=` | Equal to |
| `!=` | Not equal to |
| `>` | Greater than |
| `<` | Less than |
| `>=` | Greater than or equal |
| `<=` | Less than or equal |

> **Important:** Use **number field type** in audience settings for numeric comparisons (`>`, `<`, `>=`, `<=`). Text fields may behave unexpectedly with numeric operators.

> **Important:** `IF` checks the entire string — `AND` and `OR` are **not** supported inside a single condition. Use nested `*|IF|*` blocks instead.

---

## 6. Group-Based Conditionals

Show content to contacts in specific audience groups:

```
*|INTERESTED:GroupCategory:GroupName|*
  Content for this group only.
*|END:INTERESTED|*

<!-- With ELSE for non-group members -->
*|INTERESTED:Customers:Wholesale|*
  Wholesale pricing enclosed.
*|ELSE:|*
  Shop our retail range.
*|END:INTERESTED|*

<!-- Multiple groups in one condition -->
*|INTERESTED:Customers:Wholesale,Repeat Buyers|*
  You're one of our best customers.
*|END:INTERESTED|*

<!-- Nested groups for unique per-group content -->
*|INTERESTED:Customers:Wholesale,Repeat Buyers|*
  *|INTERESTED:Customers:Wholesale|*
    You're a wholesale partner.
  *|END:INTERESTED|*
  *|INTERESTED:Customers:Repeat Buyers|*
    You're a loyal customer.
  *|END:INTERESTED|*
*|ELSE:|*
  We'd love to know more about you.
*|END:INTERESTED|*
```

---

## 7. Automation Email Tags

```
*|AUTOMATION:TOTALEMAILS|*        <!-- Total emails in automation sequence -->
*|AUTOMATION:CURRENT_EMAIL|*      <!-- Position of this email in sequence (1, 2, 3…) -->
*|AUTOMATION:NEXTEMAILDATE|*      <!-- Scheduled date of next email in sequence -->
*|AUTOMATION:PREVSUBJECT|*        <!-- Subject of previous email in sequence -->
*|AUTOMATION:NEXTSUBJECT|*        <!-- Subject of next email in sequence -->
```

---

## 8. RSS Feed Tags

### Feedblock (simplest approach)

```
*|RSSITEMS:|*
  <!-- RSS content auto-inserted by Mailchimp -->
*|END:RSSITEMS|*
```

### RSS channel tags (inside feedblock)

```
*|RSSITEMS:|*
*|RSS:TITLE|*                     <!-- Channel title -->
*|RSS:URL|*                       <!-- Channel URL -->
*|RSS:DATE:F j, Y|*               <!-- Channel publish date -->
*|RSS:DESCRIPTION|*               <!-- Channel description -->
*|RSSITEM:TITLE|*                 <!-- Item title -->
*|RSSITEM:URL|*                   <!-- Item URL -->
*|RSSITEM:CONTENT_FULL|*          <!-- Full item content -->
*|RSSITEM:CONTENT_SHORT|*         <!-- Truncated summary -->
*|RSSITEM:IMAGE|*                 <!-- Item featured image -->
*|RSSITEM:DATE:F j, Y|*           <!-- Item publish date -->
*|RSSITEM:AUTHOR|*                <!-- Item author -->
*|RSSITEM:CATEGORIES|*            <!-- Item categories -->
*|END:RSSITEMS|*
```

---

## 9. Content Encoding Tags

Modify how merge tag content is rendered:

```
*|HTML:FNAME|*          <!-- Render content as raw HTML (do not escape) -->
*|UNSUB:|*              <!-- Encode for use in URL -->
```

---

## 10. Custom Field Tags

Any audience field you create becomes a merge tag using its uppercase label:

```
*|BIRTHDAY|*            <!-- Field labelled "Birthday" -->
*|LASTPURCHASE|*        <!-- Field labelled "LastPurchase" -->
*|MEMBERID|*            <!-- Field labelled "MemberID" -->
*|LOYALTYTIER|*         <!-- Field labelled "LoyaltyTier" -->
*|PRODUCTURL|*          <!-- Field labelled "ProductURL" -->
*|COUPONCODE|*          <!-- Field labelled "CouponCode" -->
```

> Create custom fields in: **Audience > Settings > Audience fields & merge tags > Add a field**

---

## 11. Transactional (Mandrill) — Merge Language

Mailchimp Transactional (formerly Mandrill) uses the same `*|TAG|*` format but values are **passed in the API call at send time**, not pulled from an audience list.

```
*|FIRST_NAME|*          <!-- Passed as merge var in API call -->
*|ORDER_ID|*
*|ORDER_TOTAL|*
*|PRODUCT_NAME|*
*|TRACKING_URL|*
*|EXPIRY_DATE|*
```

### Conditional in Transactional

```
*|IF:ORDER_TOTAL >= 100|*
  Your order qualifies for free shipping.
*|ELSE:|*
  Add £*|REMAINING|* more for free shipping.
*|END:IF|*
```

---

## 12. Transactional (Mandrill) — Handlebars

Transactional also supports a custom Handlebars implementation (set `merge_language: "handlebars"` in the API):

```handlebars
{{ first_name }}
{{ order_id }}
{{ order_total }}

<!-- Conditional -->
{{#if vip_member}}
  <p>VIP exclusive offer enclosed.</p>
{{/if}}

{{#if first_name}}
  Hello, {{ first_name }}!
{{else}}
  Hello there!
{{/if}}

<!-- Loop -->
{{#each items}}
  <li>{{ name }} — {{ price }}</li>
{{/each}}

<!-- Unsubscribe helper -->
<a href="{{unsub_link 'https://yourapp.com/unsub'}}">Unsubscribe</a>
```

---

## 13. Advanced Patterns

### Personalised subject line

```
Subject: *|FNAME|*, here's what's new this week
```

### First name with fallback (conditional)

```
*|IF:FNAME|*Hello, *|FNAME|*,*|ELSE:|*Hello there,*|END:IF|*
```

### Language-based email content

```
*|IF:MC_LANGUAGE=fr|*
  <p>Bonjour *|FNAME|* !</p>
  <p>Voici vos offres exclusives.</p>
*|ELSEIF:MC_LANGUAGE=de|*
  <p>Hallo *|FNAME|*!</p>
  <p>Hier sind Ihre exklusiven Angebote.</p>
*|ELSE:|*
  <p>Hello *|FNAME|*!</p>
  <p>Here are your exclusive offers.</p>
*|END:IF|*
```

### Tiered discount by purchase count

```
*|IF:PURCHASECOUNT >= 25|*
  <p>🏆 VIP: 50% off your next order.</p>
*|ELSEIF:PURCHASECOUNT >= 10|*
  <p>⭐ Loyal: 30% off your next order.</p>
*|ELSEIF:PURCHASECOUNT >= 1|*
  <p>Thank you! 15% off your next order.</p>
*|ELSE:|*
  <p>Welcome! 10% off your first order.</p>
*|END:IF|*
```

### Archive page — hide time-sensitive content

```
*|IF:ARCHIVE_PAGE|*
  <!-- Nothing shown in archived version -->
*|ELSE:|*
  <p>This offer expires *|DATE:F j, Y|*. Don't miss out!</p>
*|END:IF|*
```

### Dynamic product image from custom field

```html
<img src="*|PRODUCTIMGURL|*" alt="*|PRODUCTNAME|*" />
<p><strong>*|PRODUCTNAME|*</strong> — Only *|PRODUCTPRICE|* left in stock</p>
<a href="*|PRODUCTURL|*">Shop Now</a>
```

---

## 14. Fallback Patterns

| Scenario | Tag |
|----------|-----|
| First name fallback | `*|IF:FNAME|* *|FNAME|* *|ELSE:|* Friend *|END:IF|*` |
| Any field fallback | `*|IF:FIELDNAME|* *|FIELDNAME|* *|ELSE:|* Default Text *|END:IF|*` |
| Subject line | `Subject: *|FNAME|*, check this out` (Mailchimp leaves blank if missing) |
| Set default in audience | Audience > Audience fields > Edit field > Default merge tag value |

> **Best practice:** Set **Default merge tag values** in your audience settings. This fills tags globally rather than needing conditional logic in every email.

---

## 15. Gotchas & Debugging

| Issue | Cause | Fix |
|-------|-------|-----|
| `*|FNAME|*` shows literally in email | Merge tag not linked to field in audience | Check Audience Fields settings — tag must match field label |
| Numeric condition behaves wrong | Field type is set to Text | Change field type to Number in Audience > Audience fields |
| `IF` with AND/OR not working | AND/OR not supported in single condition | Use nested `*|IF|*` blocks |
| Conditional shows both branches | Incorrect operator or no space around `=` | Use `*|IF:FIELD=value|*` exactly — no extra spaces |
| Tag in subject line shows blank | Subscriber has no data for that field | Set a default value in audience field settings |
| Custom tag not populating | Tag name mismatch | Tag must be all caps, matching the field's merge tag name exactly |
| Group conditional not working | Group name has typo | Copy group name exactly from Audience > Groups |
| RSS content not loading | Feed URL changed or returning errors | Validate RSS feed URL returns valid XML |
| `MMERGE1` showing instead of field label | Merge tag not renamed after field creation | Rename in Audience fields settings |
| Handlebars not rendering (Transactional) | `merge_language` not set to `"handlebars"` in API | Set parameter in API call or account Sending Defaults |

---

## QA Rule Mapping

This section maps the reference material above to executable QA engine rules.

### Rules Applied to Mailchimp Merge Tag Templates

| Rule ID | Group | Check | Deduction | Applies When |
|---------|-------|-------|-----------|-------------|
| ps-delimiter-unbalanced | delimiter_balance | Delimiter pairs balanced | -0.15 | Unclosed `*|…|*` |
| ps-conditional-unbalanced | delimiter_balance | Conditional blocks balanced | -0.15 | Unclosed `*|IF:…|*…*|END:IF|*` |
| ps-fallback-missing | fallback_completeness | Output tags have defaults | -0.05 | Merge tag without `*|IF:FIELD|*…*|ELSE:|*…*|END:IF|*` wrapper |
| ps-fallback-empty | fallback_completeness | Fallback values non-empty | -0.03 | Empty ELSE branch `*|ELSE:|*…*|END:IF|*` |
| ps-syntax-other | syntax_correctness | Merge tag syntax well-formed | -0.10 | Malformed merge tag delimiters |
| ps-nesting-depth | best_practices | Nesting ≤ 3 levels | -0.03 | Nested `*|IF|*` > 3 deep |
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
