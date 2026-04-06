---
version: "1.0.0"
---

<!-- L4 source: docs/esp_personalisation/esp_05_mailchimp.md sections 1-15 -->
# Mailchimp Merge Language Reference

## Merge Tags

### Contact Tags
```
*|FNAME|*
*|LNAME|*
*|EMAIL|*
*|PHONE|*
*|ADDRESS|*
*|CITY|*
*|STATE|*
*|ZIP|*
*|COUNTRY|*
```

### Audience & Account Tags
```
*|LIST:NAME|*
*|LIST:COMPANY|*
*|MC_PREVIEW_TEXT|*
*|MC_SUBJECT|*
*|MC_LANGUAGE|*
```

### System Tags
```
*|ARCHIVE|*
*|UNSUBSCRIBE|*
*|UPDATE_PROFILE|*
*|FORWARD|*
*|PROMO_CODE|*
```

### Date Tags
```
*|DATE:F j, Y|*
*|DATE:d/m/Y|*
*|CURRENT_YEAR|*
```

### Custom Field Tags
```
*|BIRTHDAY|*
*|LOYALTYTIER|*
*|MEMBERID|*
*|COUPONCODE|*
```

## Conditional Logic

### Basic IF / ELSE
```
*|IF:FNAME|*
  Hello, *|FNAME|*!
*|ELSE:|*
  Hello, Friend!
*|END:IF|*
```

### IF with Value Comparison
```
*|IF:MC_LANGUAGE=fr|*
  Bonjour !
*|ELSEIF:MC_LANGUAGE=de|*
  Guten Tag!
*|ELSE:|*
  Hello!
*|END:IF|*
```

### Numeric Comparison
```
*|IF:TRANSACTIONS >= 20|*
  VIP: 40% off
*|ELSEIF:TRANSACTIONS >= 10|*
  Loyal: 20% off
*|ELSE:|*
  Welcome: 10% off
*|END:IF|*
```

### IFNOT (Negative)
```
*|IFNOT:FNAME|*
  Please update your profile!
*|END:IF|*
```

### Nested Conditionals
```
*|IF:TRANSACTIONS >= 10|*
  *|IF:COUNTRY=US|*
    US VIP shipping included.
  *|ELSE:|*
    International VIP rate applies.
  *|END:IF|*
*|END:IF|*
```

### Supported Operators
| Operator | Use |
|----------|-----|
| *(none)* | Has any value |
| `=` | Equal to |
| `!=` | Not equal to |
| `>` | Greater than |
| `<` | Less than |
| `>=` | Greater than or equal |
| `<=` | Less than or equal |

## Group-Based Conditionals

```
*|INTERESTED:GroupCategory:GroupName|*
  Content for this group only.
*|END:INTERESTED|*

*|INTERESTED:Customers:Wholesale|*
  Wholesale pricing enclosed.
*|ELSE:|*
  Shop our retail range.
*|END:INTERESTED|*
```

## Transactional (Mandrill) Handlebars

```handlebars
{{ first_name }}
{{#if vip_member}}VIP offer{{/if}}
{{#each items}}<li>{{ name }}</li>{{/each}}
```

## Common Patterns

### First Name with Fallback
```
*|IF:FNAME|*Hello, *|FNAME|*,*|ELSE:|*Hello there,*|END:IF|*
```

### Language-Based Content
```
*|IF:MC_LANGUAGE=fr|*
  Bonjour *|FNAME|* !
*|ELSEIF:MC_LANGUAGE=de|*
  Hallo *|FNAME|*!
*|ELSE:|*
  Hello *|FNAME|*!
*|END:IF|*
```

### Dynamic Product Image
```html
<img src="*|PRODUCTIMGURL|*" alt="*|PRODUCTNAME|*" />
<strong>*|PRODUCTNAME|*</strong> — Only *|PRODUCTPRICE|*
<a href="*|PRODUCTURL|*">Shop Now</a>
```