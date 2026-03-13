---
level: L4
type: reference
domain: personalisation
platform: sfmc
qa_check: personalisation_syntax
version: "1.0"
---

# ESP: Salesforce Marketing Cloud — AMPscript Personalisation Reference

**Language:** AMPscript (proprietary) + Personalization Strings
**Delimiters:** `%%[ ]%%` code blocks · `%%=FunctionName()=%%` inline output · `%%field%%` personalization strings
**Case-sensitive:** No (function names and field references are case-insensitive)
**Docs:** https://ampscript.guide · https://developer.salesforce.com/docs/marketing/marketing-cloud-ampscript

---

## SECTIONS
1. [Personalization Strings — Subscriber / System](#1-personalization-strings--subscriber--system)
2. [Data Extension Field References](#2-data-extension-field-references)
3. [Code Block Syntax](#3-code-block-syntax)
4. [Inline Output Syntax](#4-inline-output-syntax)
5. [Conditional Logic](#5-conditional-logic)
6. [String Functions](#6-string-functions)
7. [Date Functions](#7-date-functions)
8. [Math Functions](#8-math-functions)
9. [Data Extension Lookups](#9-data-extension-lookup-functions)
10. [Loops](#10-loops)
11. [Dynamic Content Rules](#11-dynamic-content-rules)
12. [Server-Side JavaScript (SSJS)](#12-server-side-javascript-ssjs)
13. [Complete Function Reference](#13-complete-function-reference)
14. [Advanced Patterns](#14-advanced-patterns)
15. [Fallback Patterns](#15-fallback-patterns)
16. [Gotchas & Debugging](#16-gotchas--debugging)

---

## 1. Personalization Strings — Subscriber / System

Personalization strings are **not AMPscript** — they are simple substitution strings processed before AMPscript runs.

```
%%emailaddr%%               <!-- subscriber email address -->
%%emailname%%               <!-- subscriber display name -->
%%_subscriberkey%%          <!-- subscriber key (unique ID) -->
%%subscriberid%%            <!-- numeric subscriber ID -->
%%jobid%%                   <!-- send job ID -->
%%listid%%                  <!-- list ID -->
%%memberid%%                <!-- member ID (business unit) -->

<!-- Date/Time — evaluated at send time (Central Standard Time) -->
%%xtmonth%%                 <!-- January -->
%%xtshortmonth%%            <!-- Jan -->
%%xtday%%                   <!-- 15 -->
%%xtlongdate%%              <!-- Monday January 15 2024 -->
%%xtshortdate%%             <!-- 1/15/2024 -->
%%xtyear%%                  <!-- 2024 -->
%%xttime%%                  <!-- 10:30 AM -->

<!-- Link system strings -->
%%view_email_url%%          <!-- View in browser link -->
%%unsub_center_url%%        <!-- Unsubscribe center URL -->
%%profile_center_url%%      <!-- Profile center URL -->
```

---

## 2. Data Extension Field References

Inside AMPscript blocks, reference DE fields directly by column name:

```ampscript
[FirstName]
[LastName]
[EmailAddress]
[City]
[State]
[PostalCode]
[Country]
[PhoneNumber]
[LoyaltyTier]
[LastPurchaseDate]
[TotalSpend]
[CustomField]             <!-- Any column in your sending DE -->
```

Outside blocks (inline), wrap in `%%`:

```
%%FirstName%%
%%LastName%%
%%LoyaltyTier%%
```

---

## 3. Code Block Syntax

```ampscript
%%[
  /* Multi-line code block */
  VAR @firstName, @email, @tier, @greeting

  SET @firstName = [FirstName]
  SET @email     = [EmailAddress]
  SET @tier      = AttributeValue('LoyaltyTier')
  SET @today     = NOW()

  /* Conditional */
  IF NOT EMPTY(@firstName) THEN
    SET @greeting = CONCAT("Hello, ", @firstName, "!")
  ELSE
    SET @greeting = "Hello, Valued Customer!"
  ENDIF
]%%
```

---

## 4. Inline Output Syntax

```ampscript
%%=V(@variableName)=%%                     <!-- Output a variable -->
%%=AttributeValue('FieldName')=%%          <!-- Output a profile attribute -->
%%=Concat([FirstName], " ", [LastName])=%% <!-- Inline function output -->
%%=IIF(Empty([FirstName]),'Friend',[FirstName])=%% <!-- Inline conditional -->
```

---

## 5. Conditional Logic

### IF / ELSEIF / ELSE / ENDIF

```ampscript
%%[
  IF [LoyaltyTier] == "Gold" THEN
    SET @offerText = "Exclusive Gold offer inside"
  ELSEIF [LoyaltyTier] == "Silver" THEN
    SET @offerText = "Your Silver member discount"
  ELSE
    SET @offerText = "A special offer just for you"
  ENDIF
]%%
%%=V(@offerText)=%%
```

### Inline with IIF (ternary)

```ampscript
%%=IIF(Empty([FirstName]), "Friend", [FirstName])=%%
%%=IIF([Gender]=="M", "Mr.", "Ms.")=%%
%%=IIF([TotalSpend] > 500, "VIP", "Standard")=%%
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
| `AND` | Logical AND |
| `OR` | Logical OR |
| `NOT` | Logical NOT |

### EMPTY / NOT EMPTY checks

```ampscript
%%[
  IF NOT EMPTY([FirstName]) THEN
    /* has a value */
  ENDIF

  IF EMPTY([LastPurchaseDate]) THEN
    /* never purchased */
  ENDIF
]%%
```

---

## 6. String Functions

```ampscript
%%=ProperCase([FirstName])=%%                    <!-- john → John -->
%%=UpperCase([LastName])=%%                      <!-- smith → SMITH -->
%%=LowerCase([Email])=%%                         <!-- USER@MAIL.COM → user@mail.com -->
%%=Substring([FullName], 1, 5)=%%                <!-- First 5 chars (1-indexed) -->
%%=Length([Bio])=%%                              <!-- Character count -->
%%=Trim([Field])=%%                              <!-- Strip leading/trailing whitespace -->
%%=LTrim([Field])=%%                             <!-- Strip left whitespace -->
%%=RTrim([Field])=%%                             <!-- Strip right whitespace -->
%%=Replace([Body], "old text", "new text")=%%
%%=RegExMatch([Field], "pattern")=%%             <!-- Regex match -->
%%=Concat([First], " ", [Last])=%%               <!-- Join strings -->
%%=BuildRowsetFromString([CSV], ",")=%%          <!-- Split CSV to rowset -->
%%=Field(Row(@rowset, 1), 1)=%%                  <!-- Access first item of rowset -->

<!-- URL encoding -->
%%=URLEncode([TrackingParam])=%%
%%=Base64Encode([RawData])=%%
%%=Base64Decode([EncodedData])=%%

<!-- Hashing -->
%%=MD5([Email])=%%
%%=SHA256([Field])=%%

<!-- GUID -->
%%=GUID()=%%                                     <!-- Generate unique ID -->
```

---

## 7. Date Functions

```ampscript
%%=Format(Now(), "MMMM d, yyyy")=%%              <!-- March 15, 2024 -->
%%=Format(Now(), "MM/dd/yyyy")=%%                <!-- 03/15/2024 -->
%%=Format(Now(), "d MMMM yyyy")=%%               <!-- 15 March 2024 -->
%%=Format(Now(), "dddd, MMMM d")=%%              <!-- Friday, March 15 -->
%%=Format([PurchaseDate], "MMMM d, yyyy")=%%
%%=Format([PurchaseDate], "MMMM d")=%%

%%=Now()=%%                                      <!-- Current server datetime (CST) -->
%%=DateAdd(Now(), 7, "D")=%%                     <!-- 7 days from now -->
%%=DateAdd(Now(), 1, "M")=%%                     <!-- 1 month from now -->
%%=DateAdd(Now(), -30, "D")=%%                   <!-- 30 days ago -->
%%=DateDiff(Now(), [SignupDate], "D")=%%          <!-- Days since signup -->
%%=DateDiff([ExpiryDate], Now(), "D")=%%          <!-- Days until expiry -->
%%=DatePart(Now(), "D")=%%                        <!-- Day of month (1–31) -->
%%=DatePart(Now(), "M")=%%                        <!-- Month number (1–12) -->
%%=DatePart(Now(), "Y")=%%                        <!-- Year (2024) -->
%%=DatePart(Now(), "H")=%%                        <!-- Hour (0–23) -->
```

**DateAdd units:** `"D"` days · `"M"` months · `"Y"` years · `"H"` hours · `"MI"` minutes

> **Gotcha:** SFMC servers run on CST (UTC-6). Use `DateAdd(Now(), -6, "H")` as a base if you need UTC, or handle timezone offset logic.

---

## 8. Math Functions

```ampscript
%%=Add([Points], 100)=%%
%%=Subtract([Price], [Discount])=%%
%%=Multiply([Qty], [UnitPrice])=%%
%%=Divide([Total], [Count])=%%
%%=Mod([Number], 2)=%%                <!-- Modulo -->
%%=Abs([NegativeNumber])=%%
%%=FormatNumber([Price], "N2")=%%     <!-- 12.50 -->
%%=FormatNumber([Price], "C2")=%%     <!-- $12.50 (currency) -->
```

---

## 9. Data Extension Lookup Functions

### Lookup — single value from single row

```ampscript
%%[
  SET @promoCode = Lookup("PromoCodes", "Code", "SubscriberKey", @subKey)
  SET @firstName = Lookup("Contacts", "FirstName", "Email", [emailaddr])
]%%
```

### LookupRows — multiple rows

```ampscript
%%[
  SET @rows     = LookupRows("Orders", "SubscriberKey", @subKey)
  SET @rowCount = RowCount(@rows)
  IF @rowCount > 0 THEN
    SET @firstRow  = Row(@rows, 1)
    SET @orderDate = Field(@firstRow, "OrderDate")
    SET @total     = Field(@firstRow, "Total")
  ENDIF
]%%
```

### LookupOrderedRows — sorted results with limit

```ampscript
%%[
  /* 5 most recent orders, newest first */
  SET @orders = LookupOrderedRows("Orders", 5, "OrderDate desc", "SubscriberKey", @subKey)
  SET @count  = RowCount(@orders)
]%%
```

### LookupRows with multiple conditions

```ampscript
%%[
  SET @rows = LookupRowsCS("Products", "Category", [Category], "InStock", "true")
]%%
```

> **Note:** `LookupRowsCS` is case-sensitive. Use `LookupRows` for case-insensitive matching.

---

## 10. Loops

```ampscript
%%[
  SET @products = LookupOrderedRows("RecentPurchases", 5, "Date desc", "SubscriberKey", @subKey)
  SET @count    = RowCount(@products)

  FOR @i = 1 TO @count DO
    SET @row          = Row(@products, @i)
    SET @productName  = Field(@row, "ProductName")
    SET @productPrice = Field(@row, "Price")
    SET @productImage = Field(@row, "ImageURL")
]%%
    <div class="product-card">
      <img src="%%=V(@productImage)=%%" />
      <p>%%=V(@productName)=%%</p>
      <p>£%%=V(@productPrice)=%%</p>
    </div>
%%[  NEXT @i ]%%
```

---

## 11. Dynamic Content Rules

AMPscript-driven content swap (code-only approach):

```ampscript
%%[
  SET @tier = AttributeValue('LoyaltyTier')
]%%

%%[ IF @tier == "Platinum" THEN ]%%
  <img src="https://cdn.example.com/platinum-banner.jpg" alt="Platinum offer" />
%%[ ELSEIF @tier == "Gold" THEN ]%%
  <img src="https://cdn.example.com/gold-banner.jpg" alt="Gold offer" />
%%[ ELSEIF @tier == "Silver" THEN ]%%
  <img src="https://cdn.example.com/silver-banner.jpg" alt="Silver offer" />
%%[ ELSE ]%%
  <img src="https://cdn.example.com/standard-banner.jpg" alt="Standard offer" />
%%[ ENDIF ]%%
```

> Marketing Cloud also has a **Dynamic Content** UI builder that creates rule-based content blocks without code. The above is the code-equivalent approach giving full control.

---

## 12. Server-Side JavaScript (SSJS)

SSJS runs server-side in Marketing Cloud. Used for complex logic, API calls, and write-back to DEs.

```javascript
<script runat="server">
  Platform.Load("Core", "1");

  /* Read values */
  var email     = [emailaddr];
  var firstName = [FirstName];
  var subKey    = [_subscriberkey];

  /* Get/set AMPscript variables */
  var myVar = Variable.GetValue("@ampscriptVar");
  Variable.SetValue("@result", "computed value");

  /* Data Extension operations */
  var de   = DataExtension.Init("MyDE");
  var rows = de.Rows.Lookup(["SubscriberKey"], [subKey]);

  /* Write output */
  Write("Hello, " + firstName);
</script>
```

---

## 13. Complete Function Reference

| Function | Category | Description |
|----------|----------|-------------|
| `AttributeValue(name)` | Data | Get subscriber attribute |
| `Lookup(DE, returnF, matchF, matchV)` | Data | Single value from DE |
| `LookupRows(DE, field, val)` | Data | Multiple rows from DE |
| `LookupOrderedRows(DE, count, order, field, val)` | Data | Ordered rows with limit |
| `Row(rowset, n)` | Data | Get row n from rowset |
| `Field(row, fieldName)` | Data | Get field value from row |
| `RowCount(rowset)` | Data | Count rows |
| `Now()` | Date | Current datetime |
| `Format(val, format)` | Date | Format date or number |
| `DateAdd(date, n, unit)` | Date | Add time to date |
| `DateDiff(d1, d2, unit)` | Date | Difference between dates |
| `DatePart(date, part)` | Date | Extract part of date |
| `SystemDateToLocalDate(date)` | Date | Convert system to local |
| `Concat(a, b, ...)` | String | Join strings |
| `Substring(str, start, len)` | String | Extract substring |
| `Length(str)` | String | String length |
| `Trim(str)` | String | Strip whitespace |
| `LTrim(str)` | String | Strip left whitespace |
| `RTrim(str)` | String | Strip right whitespace |
| `ProperCase(str)` | String | Title case |
| `UpperCase(str)` | String | UPPER CASE |
| `LowerCase(str)` | String | lower case |
| `Replace(str, old, new)` | String | Replace text |
| `RegExMatch(str, pattern)` | String | Regex match |
| `URLEncode(str)` | String | URL-encode string |
| `Base64Encode(str)` | String | Base64 encode |
| `MD5(str)` | String | MD5 hash |
| `SHA256(str)` | String | SHA-256 hash |
| `GUID()` | String | Generate GUID |
| `Empty(val)` | Logic | True if null/empty |
| `IIF(cond, true, false)` | Logic | Inline ternary |
| `Add(a, b)` | Math | Addition |
| `Subtract(a, b)` | Math | Subtraction |
| `Multiply(a, b)` | Math | Multiplication |
| `Divide(a, b)` | Math | Division |
| `Mod(a, b)` | Math | Modulo |
| `Abs(n)` | Math | Absolute value |
| `FormatNumber(n, format)` | Math | Format number |
| `InsertDE(name, ...)` | DE Write | Insert row into DE |
| `UpdateDE(name, ...)` | DE Write | Update DE row |
| `UpsertDE(name, ...)` | DE Write | Insert or update |
| `DeleteDE(name, ...)` | DE Write | Delete DE row |
| `SendEmailMessage(...)` | Send | Trigger email send |
| `CreateObject(...)` | API | Create Marketing Cloud object |

---

## 14. Advanced Patterns

### Personalised subject line

```
Subject: Hello %%FirstName%%, your exclusive offer is inside
```

### Dynamic greeting with ProperCase

```ampscript
%%[
  SET @name = ProperCase(LowerCase([FirstName]))
  IF EMPTY(@name) THEN
    SET @name = "Valued Customer"
  ENDIF
]%%
Hello, %%=V(@name)=%%!
```

### Days since last purchase

```ampscript
%%[
  IF NOT EMPTY([LastPurchaseDate]) THEN
    SET @daysSince = DateDiff(Now(), [LastPurchaseDate], "D")
  ELSE
    SET @daysSince = 999
  ENDIF
]%%
%%[ IF @daysSince < 30 THEN ]%%
  Thanks for your recent purchase!
%%[ ELSEIF @daysSince < 90 THEN ]%%
  We miss you — it's been %%=V(@daysSince)=%% days.
%%[ ELSE ]%%
  It's been a while — here's 20% off to welcome you back.
%%[ ENDIF ]%%
```

### Dynamic image URL

```ampscript
%%[
  SET @imgUrl = Concat("https://cdn.example.com/hero/", LowerCase([LoyaltyTier]), ".jpg")
]%%
<img src="%%=V(@imgUrl)=%%" alt="Your offer" />
```

### Product loop with image and price

```ampscript
%%[
  SET @subKey   = AttributeValue("_subscriberkey")
  SET @products = LookupOrderedRows("RecoProducts", 3, "Score desc", "SubscriberKey", @subKey)
  SET @count    = RowCount(@products)
  FOR @i = 1 TO @count DO
    SET @row   = Row(@products, @i)
    SET @name  = Field(@row, "ProductName")
    SET @price = Field(@row, "Price")
    SET @img   = Field(@row, "ImageURL")
    SET @url   = Field(@row, "ProductURL")
]%%
  <div class="product">
    <a href="%%=V(@url)=%%">
      <img src="%%=V(@img)=%%" alt="%%=V(@name)=%%" />
      <p>%%=V(@name)=%%</p>
      <p>£%%=FormatNumber(@price,"N2")=%%</p>
    </a>
  </div>
%%[  NEXT @i ]%%
```

---

## 15. Fallback Patterns

| Scenario | AMPscript |
|----------|-----------|
| First name fallback | `%%=IIF(Empty([FirstName]),"Friend",[FirstName])=%%` |
| Proper-cased with fallback | `%%=IIF(Empty([FirstName]),"Friend",ProperCase(LowerCase([FirstName])))=%%` |
| Date with empty check | `%%[ IF NOT EMPTY([OrderDate]) THEN ]%% %%=Format([OrderDate],"MMMM d")=%% %%[ ELSE ]%% recently %%[ ENDIF ]%%` |
| Lookup with fallback | `%%[ SET @val = Lookup("DE","Field","Key",@key) IF EMPTY(@val) THEN SET @val = "Default" ENDIF ]%%` |

---

## 16. Gotchas & Debugging

| Issue | Cause | Fix |
|-------|-------|-----|
| `Variable not defined` error | Missing `VAR @name` declaration | Always declare variables with `VAR` first |
| Empty output | Lookup returns null | Wrap with `IIF(Empty(@var),"fallback",@var)` |
| Wrong timezone on dates | SFMC server is CST (UTC-6) | Use `DateAdd(Now(), offset, "H")` to adjust |
| DE field not found | Wrong column name casing or typo | Field names are case-insensitive but must match column name |
| AMPscript not rendering | Code placed outside `%%[ ]%%` | Ensure all code is inside block delimiters |
| Inline output not showing | Using `%%[@var]%%` instead of `%%=V(@var)=%%` | Use `V()` function for variable output |
| Personalization string shows literally | Typo in string name | Check exact string in SFMC docs |
| Content Builder strips AMPscript | HTML pasting issue | Use Code View in Content Builder to paste AMPscript |
| FOR loop runs 0 times | `RowCount` returns 0 | Check Lookup conditions; verify DE has matching data |
| `LookupRows` returns wrong row | Multiple matches, wrong sort | Use `LookupOrderedRows` with explicit sort order |

---

## QA Rule Mapping

This section maps the reference material above to executable QA engine rules.

### Rules Applied to SFMC AMPscript Templates

| Rule ID | Group | Check | Deduction | Applies When |
|---------|-------|-------|-----------|-------------|
| ps-delimiter-unbalanced | delimiter_balance | Delimiter pairs balanced | -0.15 | Unclosed `%%[ ]%%` or `%%=...=%%` |
| ps-conditional-unbalanced | delimiter_balance | Conditional blocks balanced | -0.15 | Unclosed `IF…ENDIF` |
| ps-fallback-missing | fallback_completeness | Output tags have defaults | -0.05 | Output tag without `IIF(Empty())` fallback |
| ps-fallback-empty | fallback_completeness | Fallback values non-empty | -0.03 | Empty string fallback `IIF(Empty(), "")` |
| ps-syntax-ampscript | syntax_correctness | AMPscript syntax well-formed | -0.10 | SET without @ prefix, unbalanced parentheses |
| ps-nesting-depth | best_practices | Nesting ≤ 3 levels | -0.03 | Nested `IF` > 3 deep |
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
