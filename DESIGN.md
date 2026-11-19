# Design System and Visual Direction

> Owns visual direction, design principles, design tokens, and aesthetic anti-patterns for Tickr (Office Daily Time Record & Attendance System).

## Purpose and Visual Direction

- **Visual identity:** Authoritative, clean, professional, and purpose-built for university computer center administration and student assistant (GIA) attendance management.
- **Design priorities:** Clarity > Hierarchy > Density > Usability & UX > Visual Polish.
- **Target environment:** Desktop administration workspace and kiosk-style tablet/mobile clock-in stations.

## Design Tokens and Foundations

- **Token source:** `static/css/theme.css` and `static/css/base.css`
- **Color roles:**
  - **Canvas & Surface:**
    - Page Canvas: `#f8fafc` (`--color-canvas`)
    - Surface Card: `#ffffff` (`--color-surface`)
    - Muted Surface: `#f1f5f9` (`--color-surface-subtle`)
    - Sidebar Surface: `#ffffff`
  - **Text & Foreground:**
    - Primary Text: `#0f172a` (Slate 900, 14:1 contrast ratio)
    - Secondary Text: `#475569` (Slate 600, 5.5:1 contrast ratio)
    - Muted Text: `#64748b` (Slate 500, 4.6:1 contrast ratio)
    - Inverse Text: `#ffffff`
  - **Brand & Primary:**
    - Brand Primary: `#1e3a8a` (Deep Navy, NDMU institutional tone)
    - Brand Primary Hover: `#172554`
    - Brand Accent: `#2563eb` (Modern Tech Blue)
    - Brand Tint: `#eff6ff`
  - **Feedback & Semantic Status:**
    - Success (Present, Clock In, Active): `#059669` (bg: `#ecfdf5`, border: `#a7f3d0`)
    - Warning (Late, Split Shift, Incomplete): `#d97706` (bg: `#fffbeb`, border: `#fde68a`)
    - Danger (Clock Out, Inactive, Restricted): `#dc2626` (bg: `#fef2f2`, border: `#fecaca`)
    - Info / Neutral (Admin, MW/TTh, Total): `#2563eb` (bg: `#eff6ff`, border: `#bfdbfe`)
  - **Borders & Dividers:**
    - Default: `#e2e8f0` (`--color-border`)
    - Subtle: `#edf2f7` (`--color-border-subtle`)
    - Focused: `#3b82f6` (`--color-border-focus`)
- **Typography:**
  - Font families: Primary `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`; Monospace `ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace` for clock displays, timestamps, and hours.
  - Scale: H1 (24px, 700), H2 (20px, 600), Body (14px, 400/500), Micro/Badges (12px, 600).
- **Spacing & Sizing Scale:** 4px base (`--space-1: 4px`, `--space-2: 8px`, `--space-4: 16px`, `--space-6: 24px`, `--space-8: 32px`).
- **Elevation & Radii:**
  - Border radii: 6px (`--radius-sm`), 8px (`--radius-md`), 12px (`--radius-lg`), 16px (`--radius-xl`), 9999px (`--radius-full`).
  - Shadows: Subtle crisp multi-layer shadows (`--shadow-sm`, `--shadow-md`, `--shadow-lg`).

## Anti-Slop Visual Rules

- **No decorative clutter:** Every badge, card, and indicator serves an operational attendance purpose. No decorative background blurs, random neon gradients, or AI clichés.
- **Strict WCAG AA contrast:** All text passes 4.5:1 minimum contrast against its background. Status colors are accompanied by clear text labels and icons, never communicated solely by color.
- **Kiosk-grade ergonomics:** Large click/tap targets for clock-in and navigation on touchscreen kiosks.
- **Information scannability:** Tables, shift cards, and summaries feature structured column alignments and monospace numeric formatting for time figures.

## Layout and Hierarchy

- **Admin Portal:** Fixed 260px left sidebar with collapsible mobile drawer, sticky topbar with breadcrumb navigation and accessibility skip links, responsive card grid.
- **Employee Kiosk Portal:** Centered, focused single-page layout featuring live clock, active shift beacon, ergonomic clock button, monthly progress metrics, and attendance history table.
