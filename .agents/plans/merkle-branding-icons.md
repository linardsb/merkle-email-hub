# Plan: Merkle Branding — Icons, Logo, Sidebar Color, Remove Demo Bar

## Context
Replace lucide-react nav icons with Merkle branded SVG icons from `/assets/`, add the actual Merkle logo to the sidebar header, change the sidebar background from near-black to Merkle dark blue, and remove the red "Demo Mode" banner at the top.

## Assets Available
- **Logo**: `assets/2022-05_Merkle-densu-logo-color_500.png/` — Merkle-dentsu logo (red triangle + dark navy text + "a dentsu company"). Multiple sizes available. Dark text on transparent bg — not usable directly on dark sidebar.
- **AI Icons**: `assets/Artificial Intelligence/` — brain, chip, idea, person (white + black variants, 32x32 and 64x64 SVGs)
- **Digital Marketing Icons**: `assets/Digital Marketing/` — 80+ icons (white + black variants, 32x32 and 64x64 SVGs). Each has white fill (`#fff`) + blue accent (`#538fe4`).

## Icon Mapping (Nav Items → Merkle Icons)

| Nav Item | Current (lucide) | Merkle Icon File (32x32 white) |
|----------|------------------|-------------------------------|
| Dashboard | `LayoutDashboard` | `32x32-Digital-Marketng-Digital-Analysis-white.svg` |
| Projects | `FolderOpen` | `32x32-Digital-Marketng-Email-white.svg` |
| Components | `Blocks` | `32x32-Digital-Marketng-Package-white.svg` |
| Approvals | `ClipboardCheck` | `32x32-Digital-Marketng-Checkmark-white.svg` |
| Connectors | `Plug` | `32x32-Digital-Marketng-Networking-white.svg` |
| Intelligence | `BarChart3` | `32x32-Digital-Marketng-Metrics-white.svg` |
| Knowledge | `BookOpen` | `32x32-Digital-Marketng-Identifying-Knowledge-white.svg` |
| Logout | `LogOut` | Keep lucide `LogOut` (no matching Merkle icon) |

## Files to Create
- `cms/apps/web/public/icons/merkle/dashboard.svg` — copied from Digital-Analysis-white
- `cms/apps/web/public/icons/merkle/projects.svg` — copied from Email-white
- `cms/apps/web/public/icons/merkle/components.svg` — copied from Package-white
- `cms/apps/web/public/icons/merkle/approvals.svg` — copied from Checkmark-white
- `cms/apps/web/public/icons/merkle/connectors.svg` — copied from Networking-white
- `cms/apps/web/public/icons/merkle/intelligence.svg` — copied from Metrics-white
- `cms/apps/web/public/icons/merkle/knowledge.svg` — copied from Identifying-Knowledge-white
- `cms/apps/web/public/merkle-logo.png` — copied from 140x100 variant of the Merkle-dentsu logo

## Files to Modify
- `cms/packages/ui/src/tokens.css` — Update `--color-sidebar-bg` from neutral-900 to Merkle dark blue
- `cms/apps/web/src/app/[locale]/(dashboard)/layout.tsx` — Remove demo banner, replace lucide icons with `<Image>` Merkle icons, update logo section

## Implementation Steps

### Step 1: Copy Merkle icon SVGs to public directory
```bash
mkdir -p cms/apps/web/public/icons/merkle

# Copy and rename each icon
cp "assets/Digital Marketing/32x32-Digital-Marketng-Digital-Analysis-white.svg" cms/apps/web/public/icons/merkle/dashboard.svg
cp "assets/Digital Marketing/32x32-Digital-Marketng-Email-white.svg" cms/apps/web/public/icons/merkle/projects.svg
cp "assets/Digital Marketing/32x32-Digital-Marketng-Package-white.svg" cms/apps/web/public/icons/merkle/components.svg
cp "assets/Digital Marketing/32x32-Digital-Marketng-Checkmark-white.svg" cms/apps/web/public/icons/merkle/approvals.svg
cp "assets/Digital Marketing/32x32-Digital-Marketng-Networking-white.svg" cms/apps/web/public/icons/merkle/connectors.svg
cp "assets/Digital Marketing/32x32-Digital-Marketng-Metrics-white.svg" cms/apps/web/public/icons/merkle/intelligence.svg
cp "assets/Digital Marketing/32x32-Digital-Marketng-Identifying-Knowledge-white.svg" cms/apps/web/public/icons/merkle/knowledge.svg
```

### Step 2: Copy Merkle logo PNG
```bash
cp "assets/2022-05_Merkle-densu-logo-color_500.png/2022-05_Merkle-densu-logo-color_500-140x100.png" cms/apps/web/public/merkle-logo.png
```

### Step 3: Update sidebar color tokens in `tokens.css`

Change `--color-sidebar-bg` from near-black (neutral-900) to Merkle dark blue.

