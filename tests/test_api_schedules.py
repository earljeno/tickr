def test_get_schedules_as_admin(admin_client):
    res = admin_client.get("/api/get-schedules")
    assert res.status_code == 200
    data = res.get_json()
    assert "schedules" in data
    assert "users" in data
    assert len(data["schedules"]) >= 4


def test_get_user_schedule_own(gia_client):
    res = gia_client.get("/api/get-schedule/2024001")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert len(data["schedules"]) == 4


def test_get_user_schedule_other_forbidden(gia_client):
    # GIA trying to access someone else's schedule
    res = gia_client.get("/api/get-schedule/2024002")
    assert res.status_code == 403


def test_update_schedule(admin_client):
    payload = {
        "schedules": [
            {"day": "mw", "start_time": "08:30", "end_time": "17:30"},
            {"day": "tth", "start_time": "09:00", "end_time": "18:00"},
        ],
        "brokenSched": [
            {"day": "mw", "split_start_time": "13:00", "split_end_time": "17:00"}
        ],
    }
    res = admin_client.post("/api/update-schedule/2024001", json=payload)
    assert res.status_code == 200

    sched_res = admin_client.get("/api/get-schedule/2024001")
    data = sched_res.get_json()
    mw_sched = next(s for s in data["schedules"] if s["day"] == "mw")
    assert mw_sched["start_time"] == "08:30"
    assert mw_sched["is_split_shift"] is True

    # Verify /api/get-schedules returns split shift metadata for matrix view
    all_scheds_res = admin_client.get("/api/get-schedules")
    assert all_scheds_res.status_code == 200
    all_data = all_scheds_res.get_json()
    user_mw = next(
        s for s in all_data["schedules"]
        if s["user_id"] == "2024001" and s["day"] == "mw"
    )
    assert user_mw["is_split_shift"] is True
    assert user_mw["split_start_time"] != ""
    assert user_mw["split_end_time"] != ""


def test_get_schedules_with_filters(admin_client):
    # Filter by status=active
    res = admin_client.get("/api/get-schedules?status=active")
    assert res.status_code == 200
    data = res.get_json()
    assert all(u["status"] == "active" for u in data["users"])

    # Filter by search
    res = admin_client.get("/api/get-schedules?search=2024001")
    assert res.status_code == 200
    data = res.get_json()
    assert any(u["user_id"] == "2024001" for u in data["users"])

    # Filter by non-existent
    res = admin_client.get("/api/get-schedules?search=nonexistentassistant999")
    assert res.status_code == 200
    data = res.get_json()
    assert len(data["users"]) == 0


def test_update_daily_schedule(admin_client):
    payload = {
        "schedule_mode": "daily",
        "schedules": [
            {"day": "mon", "start_time": "08:00", "end_time": "12:00"},
            {"day": "tue", "start_time": "13:00", "end_time": "17:00"},
            {"day": "wed", "start_time": "08:00", "end_time": "12:00"},
            {"day": "thu", "start_time": "13:00", "end_time": "17:00"},
            {"day": "fri", "start_time": "09:00", "end_time": "13:00"},
            {"day": "sat", "start_time": "09:00", "end_time": "13:00"},
        ],
        "brokenSched": [
            {"day": "mon", "split_start_time": "14:00", "split_end_time": "16:00"}
        ],
    }
    res = admin_client.post("/api/update-schedule/2024001", json=payload)
    assert res.status_code == 200

    sched_res = admin_client.get("/api/get-schedule/2024001")
    assert sched_res.status_code == 200
    data = sched_res.get_json()
    days = [s["day"] for s in data["schedules"]]
    assert "mon" in days
    assert "tue" in days
    assert "wed" in days
    assert "thu" in days
    assert "mw" not in days  # Cleared out old block schedule

    mon_sched = next(s for s in data["schedules"] if s["day"] == "mon")
    assert mon_sched["start_time"] == "08:00"
    assert mon_sched["is_split_shift"] is True

    # Check /api/get-schedules matrix returns individual days
    all_res = admin_client.get("/api/get-schedules")
    assert all_res.status_code == 200
    all_data = all_res.get_json()
    user_mon = next(
        s for s in all_data["schedules"]
        if s["user_id"] == "2024001" and s["day"] == "mon"
    )
    assert user_mon["start_time"] != ""


def test_open_time_schedule_flow(admin_client):
    # Set Saturday as Open Time (Flexible / office hours fallback)
    payload = {
        "schedule_mode": "block",
        "schedules": [
            {"day": "mw", "start_time": "08:00", "end_time": "12:00"},
            {"day": "tth", "start_time": "08:00", "end_time": "12:00"},
            {"day": "fri", "start_time": "08:00", "end_time": "12:00"},
            {"day": "sat", "is_open_time": True},
        ],
        "brokenSched": [],
    }
    res = admin_client.post("/api/update-schedule/2024001", json=payload)
    assert res.status_code == 200

    sched_res = admin_client.get("/api/get-schedule/2024001")
    assert sched_res.status_code == 200
    data = sched_res.get_json()
    sat_sched = next(s for s in data["schedules"] if s["day"] == "sat")
    assert sat_sched["is_open_time"] is True

    # In get-schedules, daily_hours for open_time should be 0.0 (excluded from 24h total calculation)
    all_res = admin_client.get("/api/get-schedules")
    assert all_res.status_code == 200
    all_data = all_res.get_json()
    user_sat = next(
        s for s in all_data["schedules"]
        if s["user_id"] == "2024001" and s["day"] == "sat"
    )
    assert user_sat["is_open_time"] is True
    assert user_sat["daily_hours"] == 0.0


