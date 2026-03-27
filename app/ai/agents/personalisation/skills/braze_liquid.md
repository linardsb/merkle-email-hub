---
version: "1.0.0"
---

<!-- L4 source: docs/esp_personalisation/esp_01_braze.md -->
# Braze Liquid Syntax Reference

## Variables

### Basic Variable Output
```liquid
{{ ${first_name} }}
{{ ${last_name} }}
{{ ${email_address} }}
{{ ${city} }}
```

### With Default/Fallback
```liquid
{{ ${first_name} | default: "there" }}
{{ ${city} | default: "your area" }}
{{ ${company_name} | default: "your company" }}
```

### Custom Attributes
```liquid
{{ custom_attribute.${favorite_color} }}
{{ custom_attribute.${membership_tier} | default: "Member" }}
```

## Filters

### String Filters
```liquid
{{ ${first_name} | capitalize }}
{{ ${first_name} | upcase }}
{{ ${first_name} | downcase }}
{{ ${first_name} | truncate: 20 }}
{{ ${first_name} | strip }}
```

### Date Filters
```liquid
{{ ${date_of_birth} | date: "%B %d" }}
{{ "now" | date: "%Y" }}
{{ ${last_purchase_date} | date: "%m/%d/%Y" }}
```

### Number Filters
```liquid
{{ ${points_balance} | number_with_delimiter }}
{{ ${price} | money }}
```

## Conditionals

### If/Else
```liquid
{% if ${first_name} != blank %}
  Hi {{ ${first_name} }},
{% else %}
  Hi there,
{% endif %}
```

### Elsif
```liquid
{% if ${membership_tier} == "Gold" %}
  Exclusive Gold offer
{% elsif ${membership_tier} == "Silver" %}
  Silver member special
{% else %}
  Join our loyalty program
{% endif %}
```

### Contains
```liquid
{% if ${favorite_categories} contains "shoes" %}
  Check out our new shoe collection
{% endif %}
```

## Connected Content

### Basic GET Request
```liquid
{% connected_content https://api.example.com/recommendations?user_id={{${user_id}}} :save recommendations %}
{{ recommendations.product_name }}
```

### With Headers
```liquid
{% connected_content https://api.example.com/data
   :headers {"Authorization": "Bearer {{api_key}}"}
   :content_type application/json
   :save response %}
```

## Content Blocks

### Include a Content Block
```liquid
{{content_blocks.${header_block}}}
{{content_blocks.${footer_block}}}
```

### Content Block with Variables
Content blocks can reference the same Liquid variables as the parent template.

## Abort & Fallback

```liquid
{% if ${email_address} == blank %}
  {% abort_message("No email address") %}
{% endif %}
```

## Common Patterns

### Personalized Greeting
```liquid
{% if ${first_name} != blank %}
  Hi {{ ${first_name} | capitalize }},
{% else %}
  Hi there,
{% endif %}
```

### Dynamic Product Recommendations
```liquid
{% for item in ${recommended_products} %}
  <tr>
    <td>{{ item.name }}</td>
    <td>{{ item.price | money }}</td>
  </tr>
{% endfor %}
```

### Conditional Content Block
```liquid
{% if ${membership_tier} == "Premium" %}
  {{content_blocks.${premium_offer}}}
{% else %}
  {{content_blocks.${standard_offer}}}
{% endif %}
```

### Date-Based Logic
```liquid
{% assign days_since = "now" | date: "%s" | minus: ${last_purchase_date} | date: "%s" | divided_by: 86400 %}
{% if days_since > 30 %}
  We miss you! Come back for 15% off.
{% endif %}
```