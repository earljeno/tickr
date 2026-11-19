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


def test_split_shift_attendance_flags(app):
    from models.models import AttendanceInconsistency, GlobalSettings, Schedule
    from routes.gia import check_attendance_flags

    with app.app_context():
        # Setup settings with strict mode enabled
        settings = GlobalSettings.get_or_create()
        settings.enable_strict_schedule = True
        settings.allow_early_out = False
        settings.allow_overtime = False
        db.session.commit()

        # Setup split schedule for Monday (mw): 08:00-12:00 and 13:00-17:00
        monday_date = date(2026, 11, 2)  # Monday
        assert monday_date.strftime("%A").lower() == "monday"

        sched = Schedule.query.filter_by(user_id="2024001", day="mw").first()
        sched.start_time = time(8, 0)
        sched.end_time = time(12, 0)
        sched.is_split_shift = True
        sched.split_start_time = time(13, 0)
        sched.split_end_time = time(17, 0)
        db.session.commit()

        # Clear any existing inconsistencies for clean test
        AttendanceInconsistency.query.filter_by(user_id="2024001").delete()
        db.session.commit()

        # Case 1: Clock in on time for second shift (13:00)
        # Should NOT be flagged as Late against primary shift (08:00)
        att_second_on_time = Attendance(
            user_id="2024001",
            date=monday_date,
            clock_in=time(13, 0),
            clock_out=time(17, 0),
        )
        db.session.add(att_second_on_time)
        db.session.commit()

        check_attendance_flags(att_second_on_time)

        flags = AttendanceInconsistency.query.filter_by(
            user_id="2024001", date=monday_date
        ).all()
        assert len(flags) == 0

        # Case 2: Clock in late for second shift (13:15)
        # Should be flagged as Late for second shift, referencing second shift's 1:00 PM start
        att_second_late = Attendance(
            user_id="2024001",
            date=monday_date,
            clock_in=time(13, 15),
            clock_out=time(17, 0),
        )
        db.session.add(att_second_late)
        db.session.commit()

        check_attendance_flags(att_second_late)

        late_flag = AttendanceInconsistency.query.filter_by(
            user_id="2024001", date=monday_date, issue_type="Late"
        ).first()
        assert late_flag is not None
        assert "second shift" in late_flag.details
        assert "01:00 PM" in late_flag.details

        # Case 3: Early out on primary shift (clock-out at 11:30 when end is 12:00)
        tuesday_date = date(2026, 11, 3)  # Tuesday (tth)
        tth_sched = Schedule.query.filter_by(user_id="2024001", day="tth").first()
        tth_sched.start_time = time(8, 0)
        tth_sched.end_time = time(12, 0)
        tth_sched.is_split_shift = True
        tth_sched.split_start_time = time(13, 0)
        tth_sched.split_end_time = time(17, 0)
        db.session.commit()

        att_primary_early = Attendance(
            user_id="2024001",
            date=tuesday_date,
            clock_in=time(8, 0),
            clock_out=time(11, 30),
        )
        db.session.add(att_primary_early)
        db.session.commit()

        check_attendance_flags(att_primary_early)

        early_flag = AttendanceInconsistency.query.filter_by(
            user_id="2024001", date=tuesday_date, issue_type="Early Out"
        ).first()
        assert early_flag is not None
        assert "primary shift" in early_flag.details
        assert "12:00 PM" in early_flag.details


def test_ip_whitelist_allows_dashboard_view_but_blocks_clocking(gia_client, monkeypatch):
    """GIA users can view their dashboard on non-whitelisted devices, but clock in/out is blocked."""
    # Simulate an external / non-whitelisted device IP
    monkeypatch.setattr("utils.decorators.is_ip_whitelisted", lambda user_id=None, client_ip=None: False)

    # Dashboard view remains accessible so users can view their records and info
    dash_res = gia_client.get("/dashboard")
    assert dash_res.status_code == 200
    assert b"GIA Portal" in dash_res.data or b"Time Clock" in dash_res.data

    # Clock in must be blocked with 403 on non-official devices
    clock_in_res = gia_client.post("/api/clock-in", json={"user_id": "2024001"})
    assert clock_in_res.status_code == 403
    in_data = clock_in_res.get_json()
    assert in_data["success"] is False
    assert "Your device is not allowed" in in_data["error"]

    # Clock out must also be blocked with 403 on non-official devices
    clock_out_res = gia_client.post("/api/clock-out", json={"user_id": "2024001"})
    assert clock_out_res.status_code == 403
    out_data = clock_out_res.get_json()
    assert out_data["success"] is False
    assert "Your device is not allowed" in out_data["error"]
