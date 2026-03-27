---
version: "1.0.0"
---

<!-- L4 source: docs/esp_personalisation/esp_04_klaviyo.md sections 1-13 -->
# Klaviyo Django Template Language Reference

## Variables

### Basic Variable Output
```django
{{ first_name }}
{{ last_name }}
{{ email }}
{{ person.city }}
{{ person.region }}
```

### With Default/Fallback
```django
{{ first_name|default:'Friend' }}
{{ person|lookup:'LoyaltyTier'|default:'Standard' }}
{{ person|lookup:'NickName'|default:first_name }}
```

### Custom Profile Properties
```django
{{ person|lookup:'PropertyName' }}
{{ person|lookup:'LoyaltyTier' }}
{{ person|lookup:'TotalSpend' }}
{{ person|lookup:'Favorite Category' }}
```

### Event Variables (Flow Emails)
```django
{{ event.value }}
{{ event.extra.OrderId }}
{{ event.extra.Items.0.ProductName }}
{{ event.extra.Items.0.ImageURL }}
{{ event.extra.Items.0.ItemPrice }}
```

## Filters

### Text Filters
```django
{{ first_name|default:'Friend' }}
{{ first_name|title }}
{{ first_name|upper }}
{{ first_name|lower }}
{{ first_name|capfirst }}
{{ person|lookup:'Bio'|truncatechars:150 }}
{{ first_name|striptags }}
```

### Number Filters
```django
{{ event.value|floatformat:2 }}
{{ event.value|floatformat:0 }}
{{ person|lookup:'TotalOrders'|default:0 }}
```

### Date Filters
```django
{{ event.EventDate|date:"F j, Y" }}
{{ event.EventDate|date:"d/m/Y" }}
{{ person|lookup:'MemberSince'|date:"F Y" }}
```

### Array Filters
```django
{{ event.extra.Items|length }}
{{ event.extra.Items|first }}
{{ event.extra.Items|last }}
```

## Conditionals

### If/Else
```django
{% if first_name %}
  Hello, {{ first_name }}!
{% else %}
  Hello there!
{% endif %}
```

### If/Elif/Else
```django
{% if person|lookup:'LoyaltyTier' == 'Platinum' %}
  Platinum exclusive offer
{% elif person|lookup:'LoyaltyTier' == 'Gold' %}
  Gold member deal
{% else %}
  Join our loyalty programme
{% endif %}
```

### Numeric Comparisons
```django
{% if event.value > 100 %}
  Free shipping on this order!
{% endif %}
```

## Loops

### Basic Loop
```django
{% for item in event.extra.Items %}
  <tr>
    <td>{{ item.ProductName }}</td>
    <td>{{ item.Quantity }}</td>
    <td>£{{ item.ItemPrice|floatformat:2 }}</td>
  </tr>
{% endfor %}
```

### Loop with Limit
```django
{% for item in event.extra.Items|slice:":3" %}
  {{ item.ProductName }}
{% endfor %}
```

### Empty Loop Fallback
```django
{% for item in event.extra.Items %}
  {{ item.ProductName }}
{% empty %}
  No items found.
{% endfor %}
```

## Common Patterns

### Personalized Greeting
```django
{% if first_name %}
  Hi {{ first_name|title }},
{% else %}
  Hi there,
{% endif %}
```

### Dynamic Product Recommendations
```django
{% for item in event.extra.Items %}
  <tr>
    <td><img src="{{ item.ImageURL }}" width="80" /></td>
    <td>{{ item.ProductName }}</td>
    <td>£{{ item.ItemPrice|floatformat:2 }}</td>
  </tr>
{% endfor %}
```

### Gender Salutation
```django
{% if person|lookup:'Gender' == 'M' %}
  Dear Mr {{ last_name }},
{% elif person|lookup:'Gender' == 'F' %}
  Dear Ms {{ last_name }},
{% else %}
  Dear {{ first_name|default:'Customer' }},
{% endif %}
```

### Language-Based Content
```django
{% if person|lookup:'Language' == 'fr' %}
  Bonjour {{ first_name|default:'cher client' }} !
{% else %}
  Hello {{ first_name|default:'there' }}!
{% endif %}
```