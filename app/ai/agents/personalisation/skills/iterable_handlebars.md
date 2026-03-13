<!-- L4 source: docs/esp_personalisation/esp_07_iterable.md sections 1-18 -->
# Iterable Handlebars Reference

## User Profile Fields

```handlebars
{{firstName}}
{{lastName}}
{{email}}
{{userId}}
{{profile.loyaltyTier}}
{{profile.totalSpend}}
{{profile.country}}
```

### Special Field Name Syntax
```handlebars
{{[First Name]}}
{{[1stOrderDate]}}
{{profile.[Loyalty Tier]}}
```

### System Variables
```handlebars
{{campaignName}}
{{campaignId}}
{{templateName}}
{{now}}
{{unsubscribeUrl}}
```

### Event / Trigger Data
```handlebars
{{dataFields.orderId}}
{{dataFields.total}}
{{dataFields.items.[0].name}}
{{dataFields.items.[0].price}}
{{dataFields.items.[0].imageUrl}}
```

## Conditional Logic

### Basic If/Else
```handlebars
{{#if firstName}}
  Hello, {{firstName}}!
{{else}}
  Hello, Valued Customer!
{{/if}}
```

### Unless (Inverse)
```handlebars
{{#unless profile.emailOptOut}}
  You're receiving exclusive offers.
{{/unless}}
```

## Comparison Helpers

```handlebars
{{#ifEq profile.loyaltyTier "Gold"}}Gold exclusive{{/ifEq}}
{{#ifGt dataFields.total 100}}Free shipping!{{/ifGt}}
{{#ifLt profile.loyaltyPoints 100}}Almost there!{{/ifLt}}
{{#ifGte profile.totalOrders 10}}Thank you for loyalty.{{/ifGte}}
{{#ifLte dataFields.itemsRemaining 5}}Hurry — low stock!{{/ifLte}}
{{#ifNotEq profile.country "US"}}International shipping{{/ifNotEq}}
```

## String Helpers

```handlebars
{{capitalize firstName}}
{{upper firstName}}
{{lower firstName}}
{{truncate profile.bio 150}}
{{defaultIfEmpty firstName "Friend"}}
{{join dataFields.tags ", "}}
{{length dataFields.items}}
```

## Date Helpers

```handlebars
{{formatDate profile.memberSince "MMMM d, yyyy"}}
{{formatDate now "MMMM d, yyyy"}}
{{addDays now 7}}
{{formatDate (addDays now 7) "MMMM d, yyyy"}}
{{daysBetween profile.signupDate now}}
```

## Number Helpers

```handlebars
{{formatNumber dataFields.price 2}}
{{formatCurrency dataFields.price "GBP"}}
{{math dataFields.qty '*' dataFields.price}}
{{round dataFields.rating}}
{{add a b}}
{{subtract a b}}
```

## Loops

### Basic Product Loop
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

### Limit to First N Items
```handlebars
{{#each (slice dataFields.items 0 3)}}
  {{name}}
{{/each}}
```

### Check Array Not Empty
```handlebars
{{#if dataFields.items}}
  {{#each dataFields.items}}
    <li>{{name}}</li>
  {{/each}}
{{else}}
  <p>No items to display.</p>
{{/if}}
```

## Data Feeds & Catalog

```handlebars
[[catalog_item.productName]]
[[catalog_item.price]]
[[feed_name.fieldName]]
```

## Snippets & Skip Send

```handlebars
{{snippet "snippetName"}}
{{snippet "productCard" productName=dataFields.productName}}

{{#unless dataFields.orderId}}
  {{sendSkip cause="No order ID"}}
{{/unless}}
```

## Common Patterns

### Personalized Greeting
```handlebars
{{#if firstName}}
  Hi {{firstName}},
{{else}}
  Hi there,
{{/if}}
```

### Order Receipt Table
```handlebars
<p>Order #{{dataFields.orderId}}</p>
<table>
  {{#each dataFields.items}}
  <tr>
    <td>{{name}}</td>
    <td>{{quantity}}</td>
    <td>{{formatCurrency price "GBP"}}</td>
  </tr>
  {{/each}}
  <tr><td colspan="2">Total</td><td>{{formatCurrency dataFields.total "GBP"}}</td></tr>
</table>
```

### Loyalty Tier Hero Image
```handlebars
{{#ifEq profile.loyaltyTier "Platinum"}}
  <img src="https://cdn.example.com/hero-platinum.jpg" />
{{else}}
  {{#ifEq profile.loyaltyTier "Gold"}}
    <img src="https://cdn.example.com/hero-gold.jpg" />
  {{else}}
    <img src="https://cdn.example.com/hero-standard.jpg" />
  {{/ifEq}}
{{/ifEq}}
```

### Language-Based Greeting
```handlebars
{{#ifEq profile.language "fr"}}
  Bonjour {{defaultIfEmpty firstName "cher client"}} !
{{else}}
  Hello {{defaultIfEmpty firstName "there"}}!
{{/ifEq}}
```
