# System Architecture

## Purpose and Scope

- **System Purpose:** Tickr provides a centralized Daily Time Record (DTR) and attendance management system for educational and enterprise computer centers. It handles schedule definition, real-time clock-in/out verification, irregularity tracking, and official monthly DTR generation.
- **Primary Actors:**
  - **Superadmin:** Full system ownership, administrative user provisioning, and global policy control.
  - **Admin:** Employee management, schedule assignment, attendance record adjustment, and DTR generation.
  - **Employee (GIA):** Station kiosk login, live attendance clock-in/out, schedule viewing, and hours monitoring.
- **Out of Scope:** Biometric hardware drivers, payroll disbursement calculation, and multi-tenant organizational partitioning.

---

## Runtime and Components

| Component | Responsibility | Entry Point / Location | Notes |
|---|---|---|---|
| **Application Factory** | App instantiation, extension registration, CLI commands | `app.py:create_app()` | Supports `DevelopmentConfig`, `TestingConfig`, `ProductionConfig` |
| **Authentication Blueprint** | ID kiosk and admin credential auth, session lifecycle | `routes/auth.py` (`/auth`) | Dual login modes: kiosk ID and password-based admin |
| **Admin Blueprint** | Admin UI views, dashboard metrics, DTR report generation | `routes/admin.py` (`/admin`) | Role-guarded via `@admin_required` |
| **GIA Blueprint** | Employee portal views and IP-restriction landing | `routes/gia.py` (`/dashboard`, `/blocked`) | Guarded by `@gia_required` and `@ip_whitelist_required` |
| **API Blueprint** | RESTful endpoints powering asynchronous UI interactions | `routes/api.py` (`/api`) | JSON responses, uniform error handling, strict authorization |
| **Utility Suite** | Cross-cutting concerns: timezone, logging, network IP, decorators | `utils/` | Decoupled helpers resolving circular dependencies |
| **Database Models** | SQLAlchemy ORM entity definitions and relationships | `models/models.py` | Cross-database compatibility (SQLite & MySQL) |

---

## High-Level Request Flows

### 1. Employee Clock-In Flow
```
User clicks "Clock In" -> POST /api/clock-in
  -> Session validation (@login_required)
  -> IP whitelist validation (@ip_whitelist_required)
  -> Today's schedule resolution (MW / TTh / Fri / Sat blocks)
  -> Window check: early-in allowance & shift boundaries
  -> Daily limit check (< 2 shifts) & open shift check
  -> Persist Attendance record (clock_in = now)
  -> Evaluate inconsistency flags (check_attendance_flags)
  -> Write audit log entry (Logs table)
  -> Response JSON with record timestamp and shift indicator
```

### 2. Admin DTR Export Flow
```
Admin navigates to /admin/export?month=YYYY-MM
  -> Role authorization check (@admin_required)
  -> Month date range expansion (first_day to last_day)
  -> Retrieve Philippine national & local holidays for year (holidays library)
  -> Query active GIA users and month's attendance records
  -> Aggregate shift 1 and shift 2 time deltas into decimal hours
  -> Render dual-card printable HTML template (dtr_report.html)
```

---

## Design Constraints & Operational Rules

1. **Timezone Uniformity:** All system operations, date logic, and log entries operate under `Asia/Manila` (`UTC+8`) via `utils.timezone.get_now()`.
2. **Database Flexibility:** Automatically uses SQLite locally when MySQL environment variables are omitted, allowing zero-friction local setup and fast unit testing.
3. **Database Cascading:** Foreign keys (`Attendance`, `Schedule`, `AttendanceInconsistency`) cascade on delete of a `User`.

---

## See Also

- [SECURITY.md](SECURITY.md) — Authentication, authorization, and network controls
- [DATABASE.md](DATABASE.md) — Schema definitions and integrity rules
- [API.md](API.md) — API endpoint contracts and specifications
- [TESTING.md](TESTING.md) — Test suite layout and execution procedures
