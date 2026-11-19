# Deployment Guide

## Production Architecture

In production, Tickr runs behind a reverse proxy (Nginx, Cloudflare, or Railway / Render ingress) with Waitress or Gunicorn as the WSGI server.

---

## Deployment via Railpack / Railway

Tickr includes native `railpack.json` configuration:

```json
{
  "$schema": "https://schema.railpack.com",
  "deploy": {
    "startCommand": "waitress-serve --host=0.0.0.0 --port=$PORT app:app"
  }
}
```

### Required Environment Variables in Production:
- `SECRET_KEY`: High-entropy random key (`python -c "import secrets; print(secrets.token_hex(32))"`).
- `FLASK_ENV`: `production`
- `DATABASE_URL` or `DB_HOST`, `DB_USER`, `DB_PASS`, `DB_NAME`: Production MySQL / PostgreSQL connection.
- `IP_WHITELIST`: Comma-separated list of allowed station IPs.
- `SUPERADMIN_USER` & `SUPERADMIN_PASS`: Initial superadmin credentials.

---

## Database Migration in Production

Before starting the application, run pending migrations:
```bash
flask db upgrade
```
Or seed initial tables and configuration:
```bash
flask init-db
flask seed-admin
```
