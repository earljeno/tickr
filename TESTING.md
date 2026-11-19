# Testing Guide

## Test Architecture

Tickr has an automated test suite located in `tests/` powered by `pytest`.

Tests execute against an isolated in-memory SQLite database (`sqlite:///:memory:`) using the `TestingConfig` configuration profile, ensuring zero dependence on external database servers or lingering filesystem side-effects.

---

## Test Inventory

| Module | Purpose | Covered Scenarios |
|---|---|---|
| `test_auth.py` | Authentication flows | Admin login, GIA ID login, inactive account rejection, logout, root URL routing |
| `test_api_users.py` | User management | User CRUD, search, pagination, phone normalization, duplicate checks, CSV export |
| `test_api_schedules.py` | Work schedules | Block scheduling (`MW`, `TTh`, `Fri`, `Sat`), split shift updates, authorization checks |
| `test_attendance.py` | Clock in / out | Real-time logging, double clock-in prevention, daily limits, grace periods, settings API |
| `test_admin_views.py` | Views & background jobs | Admin dashboard, schedule table, audit logs, DTR PDF generation, auto clock-out tasks |

---

## Running Tests

### Run all tests:
```bash
pytest -v
```

### Run specific test module:
```bash
pytest tests/test_attendance.py -vv
```

### Run with coverage report:
```bash
pytest --cov=. --cov-report=term-missing
```

---

## Verification Standards

- **Zero Regression:** All 36 tests must pass before merging changes.
- **Code Hygiene:** `ruff check .` must report zero errors or warnings.
- **In-Memory Fixtures:** Use `client`, `admin_client`, or `gia_client` fixtures defined in `tests/conftest.py` for consistent, reproducible testing.
