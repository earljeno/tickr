# UI Engineering

> Owns frontend/view implementation, rendering, styling integration, responsive behavior, and accessibility. Use `DESIGN.md` for visual direction and token definitions, `UX.md` for user goals and interaction behavior, and `COMPONENTS.md` for component boundaries and reuse.

## UI stack and structure

- **Framework / rendering model:** Server-Side Rendered (SSR) HTML5 with Jinja2 templates via Flask 3.1.
- **Component organization:** 
  - `templates/admin/base.html` (Master admin shell, sidebar, topbar, toast container)
  - `templates/admin/*.html` (Admin views: dashboard, users, schedules, daily logs, export, audit, settings, profile)
  - `templates/auth/login.html` (Dual-mode GIA/Admin kiosk authentication)
  - `templates/gia/dashboard.html` (Employee kiosk attendance portal)
  - `templates/gia/access_denied.html` (Off-network warning)
  - `templates/maintenance.html` (503 database operational error screen)
- **Styling approach:** Central design tokens (`static/css/theme.css`), layout (`static/css/base.css`), and modernized components (`static/css/style.css`, `login.css`, `gia_dashboard.css`, `access_denied.css`, `dtr_report.css`).
- **Form and validation approach:** HTML5 constraint validation + custom client-side validation handlers + server-side validation with Flask/SQLAlchemy.

## Design consistency

- Reusable design tokens in `theme.css` define all primary, surface, border, and status colors.
- Uniform 8px/12px border radii, subtle multi-tier box shadows, and 4px spacing scale.
- Reusable `.content-card`, `.stat-card`, `.btn`, `.form-control`, `.status-badge`, and `.role-badge` classes across all views.
- Monospace font styling (`ui-monospace`) for all time inputs, timestamps, and hours rendered.

## Accessibility

- Visible focus rings (`--focus-ring`) on all interactive buttons, links, and inputs.
- Keyboard navigation: Skip to main content link on base layout; <kbd>Ctrl+K</kbd> quick search shortcut on users, daily logs, and audit logs.
- Color contrast meets WCAG AA standards (minimum 4.5:1 for body copy and 3:1 for UI elements).
- Status is never communicated solely by color; accompanied by icons and descriptive text labels.

## States accounted for

- **Loading & Submitting:** Disabled buttons with animated spinners (`spinner-border-sm`) and "Saving...", "Adding...", or "Authenticating..." feedback text.
- **Empty & First-Use:** Clean empty states with informative icons and instructions when logs or users lists are empty.
- **Validation & System Errors:** Inline `.is-invalid` borders, error text divs, and floating toast error notifications.
- **Success & Confirmation:** Toast notifications via `showAlert('success', '...')` auto-dismissing after 4.5 seconds.
