---
token_cost: 350
priority: 1
version: "1.0.0"
---
# ESP Template Token Syntax Reference

All tokens below must be treated as **opaque text** — never parse, modify, or move them.

## 1. Liquid (Braze, Shopify)
```
{{ variable }}
{% if condition %}...{% endif %}
{% for item in list %}...{% endfor %}
{{ variable | filter }}
```

## 2. Handlebars (Iterable, Mandrill)
```
{{ variable }}
{{{ unescaped_variable }}}
{{#if condition}}...{{/if}}
{{#each list}}...{{/each}}
{{> partial_name}}
```

## 3. AMPscript (SFMC)
```
%%[SET @var = "value"]%%
%%=v(@var)=%%
%%=Lookup("DE","Field","Key","Value")=%%
%%[IF @var == "value" THEN]%%...%%[ENDIF]%%
```

## 4. ERB (Custom Rails Mailers)
```
<%= variable %>
<% code %>
<%= raw(variable) %>
```

## 5. Jinja2 (Internal Tools)
```
{{ variable }}
{% block name %}...{% endblock %}
{% extends "base.html" %}
{{ variable|filter }}
```

## 6. EJS
```
<%= variable %>
<% code %>
<%- unescaped %>
```

## 7. Velocity (Adobe Campaign)
```
$variable
${variable}
#if($condition)...#end
#foreach($item in $list)...#end
```

## Key Rules
- NEVER modify token content or syntax
- NEVER move tokens across element boundaries
- NEVER split a token across annotations
- If a token wraps structural elements (e.g., `{% if %}` around a `<tr>`), the structural element gets the annotation, not the token
