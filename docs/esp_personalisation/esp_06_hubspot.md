---
level: L4
type: reference
domain: personalisation
platform: hubspot
qa_check: personalisation_syntax
version: "1.0"
---

# ESP: HubSpot — HubL Personalisation Reference

**Language:** HubL (HubSpot's Jinja2-based templating language)
**Delimiters:** `{{ }}` output · `{% %}` logic
**Case-sensitive:** No for variable names, but property internal names must match exactly
**Docs:** https://developers.hubspot.com/docs/cms/hubl · https://knowledge.hubspot.com/email/personalize-your-emails

---

## SECTIONS
1. [Contact Personalisation Tokens](#1-contact-personalisation-tokens)
2. [Company Tokens](#2-company-tokens)
3. [Deal Tokens (Automated Only)](#3-deal-tokens-automated-only)
4. [Ticket Tokens (Automated Only)](#4-ticket-tokens-automated-only)
5. [Owner Tokens](#5-owner-tokens)
6. [Office Location Tokens](#6-office-location-tokens)
7. [Subscription & Utility Tokens](#7-subscription--utility-tokens)
8. [Conditional Logic](#8-conditional-logic)
9. [Filters](#9-filters)
10. [Smart Content Rules (No-Code)](#10-smart-content-rules-no-code)
11. [Advanced Patterns](#11-advanced-patterns)
12. [Fallback Patterns](#12-fallback-patterns)
13. [Finding Internal Property Names](#13-finding-internal-property-names)
14. [Gotchas & Debugging](#14-gotchas--debugging)

---

## 1. Contact Personalisation Tokens

> **Syntax note:** HubSpot requires a space inside the double braces: `{{ contact.firstname }}` not `{{contact.firstname}}`.

### Identity

```
{{ contact.firstname }}
{{ contact.lastname }}
{{ contact.email }}
{{ contact.phone }}
{{ contact.mobilephone }}
{{ contact.salutation }}              <!-- Mr, Mrs, Dr etc. -->
{{ contact.jobtitle }}
{{ contact.department }}
```

### Company & Professional

```
{{ contact.company }}
{{ contact.industry }}
{{ contact.website }}
{{ contact.linkedin_bio }}
{{ contact.twitterhandle }}
{{ contact.numemployees }}
{{ contact.annualrevenue }}
```

### Location

```
{{ contact.city }}
{{ contact.state }}
{{ contact.zip }}
{{ contact.country }}
{{ contact.address }}
```

### Lifecycle & CRM

```
{{ contact.lifecyclestage }}          <!-- lead, customer, evangelist, etc. -->
{{ contact.hs_lead_status }}          <!-- New, Open, In Progress, etc. -->
{{ contact.lead_source }}
{{ contact.hs_analytics_source }}
{{ contact.hs_email_sends_since_last_engagement }}
{{ contact.hs_email_open }}
{{ contact.hs_email_click }}
{{ contact.hs_email_bounce }}
{{ contact.hs_email_optout }}
{{ contact.notes_last_updated }}
```

### Dates

```
{{ contact.createdate }}
{{ contact.closedate }}
{{ contact.hs_last_sales_activity_timestamp }}
{{ contact.recent_conversion_date }}
{{ contact.first_conversion_date }}
```

### Custom properties

Use the **internal property name** (found via the `</>` icon in property settings):

```
{{ contact.my_custom_property }}
{{ contact.loyalty_tier }}
{{ contact.promo_code }}
{{ contact.account_id }}
{{ contact.preferred_location }}
```

---

## 2. Company Tokens

```
{{ company.name }}
{{ company.domain }}
{{ company.phone }}
{{ company.website }}
{{ company.industry }}
{{ company.description }}
{{ company.city }}
{{ company.state }}
{{ company.zip }}
{{ company.country }}
{{ company.address }}
{{ company.address2 }}
{{ company.numberofemployees }}
{{ company.annualrevenue }}
{{ company.founded_year }}
{{ company.type }}
{{ company.linkedin_company_page }}
{{ company.createdate }}
```

---

## 3. Deal Tokens (Automated Only)

Deal tokens are only available in **deal-based workflows** (enrolled from a Deal record).

```
{{ deal.dealname }}
{{ deal.dealstage }}
{{ deal.pipeline }}
{{ deal.amount }}
{{ deal.closedate }}
{{ deal.deal_currency_code }}
{{ deal.description }}
{{ deal.dealtype }}
{{ deal.num_associated_contacts }}
{{ deal.hs_lastmodifieddate }}
```

---

## 4. Ticket Tokens (Automated Only)

Ticket tokens are only available in **ticket-based workflows**.

```
{{ ticket.subject }}
{{ ticket.content }}
{{ ticket.hs_ticket_id }}
{{ ticket.hs_ticket_priority }}       <!-- LOW, MEDIUM, HIGH, URGENT -->
{{ ticket.hs_pipeline_stage }}
{{ ticket.hs_pipeline }}
{{ ticket.createdate }}
{{ ticket.source_type }}
{{ ticket.hs_resolution }}
```

---

## 5. Owner Tokens

Pulls data from the **Contact Owner** (HubSpot user assigned to the contact).

```
{{ owner.firstname }}
{{ owner.lastname }}
{{ owner.email }}
{{ owner.phone }}
{{ owner.mobile }}
{{ owner.fullname }}
{{ owner.signature }}                 <!-- Owner's configured email signature -->
{{ owner.avatar }}                    <!-- Owner's profile photo -->
{{ owner.jobtitle }}
{{ owner.linkedin_url }}
{{ owner.calendly_url }}              <!-- If configured as custom prop -->
```

---

## 6. Office Location Tokens

Based on **HubSpot Account > Office Locations**:

```
{{ office_location.name }}
{{ office_location.phone }}
{{ office_location.address }}
{{ office_location.address2 }}
{{ office_location.city }}
{{ office_location.state }}
{{ office_location.zip }}
{{ office_location.country }}
{{ office_location.email }}
```

---

## 7. Subscription & Utility Tokens

```
{{ unsubscribe_link }}                <!-- Unsubscribe URL (required) -->
{{ unsubscribe_link_all }}            <!-- Unsubscribe from all emails -->
{{ subscription_preferences_link }}  <!-- Manage email preferences page -->
{{ view_as_webpage_link }}            <!-- View email in browser -->
{{ site_settings.company_name }}      <!-- Company name from settings -->
{{ site_settings.company_street_address_1 }}
{{ site_settings.company_street_address_2 }}
{{ site_settings.company_city }}
{{ site_settings.company_state }}
{{ site_settings.company_zip }}
{{ site_settings.company_country }}
```

---

## 8. Conditional Logic

### Basic if / else / elif

```django
{% if contact.firstname %}
  Hello, {{ contact.firstname }}!
{% else %}
  Hello there!
{% endif %}
```

### Lifecycle stage based content

```django
{% if contact.lifecyclestage == 'customer' %}
  <p>Thank you for being a customer. Here's your loyalty offer.</p>
{% elif contact.lifecyclestage == 'lead' %}
  <p>Ready to take the next step? Here's an exclusive intro deal.</p>
{% elif contact.lifecyclestage == 'opportunity' %}
  <p>We're so close — here's a little nudge to help you decide.</p>
{% else %}
  <p>Discover what we can offer you.</p>
{% endif %}
```

### Lead status check

```django
{% if contact.hs_lead_status == 'NEW' %}
  Welcome to our community!
{% elif contact.hs_lead_status == 'OPEN' %}
  We're looking forward to connecting with you.
{% elif contact.hs_lead_status == 'IN_PROGRESS' %}
  Great progress — let's keep going.
{% endif %}
```

### Company size branching

```django
{% if contact.numemployees > 1000 %}
  <p>Enterprise pricing applies — let's talk.</p>
{% elif contact.numemployees > 100 %}
  <p>Scale your team with our Business plan.</p>
{% else %}
  <p>Our Starter plan was built for growing teams like yours.</p>
{% endif %}
```

### Null / empty check

```django
{% if contact.phone %}
  Call us: {{ contact.phone }}
{% endif %}

{% if not contact.company %}
  We'd love to know more about your organisation.
{% endif %}
```

### Owner token with fallback

```django
{% if owner.firstname %}
  Your account manager, {{ owner.firstname }}, is here to help.
  <a href="mailto:{{ owner.email }}">Get in touch</a>
{% else %}
  Our team is here to help.
  <a href="mailto:hello@example.com">Get in touch</a>
{% endif %}
```

---

## 9. Filters

### String filters

```django
{{ contact.firstname | capitalize }}           <!-- John -->
{{ contact.firstname | upper }}                <!-- JOHN -->
{{ contact.firstname | lower }}                <!-- john -->
{{ contact.firstname | title }}                <!-- Title Case -->
{{ contact.firstname | default('Friend') }}    <!-- Fallback if empty -->
{{ contact.company | truncate(30) }}           <!-- Truncate with ... -->
{{ contact.company | truncate(30, '…') }}      <!-- Custom ellipsis -->
{{ contact.firstname | trim }}                 <!-- Strip whitespace -->
{{ contact.linkedin_bio | striptags }}         <!-- Remove HTML -->
{{ contact.description | wordcount }}          <!-- Word count -->
{{ contact.firstname | length }}               <!-- Character count -->
{{ contact.website | replace('http://', 'https://') }}
```

### Number filters

```django
{{ contact.annualrevenue | int }}              <!-- Convert to integer -->
{{ deal.amount | float }}                      <!-- Convert to float -->
{{ deal.amount | round }}                      <!-- Round to nearest int -->
{{ deal.amount | round(2) }}                   <!-- Round to 2 decimal places -->
{{ deal.amount | format_currency('USD') }}     <!-- $1,250.00 -->
{{ deal.amount | format_currency('GBP') }}     <!-- £1,250.00 -->
{{ contact.numemployees | filesizeformat }}    <!-- (non-standard — avoid) -->
```

### Date filters

```django
{{ contact.createdate | datetimeformat('%B %d, %Y') }}   <!-- January 15, 2024 -->
{{ contact.createdate | datetimeformat('%d/%m/%Y') }}    <!-- 15/01/2024 -->
{{ contact.createdate | datetimeformat('%B %Y') }}       <!-- January 2024 -->
{{ contact.createdate | datetimeformat('%A, %B %d') }}   <!-- Monday, January 15 -->
{{ deal.closedate | datetimeformat('%B %d, %Y') }}
```

**strftime format codes:**

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
| `%H` | 14 (24h) |
| `%I` | 02 (12h) |
| `%M` | 30 (minutes) |
| `%p` | AM/PM |

---

## 10. Smart Content Rules (No-Code)

Smart content lets you show different email modules to different contacts based on rules — no template code required.

**Available smart rule types:**

| Rule Type | Logic Based On |
|-----------|---------------|
| Contact list membership | Is/is not a member of a specific list |
| Lifecycle stage | Lead, MQL, SQL, Opportunity, Customer, etc. |
| Device type | Desktop, Mobile, Tablet |
| Country | Contact's country (from IP or property) |
| Referral source | Direct, Organic, Social, Email, Paid, etc. |
| Preferred language | Browser / contact language preference |

**How to set up:**

1. Add a content module to your email
2. Click the module → click **Make Smart**
3. Add rules and configure alternative content for each segment

Smart content rules are evaluated **at open time**, not at send time — perfect for time-sensitive offers.

---

## 11. Advanced Patterns

### Personalised subject line

```
Subject: {{ contact.firstname | default('Hey') }}, your trial ends soon
```

### Owner signature block

```django
{% if owner.firstname %}
<table>
  <tr>
    <td>
      <strong>{{ owner.firstname }} {{ owner.lastname }}</strong><br>
      {{ owner.jobtitle }}<br>
      <a href="mailto:{{ owner.email }}">{{ owner.email }}</a><br>
      {% if owner.phone %}{{ owner.phone }}{% endif %}
    </td>
  </tr>
</table>
{% else %}
<p>The {{ site_settings.company_name }} Team</p>
{% endif %}
```

### Deal-based renewal email

```django
Your renewal for <strong>{{ deal.dealname }}</strong> is coming up.
<br><br>
Current value: {{ deal.amount | format_currency('GBP') }}<br>
Renewal date: {{ deal.closedate | datetimeformat('%B %d, %Y') }}
<br><br>
{% if owner.firstname %}
  Your account manager {{ owner.firstname }} will be in touch shortly.
{% endif %}
```

### Industry-specific content

```django
{% if contact.industry == 'Technology' %}
  <img src="https://cdn.example.com/tech-hero.jpg" />
{% elif contact.industry == 'Financial Services' %}
  <img src="https://cdn.example.com/finance-hero.jpg" />
{% elif contact.industry == 'Healthcare' %}
  <img src="https://cdn.example.com/health-hero.jpg" />
{% else %}
  <img src="https://cdn.example.com/default-hero.jpg" />
{% endif %}
```

### Personalised CTA by lifecycle stage

```django
{% if contact.lifecyclestage == 'customer' %}
  <a href="https://app.example.com/account" class="btn">Access Your Account</a>
{% elif contact.lifecyclestage == 'opportunity' %}
  <a href="https://meetings.hubspot.com/{{ owner.username }}" class="btn">Book a Call</a>
{% else %}
  <a href="https://www.example.com/demo" class="btn">Request a Demo</a>
{% endif %}
```

---

## 12. Fallback Patterns

| Scenario | HubL |
|----------|------|
| First name | `{{ contact.firstname \| default('Friend') }}` |
| Company | `{{ contact.company \| default('your company') }}` |
| Owner name | `{% if owner.firstname %}{{ owner.firstname }}{% else %}our team{% endif %}` |
| Deal amount | `{{ deal.amount \| default(0) \| format_currency('GBP') }}` |
| Custom property | `{{ contact.loyalty_tier \| default('Standard') }}` |
| Date | `{% if contact.createdate %}{{ contact.createdate \| datetimeformat('%B %d, %Y') }}{% else %}recently{% endif %}` |

---

## 13. Finding Internal Property Names

HubSpot property **display names** and **internal names** often differ.

**To find the internal name:**
1. Go to **Settings > Properties** (Contact, Company, Deal, or Ticket)
2. Find the property
3. Click **Edit** → look for the **Internal name** field
4. Or click the `</>` code icon next to the property

**Common mismatches:**

| Display Name | Internal Name |
|--------------|---------------|
| First Name | `firstname` |
| Last Name | `lastname` |
| Job Title | `jobtitle` |
| Mobile Phone | `mobilephone` |
| Number of Employees | `numemployees` |
| Annual Revenue | `annualrevenue` |
| Lifecycle Stage | `lifecyclestage` |
| Lead Status | `hs_lead_status` |

---

## 14. Gotchas & Debugging

| Issue | Cause | Fix |
|-------|-------|-----|
| Token shows as `[Contact: First Name]` | Contact record has no value for this property | Add `\| default('fallback')` filter |
| Token renders literally | Missing space inside `{{ }}` | Use `{{ contact.firstname }}` not `{{contact.firstname}}` |
| Owner token blank | Contact has no owner assigned | Wrap in `{% if owner.firstname %}…{% endif %}` |
| Deal token blank | Email not triggered from deal workflow | Deal tokens only work in deal-based workflows |
| `| datetimeformat` fails | Property stores date as epoch milliseconds | HubSpot automatically converts — if still failing, check property type |
| Smart content not switching | Rule not evaluating as expected | Use **Preview as contact** and select a specific contact to test rules |
| Custom property blank | Wrong internal name | Verify via Settings > Properties > Internal Name |
| `| format_currency` wrong symbol | Wrong currency code | Use ISO 4217: `'GBP'`, `'USD'`, `'EUR'`, etc. |
| Conditional block not working | Comparing string to number | Ensure consistent types: `{{ contact.numemployees \| int }} > 100` |
| Preview shows fallback | Test contact has no data | Use a contact record with complete data for previewing |

---

## QA Rule Mapping

This section maps the reference material above to executable QA engine rules.

### Rules Applied to HubSpot HubL Templates

| Rule ID | Group | Check | Deduction | Applies When |
|---------|-------|-------|-----------|-------------|
| ps-delimiter-unbalanced | delimiter_balance | Delimiter pairs balanced | -0.15 | Unclosed `{{ }}` or `{% %}` |
| ps-conditional-unbalanced | delimiter_balance | Conditional blocks balanced | -0.15 | Unclosed `{% if %}…{% endif %}` |
| ps-fallback-missing | fallback_completeness | Output tags have defaults | -0.05 | Output tag without `| default()` filter |
| ps-fallback-empty | fallback_completeness | Fallback values non-empty | -0.03 | Empty string fallback `| default("")` |
| ps-syntax-liquid | syntax_correctness | HubL syntax well-formed | -0.10 | Dangling pipe, empty filter chain |
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
