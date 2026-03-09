# Alt Text Decision Tree & Guidelines

## Decision Tree: What Alt Text to Use

```
Is the image decorative (no information)?
├── Yes → alt="" (empty string, NOT missing)
│   Examples: spacer GIFs, decorative borders, background patterns
│
└── No → Is the image inside a link?
    ├── Yes → alt describes the link destination/action
    │   Example: <a href="/sale"><img alt="Shop the summer sale" ...></a>
    │
    └── No → Is it a complex image (chart, diagram)?
        ├── Yes → Brief alt + detailed description nearby
        │   Example: alt="Q3 revenue chart — details below"
        │
        └── No → Write descriptive alt text
            Example: alt="Woman using laptop at coffee shop"
```

## Alt Text Rules

### Rule 1: Max 125 Characters
Screen readers may truncate longer alt text. Be concise.
- X "This is an image of a beautiful sunset over the ocean with orange and pink clouds reflected in the calm blue water while seagulls fly overhead"
- O "Sunset over ocean with orange and pink clouds"

### Rule 2: Don't Start with "Image of" or "Photo of"
Screen readers already announce it as an image.
- X alt="Image of team members collaborating"
- O alt="Team members collaborating around a whiteboard"

### Rule 3: Include Relevant Details
What information does this image convey that text doesn't?
- Product image: include product name, color, key feature
- Person image: include action or context, not physical description unless relevant
- Location image: include place name and key visual element

### Rule 4: Functional Images Describe the Action
When an image is a link or button:
- X alt="Arrow icon"
- O alt="Next page"
- X alt="Logo"
- O alt="Acme Corp homepage"

### Rule 5: Decorative Images Use Empty Alt
Spacer GIFs, border images, decorative icons alongside text:
```html
<img src="spacer.gif" alt="" width="1" height="20" style="display:block;">
<img src="decorative-line.png" alt="" width="600" height="2">
```

## Context-Aware Alt Text

### Hero Images
Include the headline/message if the image contains text:
```html
<img alt="Summer Sale — Up to 50% off all styles" src="hero-banner.jpg" ...>
```

### Product Images
Include product name and distinguishing features:
```html
<img alt="Classic White Cotton T-Shirt, front view" src="product-01.jpg" ...>
```

### Team/People Images
Include name and context if relevant:
```html
<img alt="Sarah Chen, CEO, speaking at the annual conference" src="ceo.jpg" ...>
```

### Logo Images
Use company name, optionally with "logo" for clarity:
```html
<img alt="Acme Corp" src="logo.png" ...>
```

### Icons Next to Text
If the icon duplicates the adjacent text, use empty alt:
```html
<img alt="" src="phone-icon.png"> Call us: 555-0123
```

### Social Media Icons
Describe the action, not the icon:
```html
<a href="https://example.com/twitter"><img alt="Follow us on Twitter" ...></a>
<a href="https://example.com/instagram"><img alt="See our Instagram" ...></a>
```
