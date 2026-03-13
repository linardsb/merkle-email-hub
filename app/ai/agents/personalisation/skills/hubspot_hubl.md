<!-- L4 source: docs/esp_personalisation/esp_06_hubspot.md sections 1-14 -->
# HubSpot HubL Reference

## Contact Tokens

### Identity
```
{{ contact.firstname }}
{{ contact.lastname }}
{{ contact.email }}
{{ contact.phone }}
{{ contact.jobtitle }}
{{ contact.salutation }}
```

### Company & Location
```
{{ contact.company }}
{{ contact.industry }}
{{ contact.city }}
{{ contact.state }}
{{ contact.country }}
```

### Lifecycle & CRM
```
{{ contact.lifecyclestage }}
{{ contact.hs_lead_status }}
{{ contact.lead_source }}
```

### Custom Properties
```
{{ contact.my_custom_property }}
{{ contact.loyalty_tier }}
{{ contact.promo_code }}
```

## Related Object Tokens

### Company
```
{{ company.name }}
{{ company.domain }}
{{ company.industry }}
{{ company.numberofemployees }}
```

### Deal (Automated Workflows Only)
```
{{ deal.dealname }}
{{ deal.amount }}
{{ deal.closedate }}
{{ deal.dealstage }}
```

### Owner
```
{{ owner.firstname }}
{{ owner.lastname }}
{{ owner.email }}
{{ owner.phone }}
{{ owner.jobtitle }}
```

## Filters

### String Filters
```django
{{ contact.firstname | capitalize }}
{{ contact.firstname | upper }}
{{ contact.firstname | lower }}
{{ contact.firstname | default('Friend') }}
{{ contact.company | truncate(30) }}
{{ contact.firstname | trim }}
{{ contact.website | replace('http://', 'https://') }}
```

### Number Filters
```django
{{ deal.amount | round(2) }}
{{ deal.amount | format_currency('USD') }}
{{ deal.amount | format_currency('GBP') }}
{{ contact.numemployees | int }}
```

### Date Filters
```django
{{ contact.createdate | datetimeformat('%B %d, %Y') }}
{{ contact.createdate | datetimeformat('%d/%m/%Y') }}
{{ deal.closedate | datetimeformat('%B %d, %Y') }}
```

## Conditional Logic

### If/Else
```django
{% if contact.firstname %}
  Hello, {{ contact.firstname }}!
{% else %}
  Hello there!
{% endif %}
```

### Lifecycle Stage Branching
```django
{% if contact.lifecyclestage == 'customer' %}
  Thank you for being a customer.
{% elif contact.lifecyclestage == 'lead' %}
  Ready for the next step?
{% else %}
  Discover what we can offer you.
{% endif %}
```

### Numeric Comparisons
```django
{% if contact.numemployees > 1000 %}
  Enterprise pricing applies.
{% elif contact.numemployees > 100 %}
  Scale with our Business plan.
{% else %}
  Our Starter plan is perfect.
{% endif %}
```

### Null/Empty Check
```django
{% if contact.phone %}
  Call us: {{ contact.phone }}
{% endif %}

{% if not contact.company %}
  Tell us about your organisation.
{% endif %}
```

## Utility Tokens

```
{{ unsubscribe_link }}
{{ subscription_preferences_link }}
{{ view_as_webpage_link }}
{{ site_settings.company_name }}
```

## Common Patterns

### Personalized Greeting
```django
{% if contact.firstname %}
  Hi {{ contact.firstname | capitalize }},
{% else %}
  Hi there,
{% endif %}
```

### Owner Signature Block
```django
{% if owner.firstname %}
  <strong>{{ owner.firstname }} {{ owner.lastname }}</strong><br>
  {{ owner.jobtitle }}<br>
  <a href="mailto:{{ owner.email }}">{{ owner.email }}</a>
{% else %}
  The {{ site_settings.company_name }} Team
{% endif %}
```

### Industry-Specific Hero Image
```django
{% if contact.industry == 'Technology' %}
  <img src="https://cdn.example.com/tech-hero.jpg" />
{% elif contact.industry == 'Financial Services' %}
  <img src="https://cdn.example.com/finance-hero.jpg" />
{% else %}
  <img src="https://cdn.example.com/default-hero.jpg" />
{% endif %}
```

### Deal-Based Renewal Email
```django
Your renewal for <strong>{{ deal.dealname }}</strong> is coming up.
Current value: {{ deal.amount | format_currency('GBP') }}
Renewal date: {{ deal.closedate | datetimeformat('%B %d, %Y') }}
```
