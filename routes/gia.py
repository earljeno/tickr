from datetime import datetime, timedelta

from flask import Blueprint, render_template
from flask_login import current_user, login_required

from models.models import AttendanceInconsistency, GlobalSettings, Schedule, db
from utils.decorators import gia_required, ip_whitelist_required
from utils.timezone import get_now

gia_bp = Blueprint("gia", __name__)


def check_attendance_flags(attendance_entry) -> None:
    """Check and record attendance inconsistencies (late arrivals, early departures, overtime).

    Excludes weekends (Saturday and Sunday).
    """
    settings = GlobalSettings.get()
    strict_mode = settings.enable_strict_schedule if settings else False

    if not strict_mode or not attendance_entry or not attendance_entry.clock_in:
        return

    record_date = attendance_entry.date
    if record_date.weekday() in [5, 6]:  # Saturday (5) and Sunday (6)
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

    if not user_schedule or not user_schedule.start_time or not user_schedule.end_time:
        return

    schedule_start = datetime.combine(record_date, user_schedule.start_time)
    schedule_end = datetime.combine(record_date, user_schedule.end_time)
    clock_in_dt = datetime.combine(record_date, attendance_entry.clock_in)
    allowed_late_minutes = 0

    # LATE: Clock-in is after scheduled start + grace period
    if clock_in_dt > schedule_start + timedelta(minutes=allowed_late_minutes):
        db.session.add(
            AttendanceInconsistency(
                user_id=attendance_entry.user_id,
                date=record_date,
                issue_type="Late",
                details=(
                    f"Clock-in at {clock_in_dt.strftime('%I:%M %p')}, "
                    f"scheduled start {schedule_start.strftime('%I:%M %p')}"
                ),
            )
        )

    # EARLY OUT: Clock-out before scheduled end
    if attendance_entry.clock_out:
        clock_out_dt = datetime.combine(record_date, attendance_entry.clock_out)
        if clock_out_dt < schedule_end:
            db.session.add(
                AttendanceInconsistency(
                    user_id=attendance_entry.user_id,
                    date=record_date,
                    issue_type="Early Out",
                    details=(
                        f"Clock-out at {clock_out_dt.strftime('%I:%M %p')}, "
                        f"scheduled end {schedule_end.strftime('%I:%M %p')}"
                    ),
                )
            )

        # OVERTIME: Work exceeds scheduled shift + buffer (default 4 hours)
        work_duration = clock_out_dt - clock_in_dt
        scheduled_duration = schedule_end - schedule_start
        overtime_threshold = timedelta(hours=4)

        if work_duration > scheduled_duration + overtime_threshold:
            db.session.add(
                AttendanceInconsistency(
                    user_id=attendance_entry.user_id,
                    date=record_date,
                    issue_type="Overtime",
                    details=f"Worked {work_duration}, scheduled {scheduled_duration}",
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
