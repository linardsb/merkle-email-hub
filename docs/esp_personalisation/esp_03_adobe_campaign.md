---
level: L4
type: reference
domain: personalisation
platform: adobe_campaign
qa_check: personalisation_syntax
version: "1.0"
---

# ESP: Adobe Campaign — Personalisation Reference

**Products covered:** Campaign Classic v7 · Campaign v8 · Campaign Standard
**Language:** EL (Expression Language) · JavaScript (advanced)
**Delimiters:** `<%= field %>` output · `<% code %>` logic
**Case-sensitive:** Yes
**Docs:** https://experienceleague.adobe.com/en/docs/campaign

---

## SECTIONS
1. [Core Syntax](#1-core-syntax)
2. [Standard Recipient Fields](#2-standard-recipient-fields)
3. [Personalisation Blocks (Pre-built)](#3-personalisation-blocks-pre-built)
4. [JavaScript Expressions](#4-javascript-expressions)
5. [Conditional Logic](#5-conditional-logic)
6. [Variables & Calculated Fields](#6-variables--calculated-fields)
7. [Date Formatting](#7-date-formatting)
8. [String Operations](#8-string-operations)
9. [Dynamic Content (Conditional Blocks)](#9-dynamic-content-conditional-blocks)
10. [External File / Data Source](#10-external-file--data-source)
11. [Delivery & Campaign Metadata](#11-delivery--campaign-metadata)
12. [Campaign Standard vs Classic Differences](#12-campaign-standard-vs-classic-differences)
13. [Advanced Patterns](#13-advanced-patterns)
14. [Fallback Patterns](#14-fallback-patterns)
15. [Gotchas & Debugging](#15-gotchas--debugging)

---

## 1. Core Syntax

```html
<!-- Output a field value -->
<%= recipient.fieldName %>

<!-- Inline JavaScript expression -->
<%= recipient.age > 18 ? "adult" : "minor" %>

<!-- Multi-line JavaScript block -->
<%
  var name = recipient.firstName;
  var greeting = "Hello " + name;
%>
<%= greeting %>

<!-- Include a personalisation block -->
<%@ include view='blockName' %>
```

**Tag form:** `<%= ... %>` — evaluate and output
**Code form:** `<% ... %>` — execute but do not output
**Include form:** `<%@ include view='...' %>` — insert a pre-built block

---

## 2. Standard Recipient Fields

### Classic / v8 (recipient table)

```
<%= recipient.firstName %>
<%= recipient.lastName %>
<%= recipient.email %>
<%= recipient.gender %>              <!-- "M" or "F" -->
<%= recipient.birthDate %>
<%= recipient.age %>
<%= recipient.phone %>
<%= recipient.mobilePhone %>
<%= recipient.address.line1 %>
<%= recipient.address.line2 %>
<%= recipient.address.city %>
<%= recipient.address.state %>
<%= recipient.address.zipCode %>
<%= recipient.address.country %>
<%= recipient.language %>
<%= recipient.blacklisted %>         <!-- boolean -->
<%= recipient.emailOptOut %>         <!-- boolean -->
<%= recipient.created %>             <!-- creation date -->
<%= recipient.lastModified %>
<%= recipient.id %>                  <!-- internal ID -->
<%= recipient.@email %>              <!-- XPath alternative -->
```

### Nested / related objects

```
<%= recipient.company.name %>
<%= recipient.subscriptions[0].service.label %>
<%= recipient.orders[0].totalAmount %>
```

---

## 3. Personalisation Blocks (Pre-built)

Insert via: `<%@ include view='blockInternalName' %>`

```
<%@ include view='nms:unsubscriptionLink' %>     <!-- Unsubscribe link -->
<%@ include view='nms:mirrorPage' %>             <!-- View in browser link -->
<%@ include view='nms:optOutLink' %>             <!-- Opt-out link -->
<%@ include view='nms:socialNetworkSharing' %>   <!-- Social share buttons -->
<%@ include view='nms:trackableLink' %>          <!-- Tracked link wrapper -->
<%@ include view='nms:logo' %>                   <!-- Brand logo -->
<%@ include view='nms:formationFeedback' %>      <!-- Feedback form -->
```

### Custom personalisation block syntax

Custom blocks created in **Resources > Campaign Management > Personalisation blocks**:

```
<%@ include view='cus:myCustomBlock' %>
```

In the block's HTML, use standard personalisation tags. Call from email with:

```
<%@ include view='cus:myCustomBlock' %>
```

---

## 4. JavaScript Expressions

### String manipulation

```javascript
<%= recipient.firstName.toUpperCase() %>
<%= recipient.firstName.toLowerCase() %>
<%= recipient.firstName.charAt(0).toUpperCase() + recipient.firstName.slice(1).toLowerCase() %>
<%= (recipient.firstName || '').substring(0, 10) %>
<%= recipient.firstName + " " + recipient.lastName %>
<%= recipient.email.split('@')[1] %>             <!-- Get domain from email -->
```

### Null / empty guards

```javascript
<%= recipient.firstName || 'Customer' %>
<%= recipient.firstName ? recipient.firstName : 'Valued Customer' %>
<%= (recipient.firstName && recipient.firstName.length > 0) ? recipient.firstName : 'Friend' %>
```

### Number formatting

```javascript
<%= recipient.totalSpend.toFixed(2) %>
<%= Math.round(recipient.loyaltyPoints * 1.5) %>
<%= (recipient.balance / 100).toFixed(2) %>
```

---

## 5. Conditional Logic

### Simple if / else

```javascript
<% if (recipient.gender == 'M') { %>
  Dear Mr <%= recipient.lastName %>,
<% } else if (recipient.gender == 'F') { %>
  Dear Ms <%= recipient.lastName %>,
<% } else { %>
  Dear <%= recipient.firstName || 'Customer' %>,
<% } %>
```

### Membership / tier check

```javascript
<% if (recipient.loyaltyTier == 'Platinum') { %>
  <div class="platinum-block">Exclusive Platinum offer</div>
<% } else if (recipient.loyaltyTier == 'Gold') { %>
  <div class="gold-block">Gold member special</div>
<% } else { %>
  <div class="standard-block">Shop our latest range</div>
<% } %>
```

### Age-based content

```javascript
<% if (recipient.age >= 18 && recipient.age <= 27) { %>
  <img src="youth-banner.jpg" />
<% } else if (recipient.age > 27 && recipient.age <= 50) { %>
  <img src="adult-banner.jpg" />
<% } else if (recipient.age > 50) { %>
  <img src="senior-banner.jpg" />
<% } %>
```

### Null check before use

```javascript
<% if (recipient.firstName != null && recipient.firstName != '') { %>
  Hello, <%= recipient.firstName %>!
<% } else { %>
  Hello, Valued Customer!
<% } %>
```

---

## 6. Variables & Calculated Fields

```javascript
<%
  /* Declare and compute variables */
  var firstName   = recipient.firstName || 'Customer';
  var loyaltyStr  = recipient.loyaltyPoints + ' points';
  var discountPct = recipient.loyaltyPoints > 500 ? 20 : 10;

  /* Date math */
  var now         = new Date();
  var expiryDate  = new Date();
  expiryDate.setDate(now.getDate() + 30);

  /* Format expiry */
  var day   = expiryDate.getDate();
  var month = expiryDate.toLocaleString('en-GB', { month: 'long' });
  var year  = expiryDate.getFullYear();
  var expiryStr = day + ' ' + month + ' ' + year;
%>

Hello <%= firstName %>,
Your <%= loyaltyStr %> give you a <%= discountPct %>% discount, valid until <%= expiryStr %>.
```

---

## 7. Date Formatting

### Using formatDate() helper (Campaign Classic)

```javascript
<%= formatDate(recipient.birthDate, "%4Y/%2M/%2D") %>      <!-- 2024/01/15 -->
<%= formatDate(delivery.creation, "%2D %[month] %4Y") %>    <!-- 15 January 2024 -->
<%= formatDate(new Date(), "%2D/%2M/%4Y") %>                <!-- Today: 15/01/2024 -->
```

**formatDate format codes:**

| Code | Output |
|------|--------|
| `%4Y` | 2024 |
| `%2Y` | 24 |
| `%2M` | 01 |
| `%[month]` | January |
| `%2D` | 15 |
| `%[day]` | Monday |
| `%2H` | 14 |
| `%2N` | 30 (minutes) |

### Using JavaScript Date object

```javascript
<%
  var d = new Date(recipient.birthDate);
  var options = { year: 'numeric', month: 'long', day: 'numeric' };
  var formatted = d.toLocaleDateString('en-GB', options);
%>
Your birthday: <%= formatted %>
```

---

## 8. String Operations

```javascript
<%= recipient.firstName.toUpperCase() %>
<%= recipient.firstName.toLowerCase() %>
<%= recipient.firstName.trim() %>
<%= recipient.lastName.replace(/ /g, '_') %>
<%= recipient.email.indexOf('@') %>          <!-- Position of @ -->
<%= recipient.phone.slice(0, 3) %>           <!-- First 3 chars -->
<%= recipient.fullName.split(' ')[0] %>      <!-- First word (first name) -->
<%= recipient.tags.join(', ') %>             <!-- Array to string -->
```

---

## 9. Dynamic Content (Conditional Blocks)

### UI-based dynamic content (Campaign Standard)

In Adobe Campaign Standard's Email Designer, dynamic content is configured visually using targeting expressions. Each block has:

- **Expression:** `context.profile.field operator value`
- **Operator:** `==`, `!=`, `>`, `<`, `>=`, `<=`, `contains`, `startsWith`

Examples of targeting expressions:

```
context.profile.age >= 18
context.profile.loyaltyTier == "Gold"
context.profile.country == "GB"
context.profile.firstName != null
context.profile.email.length() > 0
```

### Code-driven dynamic images

```javascript
<% var imgSrc = "https://cdn.example.com/"; %>
<% if (recipient.gender == 'M') { %>
  <% imgSrc += "mens-banner.jpg"; %>
<% } else { %>
  <% imgSrc += "womens-banner.jpg"; %>
<% } %>
<img src="<%= imgSrc %>" />
```

---

## 10. External File / Data Source

When sending to an external file (not the recipient table):

```
<%= dataSource.column_name %>
<%= dataSource.FirstName %>
<%= dataSource.OrderTotal %>
<%= dataSource.PromoCode %>
```

---

## 11. Delivery & Campaign Metadata

```
<%= delivery.label %>
<%= delivery.internalName %>
<%= delivery.messageType %>
<%= delivery.scheduledDate %>
<%= delivery.creation %>
<%= delivery.contactDate %>
<%= delivery.campaign.label %>
<%= delivery.campaign.internalName %>

<!-- Sender info -->
<%= delivery.fromName %>
<%= delivery.fromAddress %>
```

---

## 12. Campaign Standard vs Classic Differences

| Feature | Classic v7 / v8 | Campaign Standard |
|---------|-----------------|-------------------|
| Syntax | `<%= recipient.field %>` | `<%= profile.field %>` or `context.profile.field` |
| Dynamic content | Code or DCE editor | Email Designer with visual rules |
| Personalisation blocks | `<%@ include view='nms:block' %>` | Blocks via Content Fragments |
| Advanced scripting | Full JS, AMPscript-like | More limited, primarily expression-based |
| Data access | Full DB schema | Profile schema + linked tables |

---

## 13. Advanced Patterns

### Personalised subject line

```
Subject: Dear <%= recipient.firstName || 'Customer' %>, your order is ready
```

### Dynamic salutation with gender

```javascript
<% var salutation = (recipient.gender == 'M') ? 'Mr' : (recipient.gender == 'F') ? 'Ms' : ''; %>
Dear <%= salutation %> <%= recipient.lastName %>,
```

### Loyalty points with formatted expiry

```javascript
<%
  var pts        = recipient.loyaltyPoints;
  var expiryDate = new Date();
  expiryDate.setDate(expiryDate.getDate() + 90);
  var expStr = formatDate(expiryDate, "%2D %[month] %4Y");
%>
You have <strong><%= pts %> points</strong> — they expire on <%= expStr %>.
```

### Countdown to offer expiry

```javascript
<%
  var expiry    = new Date(recipient.offerExpiry);
  var now       = new Date();
  var diffMs    = expiry - now;
  var daysLeft  = Math.max(0, Math.floor(diffMs / (1000 * 60 * 60 * 24)));
%>
<% if (daysLeft > 0) { %>
  Your offer expires in <strong><%= daysLeft %> day<%= daysLeft > 1 ? 's' : '' %></strong>.
<% } %>
```

### Language-based content

```javascript
<% switch(recipient.language) {
  case 'fr': %>
    Bonjour <%= recipient.firstName || 'cher client' %>,
<% break; case 'de': %>
    Guten Tag <%= recipient.firstName || 'Kunde' %>,
<% break; default: %>
    Hello <%= recipient.firstName || 'there' %>,
<% } %>
```

---

## 14. Fallback Patterns

| Scenario | Code |
|----------|------|
| First name fallback | `<%= recipient.firstName \|\| 'Customer' %>` |
| Conditional salutation | `<% if(recipient.firstName){ %><%= recipient.firstName %><% } else { %>Customer<% } %>` |
| Null date fallback | `<%= recipient.lastOrderDate ? formatDate(recipient.lastOrderDate, "%2D/%2M/%4Y") : 'N/A' %>` |
| Number with fallback | `<%= recipient.loyaltyPoints > 0 ? recipient.loyaltyPoints : 0 %>` |

---

## 15. Gotchas & Debugging

| Issue | Cause | Fix |
|-------|-------|-----|
| Tag shows as literal text | Missing `<%= %>` tags | Wrap all field output in `<%= ... %>` |
| Delivery fails personalisation phase | Script timeout (default 5s) | Increase timeout in Delivery > Properties > Maximum personalisation run time |
| `undefined` in output | Accessing non-existent field | Use `recipient.field \|\| 'default'` guard |
| Date renders as `[object Object]` | Passing Date object without formatting | Use `formatDate()` or `.toLocaleDateString()` |
| JavaScript error in preview | Syntax error in `<% %>` block | Validate JS — missing semicolons or undeclared vars are common |
| Personalisation block missing | Wrong internal name in `include` | Check exact internal name in Personalisation blocks list |
| Content exceeds 1024 chars | Personalisation field limit | Truncate long content before inserting into field |
| Dynamic content not switching | Wrong targeting expression | Use Campaign Standard's preview with test profiles to verify expressions |
| Special chars break layout | Unescaped HTML in data | Use `encodeURIComponent()` for URLs, escape HTML entities manually |

---

## QA Rule Mapping

This section maps the reference material above to executable QA engine rules.

### Rules Applied to Adobe Campaign JSSP Templates

| Rule ID | Group | Check | Deduction | Applies When |
|---------|-------|-------|-----------|-------------|
| ps-delimiter-unbalanced | delimiter_balance | Delimiter pairs balanced | -0.15 | Unclosed `<%= %>` or `<% %>` |
| ps-conditional-unbalanced | delimiter_balance | Conditional blocks balanced | -0.15 | Unclosed `<% if(){} %>` |
| ps-fallback-missing | fallback_completeness | Output tags have defaults | -0.05 | Output tag without ternary `|| 'x'` fallback |
| ps-fallback-empty | fallback_completeness | Fallback values non-empty | -0.03 | Empty string fallback `|| ''` |
| ps-syntax-jssp | syntax_correctness | JSSP syntax well-formed | -0.10 | Malformed JavaScript expressions |
| ps-nesting-depth | best_practices | Nesting ≤ 3 levels | -0.03 | Nested `<% if %>` > 3 deep |
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
