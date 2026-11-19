# Security & Threat Model

## Authentication & Authorization Model

Tickr implements distinct trust domains according to the user's role:

| Role | Access Scope | Credential Type |
|---|---|---|
| **superadmin** | Full administrative rights, settings, users, and audit logs | Username + PBKDF2-SHA256 Password Hash |
| **admin** | Daily logs, schedules, user updates, and DTR generation | Username + PBKDF2-SHA256 Password Hash |
| **gia** | Personal attendance logging, own schedule view, live tracker | School ID number (Station Kiosk Model) |
| **anonymous** | Login portal only | None |

### Role Enforcement Decorators:
- `@admin_required`: Restricts endpoints to `superadmin` and `admin`. Non-admin requests receive HTTP 403 (JSON for API, redirect to login for views).
- `@gia_required`: Ensures only `gia` role accounts access employee dashboard routes.
- `@ip_whitelist_required`: Validates client IP against designated physical stations.

---

## Defense Against Common Vulnerabilities

### 1. Cross-Site Scripting (XSS)
- **Problem Discovered in Audit:** Client-side JavaScript concatenated unescaped user attributes (`full_name`, `user_id`, `details`, `ip`) into `.innerHTML` template strings.
- **Remediation:** Centralized `escapeHtml()` sanitization function added in `static/js/base.js` and applied across all table renderers (`audit_logs.js`, `daily_logs.js`, `users.js`, `gia_dashboard.js`).

### 2. SQL Injection
- **Mitigation:** All database interactions utilize SQLAlchemy ORM parameterized queries (`filter`, `filter_by`, `session.get`) with zero raw string SQL concatenation.

### 3. Cross-Site Request Forgery (CSRF) & Session Security
- **Cookies:** `SESSION_COOKIE_HTTPONLY = True`, `SESSION_COOKIE_SAMESITE = 'Lax'`.
- In production, `SESSION_COOKIE_SECURE = True` enforces HTTPS transmission.
- Sessions automatically expire after `SESSION_LIFETIME_MINUTES` (default 60 minutes).

### 4. Broken Access Control & Information Exposure
- All administrative endpoints (`/api/add-user`, `/api/update-user`, `/api/delete-user`, `/api/add-log`, `/api/update-settings`, etc.) require authenticated sessions with admin privileges.
- GIA users cannot inspect or modify other employees' schedules or logs (`/api/get-schedule/<id>` checks `current_user.user_id == id`).

### 5. Network Access Controls (IP Whitelisting)
- Configurable via `IP_WHITELIST` environment variable.
- Safe client IP resolution evaluates headers (`CF-Connecting-IP`, `X-Forwarded-For`) only when running behind trusted proxies; falls back safely to `remote_addr`.
