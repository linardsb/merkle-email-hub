---
version: "1.0.0"
---

<!-- L4 source: none (original content — cross-platform synthesis) -->
# Universal Fallback Strategies

## Rule: Every Variable Needs a Fallback

No personalisation variable should ever render blank. If the data is missing,
show a sensible default.

## Platform-Specific Fallback Syntax

### Braze (Liquid)
```liquid
{{ ${first_name} | default: "there" }}
{{ ${city} | default: "your area" }}
{{ ${company_name} | default: "your company" }}
```

### SFMC (AMPscript)
```ampscript
%%[
SET @name = AttributeValue("FirstName")
IF Empty(@name) THEN SET @name = "there" ENDIF
]%%
```

### Adobe Campaign
```html
<%= recipient.firstName ? recipient.firstName : "there" %>
```

## Common Fallback Values

| Field | Fallback | Rationale |
|-------|----------|-----------|
| First name | "there" | "Hi there," reads naturally |
| Last name | (omit entire section) | "Dear Customer" is better than "Dear " |
| Company | "your company" | Generic but not jarring |
| City | "your area" | Avoids showing blank |
| Product name | "your item" | Context-dependent |
| Date | (use current date) | Better than blank |
| Currency amount | (hide entire section) | Never show $0 or blank price |

## Graceful Section Hiding

When a variable is empty, sometimes it's better to hide the entire section:

### Braze
```liquid
{% if ${reward_points} != blank and ${reward_points} > 0 %}
<tr>
  <td>Your reward points: {{ ${reward_points} | number_with_delimiter }}</td>
</tr>
{% endif %}
```

### SFMC
```ampscript
%%[
SET @points = AttributeValue("RewardPoints")
IF NOT Empty(@points) AND @points > 0 THEN
]%%
<tr>
  <td>Your reward points: %%=Format(@points, "#,###")=%%</td>
</tr>
%%[ENDIF]%%
```

## Fallback Testing Checklist

1. Test with ALL fields populated -> renders correctly
2. Test with ALL fields empty -> renders with fallbacks, no blanks
3. Test with MIXED empty/populated -> each field independent
4. Test with null vs empty string -> both handled
5. Test with special characters in data -> properly escaped

## Anti-Patterns to Avoid

### No Fallback (BAD)
```liquid
Hi {{ ${first_name} }},
```
Renders: "Hi ," when first_name is empty

### Fallback Creates Awkward Copy (BAD)
```liquid
Hi {{ ${first_name} | default: "Valued Customer" }},
```
Renders: "Hi Valued Customer," — too formal if rest is casual

### Nested Fallback Without Null Check (BAD)
```liquid
{{ ${first_name} | default: ${preferred_name} | default: "there" }}
```
May not work — check ESP documentation for filter chaining behavior

### Correct Pattern (GOOD)
```liquid
{% if ${first_name} != blank %}
  Hi {{ ${first_name} | capitalize }},
{% elsif ${preferred_name} != blank %}
  Hi {{ ${preferred_name} | capitalize }},
{% else %}
  Hi there,
{% endif %}
```