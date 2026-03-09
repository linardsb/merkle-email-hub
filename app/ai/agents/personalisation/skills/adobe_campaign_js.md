# Adobe Campaign Personalisation Reference

## Recipient Fields

### Basic Personalisation
```html
<td>Hello <%= recipient.firstName %>,</td>
<td>Your email: <%= recipient.email %></td>
```

### With Fallback
```html
<td>Hello <%= recipient.firstName ? recipient.firstName : "there" %>,</td>
```

## Personalisation Blocks

### Built-in Blocks
```html
<%= include("blockName") %>
```

### Conditional Blocks
```html
<% if (recipient.gender == 1) { %>
  Dear Ms. <%= recipient.lastName %>,
<% } else { %>
  Dear Mr. <%= recipient.lastName %>,
<% } %>
```

## Formatting Functions

### Date Formatting
```html
<%= formatDate(recipient.birthDate, "%B %d, %Y") %>
<%= formatDate(new Date(), "%m/%d/%Y") %>
```

### Number Formatting
```html
<%= formatNumber(recipient.points, "###,###") %>
<%= formatCurrency(recipient.balance, "USD") %>
```

### String Functions
```html
<%= recipient.firstName.toUpperCase() %>
<%= recipient.city.toLowerCase() %>
<%= recipient.firstName.substring(0, 1) %>
```

## Conditionals

### Simple If/Else
```html
<% if (recipient.loyaltyTier == "Gold") { %>
  <td>Gold Member Exclusive</td>
<% } else if (recipient.loyaltyTier == "Silver") { %>
  <td>Silver Member Special</td>
<% } else { %>
  <td>Join Our Program</td>
<% } %>
```

### Null Checks
```html
<% if (recipient.firstName != null && recipient.firstName != "") { %>
  Hi <%= recipient.firstName %>,
<% } else { %>
  Hi there,
<% } %>
```

## Loops

### Iterate Over Collection
```html
<% for (var i = 0; i < recipient.orders.length; i++) { %>
<tr>
  <td><%= recipient.orders[i].productName %></td>
  <td><%= formatCurrency(recipient.orders[i].price, "USD") %></td>
</tr>
<% } %>
```

## Common Patterns

### Personalized Greeting
```html
<%
var name = recipient.firstName;
if (!name || name == "") {
  name = "there";
}
%>
<td>Hi <%= name %>,</td>
```

### Dynamic Image URL
```html
<img src="<%= recipient.gender == 1 ? 'hero-women.jpg' : 'hero-men.jpg' %>"
  alt="Featured collection" width="600" height="300" style="display:block;">
```

## Security Notes

- Adobe Campaign uses `<% %>` syntax which looks like JavaScript but runs server-side
- This is NOT client-side JavaScript — it executes in Adobe Campaign before email send
- Content between `<% %>` tags is processed and replaced with output before delivery
- Never include actual client-side JavaScript in email HTML
