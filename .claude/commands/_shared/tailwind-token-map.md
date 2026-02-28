# Tailwind Semantic Token Rules

NEVER use primitive Tailwind colors. ALWAYS use semantic tokens.

## Background
- `bg-background` not `bg-white`
- `bg-card` not `bg-gray-50`
- `bg-muted` not `bg-gray-100`
- `bg-primary` not `bg-blue-600`
- `bg-destructive` not `bg-red-500`
- `bg-accent` not `bg-gray-200`

## Text
- `text-foreground` not `text-black`
- `text-muted-foreground` not `text-gray-500`
- `text-primary` not `text-blue-600`
- `text-destructive` not `text-red-500`
- `text-card-foreground` not `text-gray-900`

## Border
- `border-border` not `border-gray-200`
- `border-input` not `border-gray-300`
- `border-primary` not `border-blue-600`

## Ring
- `ring-ring` not `ring-blue-500`

## Container Sizes
Named container sizes collapse in Tailwind v4. Use explicit rem:
- `sm:max-w-[28rem]` not `max-w-sm`
- `sm:max-w-[32rem]` not `max-w-md`
- `sm:max-w-[36rem]` not `max-w-lg`
