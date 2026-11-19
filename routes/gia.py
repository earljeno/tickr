from datetime import datetime, timedelta

from flask import Blueprint, render_template
from flask_login import current_user, login_required

from models.models import AttendanceInconsistency, GlobalSettings, Schedule, db
from utils.decorators import gia_required, ip_whitelist_required
from utils.timezone import get_now

gia_bp = Blueprint("gia", __name__)


def check_attendance_flags(attendance_entry) -> None:
    """Check and record attendance inconsistencies (late arrivals, early departures, overtime).

    Accounts for split shifts (primary vs second shift) and respects global settings.
    Excludes Sundays (day off with no scheduled shifts).
    """
    settings = GlobalSettings.get()
    strict_mode = settings.enable_strict_schedule if settings else False

    if not strict_mode or not attendance_entry or not attendance_entry.clock_in:
        return

    record_date = attendance_entry.date
    # Sunday has no scheduled shifts
    if record_date.weekday() == 6:
        return

    # Map day to schedule blocks
    day_name = record_date.strftime("%A").lower()
    day_map = {
        "monday": "mw",
        "wednesday": "mw",
        "tuesday": "tth",
        "thursday": "tth",
        "friday": "fri",
        "saturday": "sat",
    }
    block = day_map.get(day_name)
    if not block:
        return

    user_schedule = Schedule.query.filter_by(
        user_id=attendance_entry.user_id, day=block
    ).first()

    if not user_schedule:
        return

    # Determine available shift windows for this schedule
    # A schedule can have a primary shift and optionally a split (second) shift
    shift_windows = []
    if user_schedule.start_time and user_schedule.end_time:
        shift_windows.append(
            {
                "label": "primary shift",
                "start": user_schedule.start_time,
                "end": user_schedule.end_time,
            }
        )

    if (
        getattr(user_schedule, "is_split_shift", False)
        and user_schedule.split_start_time
        and user_schedule.split_end_time
    ):
        shift_windows.append(
            {
                "label": "second shift",
                "start": user_schedule.split_start_time,
                "end": user_schedule.split_end_time,
            }
        )

    if not shift_windows:
        return

    clock_in_time = attendance_entry.clock_in
    clock_in_dt = datetime.combine(record_date, clock_in_time)

    # Match attendance record to the appropriate shift window
    # 1. Check if clock-in is within a shift window (between earliest allowed arrival and shift end)
    matched_window = None
    allowed_early_in = settings.allowed_early_in_mins if settings else 15

    for window in shift_windows:
        earliest_start_dt = datetime.combine(record_date, window["start"]) - timedelta(minutes=allowed_early_in)
        shift_end_dt = datetime.combine(record_date, window["end"])
        if earliest_start_dt <= clock_in_dt <= shift_end_dt:
            matched_window = window
            break

    # 2. If not inside any active window, match to the window whose start_time is closest to clock-in
    if not matched_window:
        matched_window = min(
            shift_windows,
            key=lambda w: abs((clock_in_dt - datetime.combine(record_date, w["start"])).total_seconds()),
        )

    shift_label = matched_window["label"]
    schedule_start = datetime.combine(record_date, matched_window["start"])
    schedule_end = datetime.combine(record_date, matched_window["end"])
    allowed_late_minutes = 0

    # LATE: Clock-in is after scheduled start + grace period
    if clock_in_dt > schedule_start + timedelta(minutes=allowed_late_minutes):
        # Prevent duplicate Late flag for this user, date, and shift
        existing_late = AttendanceInconsistency.query.filter(
            AttendanceInconsistency.user_id == attendance_entry.user_id,
            AttendanceInconsistency.date == record_date,
            AttendanceInconsistency.issue_type == "Late",
            AttendanceInconsistency.details.like(f"%({shift_label})%"),
        ).first()

        if not existing_late:
            db.session.add(
                AttendanceInconsistency(
                    user_id=attendance_entry.user_id,
                    date=record_date,
                    issue_type="Late",
                    details=(
                        f"Clock-in at {clock_in_dt.strftime('%I:%M %p')}, "
                        f"scheduled start {schedule_start.strftime('%I:%M %p')} ({shift_label})"
                    ),
                )
            )

    # EARLY OUT & OVERTIME checks when clock_out is present
    if attendance_entry.clock_out:
        clock_out_dt = datetime.combine(record_date, attendance_entry.clock_out)

        # EARLY OUT: Clock-out before scheduled end
        # Only flag if allow_early_out is False (or not allowed by settings)
        allow_early_out = getattr(settings, "allow_early_out", True) if settings else True
        if not allow_early_out and clock_out_dt < schedule_end:
            existing_early = AttendanceInconsistency.query.filter(
                AttendanceInconsistency.user_id == attendance_entry.user_id,
                AttendanceInconsistency.date == record_date,
                AttendanceInconsistency.issue_type == "Early Out",
                AttendanceInconsistency.details.like(f"%({shift_label})%"),
            ).first()

            if not existing_early:
                db.session.add(
                    AttendanceInconsistency(
                        user_id=attendance_entry.user_id,
                        date=record_date,
                        issue_type="Early Out",
                        details=(
                            f"Clock-out at {clock_out_dt.strftime('%I:%M %p')}, "
                            f"scheduled end {schedule_end.strftime('%I:%M %p')} ({shift_label})"
                        ),
                    )
                )

        # OVERTIME: Work duration exceeds scheduled shift duration by threshold
        # Only flag if allow_overtime is False (or when strict tracking is enabled)
        allow_overtime = getattr(settings, "allow_overtime", False) if settings else False
        work_duration = clock_out_dt - clock_in_dt
        scheduled_duration = schedule_end - schedule_start
        overtime_threshold = timedelta(hours=4)

        if not allow_overtime and work_duration > scheduled_duration + overtime_threshold:
            existing_ot = AttendanceInconsistency.query.filter(
                AttendanceInconsistency.user_id == attendance_entry.user_id,
                AttendanceInconsistency.date == record_date,
                AttendanceInconsistency.issue_type == "Overtime",
                AttendanceInconsistency.details.like(f"%({shift_label})%"),
            ).first()

            if not existing_ot:
                db.session.add(
                    AttendanceInconsistency(
                        user_id=attendance_entry.user_id,
                        date=record_date,
                        issue_type="Overtime",
                        details=f"Worked {work_duration}, scheduled {scheduled_duration} ({shift_label})",
                    )
                )

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()


# Employee Dashboard
@gia_bp.route("/dashboard")
@login_required
@gia_required
@ip_whitelist_required
def dashboard():
    month = get_now().strftime("%Y-%m")
    return render_template("gia/dashboard.html", user=current_user, month=month)


# Route to display access denied to unauthorized / blocked IPs
@gia_bp.route("/blocked")
def blocked():
    return render_template("gia/access_denied.html", user=current_user), 403


# Backwards compatibility export
WHITELIST = set()
SPECIAL_IDS = set()
