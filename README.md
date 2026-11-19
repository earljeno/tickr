# Tickr – Office Daily Time Record (DTR) & Attendance System

Tickr is a Daily Time Record (DTR) and attendance management web application built with modern Flask, SQLAlchemy, and Bootstrap. Designed for university and office computer centers, it provides distinct portals for administrative oversight and employee/student assistant (GIA) time logging.

---

## Key Features

### Admin Portal (`/admin`)
- **Interactive Dashboard:** Real-time visibility into present personnel, shift compliance rates, average hours worked, overtime metrics, and live activity feeds.
- **User Management:** Full CRUD management for administrators and GIAs with status toggling (`active` / `inactive`), Philippine phone number normalization, and CSV export.
- **Schedule Management:** Flexible block scheduling (`MW`, `TTh`, `Fri`, `Sat`) with support for split/broken shifts and schedule purging.
- **Daily Attendance Logs:** Real-time attendance log review with manual entry creation, time corrections, and date-filtered queries.
- **Printable DTR Export:** Monthly Daily Time Record generator with automatic Philippine regular and special holiday calculation and printable dual-card PDF layouts.
- **Audit Logging:** System-wide action audit trail with date-range filters, user search, and client IP tracking.
- **Global Settings:** Centralized configuration of unit head name, strict schedule mode, grace periods, and shift boundaries.

### Employee (GIA) Portal (`/dashboard`)
- **One-Click Clock-In / Clock-Out:** Instant kiosk-style attendance logging validating against the user's weekly block schedule.
- **Live Session Tracker:** Dynamic elapsed time counter tracking hours rendered in real time.
- **Schedule Viewer:** Modal displaying assigned daily shifts and split shift times.
- **Monthly Summary:** Rendered hours vs target hours and active days worked.
- **Network / IP Restriction:** Configurable IP whitelisting to prevent unauthorized off-site clock-ins.

---

## Tech Stack

- **Backend:** Python 3.11+, Flask 3.1, Flask-SQLAlchemy 3.1, Flask-Login 0.6, Flask-Migrate 4.1
- **Database:** SQLite (local development and automated testing) / MySQL 8.0+ (production)
- **Frontend:** HTML5, CSS3, JavaScript (ES6+), Bootstrap 5.3
- **WSGI Server:** Waitress (Windows / Production)
- **Tooling:** Ruff (linting), Pytest & Pytest-Cov (testing), Alembic (migrations)

---

## Architecture & Project Layout

Tickr utilizes the standard Flask Application Factory pattern (`create_app`) with modular blueprints:

```
/
├── app.py                  # Application factory and CLI commands (init-db, seed-admin)
├── config.py               # Environment configuration (Development, Testing, Production)
├── requirements.txt        # Production dependencies
├── pyproject.toml          # Tooling configuration (Ruff & Pytest)
├── models/
│   └── models.py           # SQLAlchemy database models (User, Attendance, Schedule, GlobalSettings, Logs)
├── routes/
│   ├── auth.py             # Authentication endpoints (/auth/login, /auth/logout)
│   ├── admin.py            # Admin panel controllers (/admin/dashboard, users, schedule, dtr)
│   ├── gia.py              # Employee portal controllers (/dashboard, /blocked)
│   └── api.py              # RESTful API endpoints for UI interactions
├── utils/
│   ├── decorators.py       # @admin_required, @gia_required, @ip_whitelist_required
│   ├── formatters.py       # Phone number normalization and time parsing helpers
│   ├── logging.py          # Unified system action audit logger
│   ├── network.py          # Safe client IP resolution and whitelist validation
│   └── timezone.py         # Asia/Manila timezone utilities and relative time helpers
├── static/
│   ├── css/                # Custom stylesheets
│   └── js/                 # Modular client-side scripts (sanitized DOM rendering)
├── templates/
│   ├── admin/              # Admin HTML templates
│   ├── auth/               # Login templates
│   └── gia/                # Employee portal templates
└── tests/                  # Automated test suite (36 unit & integration tests)
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Git
- (Optional for production) MySQL Server 8.0+

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/earlhsjks/tickr.git
   cd tickr
   ```

2. **Create and activate a virtual environment:**
   ```bash
   # Windows (PowerShell)
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

   # Linux / macOS
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install pytest ruff
   ```

4. **Environment Setup:**
   Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
   *Note: If no MySQL environment variables (`DB_USER`, `DB_NAME`, `DB_HOST`) are specified, Tickr automatically initializes a local SQLite database at `instance/tickr.db`.*

5. **Initialize Database & Seed Superadmin:**
   ```bash
   flask init-db
   flask seed-admin
   ```
   Default credentials:
   - **Admin Username:** `superadmin`
   - **Admin Password:** `admin123`

---

## Running the Application

### Development Server:
```bash
python app.py
```
Access at `http://localhost:3005`.

### Production Server (Waitress):
```bash
waitress-serve --host=0.0.0.0 --port=3005 app:app
```

---

## Running Tests & Quality Checks

Run the complete test suite:
```bash
pytest -v
```

Run code formatting and lint verification:
```bash
ruff check .
```

---

## Security Notes

1. **Secret Key:** Always set a cryptographically secure `SECRET_KEY` in `.env` before deploying to production.
2. **Kiosk Login:** The employee portal is designed for rapid station clock-ins by school ID. Restrict station access using `IP_WHITELIST` in `.env`.
3. **Change Superadmin Password:** Upon initial installation, log in as `superadmin` and immediately change the password via the Profile Settings page.

---

## License

This project is open-source software licensed under the [MIT License](LICENSE).
