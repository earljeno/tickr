from datetime import date, time

from models.models import Attendance, db


def test_clock_in_and_clock_out_flow(gia_client, app):
    # Initial status check
    status_res = gia_client.get("/api/status?user_id=2024001")
    assert status_res.status_code == 200
    assert status_res.get_json()["clocked_in"] is False

    # Clock in
    clock_in_res = gia_client.post("/api/clock-in", json={"user_id": "2024001"})
    assert clock_in_res.status_code == 200
    in_data = clock_in_res.get_json()
    assert in_data["success"] is True
    assert in_data["data"]["user_id"] == "2024001"

    # Status check after clocking in
    status_res2 = gia_client.get("/api/status?user_id=2024001")
    assert status_res2.get_json()["clocked_in"] is True

    # Attempting to clock in again before clocking out must be rejected
    double_in = gia_client.post("/api/clock-in", json={"user_id": "2024001"})
    assert double_in.status_code == 400
    assert "already clocked in" in double_in.get_json()["error"]

    # Clock out
    clock_out_res = gia_client.post("/api/clock-out", json={"user_id": "2024001"})
    assert clock_out_res.status_code == 200
    out_data = clock_out_res.get_json()
    assert out_data["success"] is True

    # Status check after clocking out
    status_res3 = gia_client.get("/api/status?user_id=2024001")
    assert status_res3.get_json()["clocked_in"] is False
    assert status_res3.get_json()["clocked_out"] is True


def test_clock_out_without_clock_in_fails(gia_client):
    res = gia_client.post("/api/clock-out", json={"user_id": "2024001"})
    assert res.status_code == 400
    assert "clocking in first" in res.get_json()["error"]


def test_gia_data_query(gia_client, app):
    # Add a sample completed attendance record
    with app.app_context():
        today = date.today()
        record = Attendance(
            user_id="2024001",
            date=today,
            clock_in=time(8, 0),
            clock_out=time(17, 0),
        )
        db.session.add(record)
        db.session.commit()
    res = gia_client.get("/api/gia-data?user_id=2024001")
    assert res.status_code == 200
    data = res.get_json()
    assert "records" in data
    assert "summary" in data


def test_manual_log_add_and_update(admin_client):
    # Add manual log
    payload = {
        "userId": "2024001",
        "date": "2026-11-01",
        "clockIn": "08:00",
        "clockOut": "17:00",
    }
    add_res = admin_client.post("/api/add-log", json=payload)
    assert add_res.status_code == 200
    assert add_res.get_json()["success"] is True

    # Get daily logs for that date
    daily_res = admin_client.get("/api/get-daily-logs?today=2026-11-01")
    assert daily_res.status_code == 200
    logs = daily_res.get_json()
    assert len(logs) >= 1
    log_id = logs[0]["log_id"]

    # Update log
    update_res = admin_client.post(
        f"/api/update-log/{log_id}",
        json={"clockIn": "08:30", "clockOut": "17:30"},
    )
    assert update_res.status_code == 200
    assert update_res.get_json()["success"] is True


def test_settings_api(admin_client):
    # Get settings
    get_res = admin_client.get("/api/get-settings")
    assert get_res.status_code == 200
    settings = get_res.get_json()
    assert "unit_head" in settings

    # Update settings
    update_res = admin_client.post(
        "/api/update-settings",
        json={
            "unitHeadName": "Dr. Alan Turing",
            "enableStrictMode": True,
            "earlyInMinutes": 10,
            "allowEarlyOut": False,
            "allowOvertime": True,
            "defaultStartTime": "08:00",
            "defaultEndTime": "17:00",
        },
    )
    assert update_res.status_code == 200

    # Verify updated
    get_res2 = admin_client.get("/api/get-settings")
    updated = get_res2.get_json()
    assert updated["unit_head"] == "Dr. Alan Turing"
    assert updated["strict"] is True
    assert updated["early_allowance"] == 10
