# Frontend Security Patterns

## Authentication
- Use `authFetch` for all API calls (handles JWT injection + refresh)
- Never store tokens in localStorage — Auth.js manages session cookies
- Validate JWT on server-side in middleware.ts

## XSS Prevention
- React auto-escapes by default — never use `dangerouslySetInnerHTML`
- Sanitize any user-generated HTML before rendering

## CSRF
- Auth.js session cookies are httpOnly + SameSite=Lax
- API calls use Bearer token (immune to CSRF)

## Content Security Policy
- Configured in next.config.ts headers
- `default-src 'self'` restricts resource loading
- Explicit allowlists for external resources (maps, CDN)