**Light mode** (line 78):
```css
--color-sidebar-bg: oklch(0.22 0.045 260);
```
This is a very dark navy blue (~#1B2A4A), clearly distinguishable from pure black while maintaining the professional Merkle brand feel.

**Dark mode** (line 194):
```css
--color-sidebar-bg: oklch(0.17 0.040 260);
```
Slightly darker variant for dark mode.

### Step 4: Update dashboard layout (`layout.tsx`)

#### 4a: Remove demo mode banner
Delete the entire `{isDemoMode && (...)}` block (lines 77-81) and the `isDemoMode` const (line 72).

#### 4b: Replace lucide icon imports
Remove all lucide icon imports except `LogOut`. Add `Image` import from `next/image`.

**Before:**
```tsx
import {
  LayoutDashboard,
  FolderOpen,
  Blocks,
  ClipboardCheck,
  Plug,
  BarChart3,
  BookOpen,
  LogOut,
} from "lucide-react";
```

**After:**
```tsx
import { LogOut } from "lucide-react";
import Image from "next/image";
```

#### 4c: Update nav items to use Merkle icon images
Replace each lucide `<Icon className="h-5 w-5" />` with:
```tsx
<Image src="/icons/merkle/{name}.svg" alt="" width={20} height={20} className="h-5 w-5" />
```

The `NavItem` interface `icon` field stays as `React.ReactNode` — just use `<Image>` instead of lucide components.

Full navItems array:
```tsx
const navItems: NavItem[] = [
  {
    href: `/${locale}`,
    label: (messages as any)?.nav?.dashboard || "Dashboard",
    icon: <Image src="/icons/merkle/dashboard.svg" alt="" width={20} height={20} className="h-5 w-5" />,
  },
  {
    href: `/${locale}/projects`,
    label: (messages as any)?.nav?.projects || "Projects",
    icon: <Image src="/icons/merkle/projects.svg" alt="" width={20} height={20} className="h-5 w-5" />,
  },
  {
    href: `/${locale}/components`,
    label: (messages as any)?.nav?.components || "Components",
    icon: <Image src="/icons/merkle/components.svg" alt="" width={20} height={20} className="h-5 w-5" />,
  },
  {
    href: `/${locale}/approvals`,
    label: (messages as any)?.nav?.approvals || "Approvals",
    icon: <Image src="/icons/merkle/approvals.svg" alt="" width={20} height={20} className="h-5 w-5" />,
  },
  {
    href: `/${locale}/connectors`,
    label: (messages as any)?.nav?.connectors || "Connectors",
    icon: <Image src="/icons/merkle/connectors.svg" alt="" width={20} height={20} className="h-5 w-5" />,
  },
  {
    href: `/${locale}/intelligence`,
    label: (messages as any)?.nav?.intelligence || "Intelligence",
    icon: <Image src="/icons/merkle/intelligence.svg" alt="" width={20} height={20} className="h-5 w-5" />,
  },
  {
    href: `/${locale}/knowledge`,
    label: (messages as any)?.nav?.knowledge || "Knowledge",
    icon: <Image src="/icons/merkle/knowledge.svg" alt="" width={20} height={20} className="h-5 w-5" />,
  },
];
```

#### 4d: Update logo section in sidebar header
The current inline SVG (red polygon + "MERKLE" text element) is a reasonable approach for dark sidebar since the actual PNG has dark text that won't be visible on dark background. Refine the SVG to be more faithful to the actual Merkle mark:

Replace the logo `<svg>` block (lines 89-94) with:
```tsx
<svg viewBox="0 0 160 36" className="h-8 w-auto" aria-label="Merkle Email Hub">
  {/* Red triangle mark */}
  <polygon points="0,4 10,18 0,32" fill="#E4002B" />
  {/* MERKLE text */}
  <text x="16" y="24" fontFamily="Inter, Arial, sans-serif" fontSize="20" fontWeight="700" letterSpacing="1" fill="white">MERKLE</text>
  {/* Subtitle */}
  <text x="98" y="34" fontFamily="Inter, Arial, sans-serif" fontSize="6" fontWeight="400" fill="#9CA3AF">email hub</text>
</svg>
```

This keeps the logo crisp at any size and readable on the dark blue sidebar.

## Verification
- [ ] `pnpm build` passes (from `cms/`)
- [ ] No TypeScript errors
- [ ] Demo mode red banner is removed
- [ ] Sidebar background is Merkle dark blue (not black)
- [ ] All 7 nav items show Merkle branded icons (white + blue accent)
- [ ] Merkle logo visible in top-left corner of sidebar
- [ ] Logout still uses lucide icon (acceptable — no Merkle equivalent)
- [ ] Dark mode sidebar still looks good (slightly darker navy)
- [ ] Icons render at correct 20x20px size in nav items
- [ ] All semantic Tailwind tokens only (no primitive colors)
