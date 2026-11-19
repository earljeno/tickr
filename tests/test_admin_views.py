from datetime import date, time

from models.models import Attendance, db
from tasks import auto_clock_out


def test_admin_dashboard_view(admin_client):
    res = admin_client.get("/admin/dashboard")
    assert res.status_code == 200
    assert b"Dashboard" in res.data


def test_admin_users_view(admin_client):
    res = admin_client.get("/admin/users")
    assert res.status_code == 200
    assert b"User Management" in res.data or b"View Users" in res.data


def test_admin_schedule_view(admin_client):
    res = admin_client.get("/admin/gia-schedule")
    assert res.status_code == 200
    assert b"Schedule" in res.data


def test_admin_daily_logs_view(admin_client):
    res = admin_client.get("/admin/daily-logs")
    assert res.status_code == 200
    assert b"Daily Logs" in res.data


def test_admin_audit_logs_view(admin_client):
    res = admin_client.get("/admin/audit-logs")
    assert res.status_code == 200
    assert b"Audit Logs" in res.data


def test_admin_settings_view(admin_client):
    res = admin_client.get("/admin/settings")
    assert res.status_code == 200
    assert b"Settings" in res.data


def test_admin_profile_view(admin_client):
    res = admin_client.get("/admin/profile")
    assert res.status_code == 200
    assert b"Profile" in res.data


def test_account_settings_redirects_to_profile(admin_client):
    res = admin_client.get("/admin/account-settings")
    assert res.status_code == 302
    assert "/admin/profile" in res.headers["Location"]


def test_export_pdf_view(admin_client):
    res = admin_client.get("/admin/export?month=2026-11")
    assert res.status_code == 200
    assert b"DAILY TIME RECORD" in res.data or b"DTR" in res.data


def test_gia_logs_view(admin_client):
    res = admin_client.get("/admin/gia-logs")
    assert res.status_code == 200
    assert b"GIA Logs & Analytics" in res.data


def test_export_gia_logs_csv(admin_client):
    res = admin_client.get("/api/export-gia-logs?user_id=2024001&month=2026-11")
    assert res.status_code == 200
    assert res.headers.get("Content-Type") == "text/csv; charset=utf-8"



def test_auto_clock_out_task(app):
    with app.app_context():
        # Create an old lingering open record from yesterday
        yesterday = date(2026, 11, 1)
        record = Attendance(
            user_id="2024001",
            date=yesterday,
            clock_in=time(8, 0),
            clock_out=None,
        )
        db.session.add(record)
        db.session.commit()

        # Run task
        updated = auto_clock_out()
        assert updated >= 1

        # Verify record was closed
        reloaded = db.session.get(Attendance, record.id)
        assert reloaded.clock_out is not None
