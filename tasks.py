import logging
from datetime import date, datetime, time, timedelta

from models.models import Attendance, GlobalSettings, Schedule, db
from utils.logging import system_log_entry
from utils.timezone import get_now

logger = logging.getLogger(__name__)


def auto_clock_out_strict_shift(
    target_date: date | None = None,
    clock_out_target: time = time(20, 30),
) -> int:
    """Auto fill clock_out to 20:30 (8:30 PM) for active shifts where clock_out is NULL

    and the user has an applicable schedule for today with an end time of 8:30 PM (20:30)
    under strict schedule mode. Applies only on weekdays (Monday - Friday).

    Returns:
        Number of attendance records updated.
    """
    now = get_now()
    eval_date = target_date or now.date()

    # Verify weekday (0 = Monday, ..., 4 = Friday, 5 = Saturday, 6 = Sunday)
    if eval_date.weekday() > 4:
        logger.info(f"Skipping auto_clock_out_strict_shift: {eval_date} is not a weekday.")
        return 0

    settings = GlobalSettings.get()
    if not settings or not settings.enable_strict_schedule:
        logger.info("Skipping auto_clock_out_strict_shift: strict schedule is not enabled.")
        return 0

    # Day mapping
    day_name = eval_date.strftime("%A").lower()
    day_short_map = {
        "monday": "mon",
        "tuesday": "tue",
        "wednesday": "wed",
        "thursday": "thu",
        "friday": "fri",
    }
    block_map = {
        "monday": "mw",
        "wednesday": "mw",
        "tuesday": "tth",
        "thursday": "tth",
        "friday": "fri",
    }

    short_day = day_short_map.get(day_name)
    target_block = block_map.get(day_name)

    # Fetch open attendance records for the date
    open_records = (
        Attendance.query.filter(
            Attendance.date == eval_date,
            Attendance.clock_in.isnot(None),
            Attendance.clock_out.is_(None),
        ).all()
    )

    if not open_records:
        return 0

    updated_count = 0

    for record in open_records:
        # Find active schedule for user for today
        user_schedules = []
        if short_day:
            user_schedules = Schedule.query.filter_by(
                user_id=record.user_id, day=short_day
            ).all()
        if not user_schedules and target_block:
            user_schedules = Schedule.query.filter_by(
                user_id=record.user_id, day=target_block
            ).all()

        is_matching_shift = False
        for sched in user_schedules:
            if getattr(sched, "is_open_time", False):
                continue

            # Primary shift check: schedule end time is 20:30 (8:30 PM)
            if sched.end_time == clock_out_target:
                is_matching_shift = True
                break

            # Split shift second block check: split schedule end time is 20:30 (8:30 PM)
            if sched.is_split_shift and sched.split_end_time == clock_out_target:
                is_matching_shift = True
                break

        if is_matching_shift:
            record.clock_out = clock_out_target
            updated_count += 1
            system_log_entry(
                action="Auto Clock Out",
                details=(
                    f"Auto-filled 8:30 clock-out for user {record.user_id} "
                    f"under strict schedule (scheduled end: 8:30 PM) on {eval_date}."
                ),
                user_id=record.user_id,
            )

    if updated_count > 0:
        try:
            db.session.commit()
            logger.info(
                f"Auto clock-out completed: updated {updated_count} records to {clock_out_target}."
            )
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to commit strict auto clock-outs: {e}")
            raise

    return updated_count


def auto_clock_out(buffer_hours: int = 4) -> int:
    """Auto clock-out any active shifts from previous days or past reasonable shift hours.

    Returns the number of records updated.
    """
    now = get_now()
    today = now.date()
    settings = GlobalSettings.get()
    default_end = settings.default_end if settings and settings.default_end else None

    # Find records with no clock_out from earlier days or active today
    open_records = Attendance.query.filter(
        Attendance.clock_in.isnot(None),
        Attendance.clock_out.is_(None),
    ).all()

    updated_count = 0

    for record in open_records:
        record_dt = datetime.combine(record.date, record.clock_in)
        # If record is from a previous day or clocked in more than 14 hours ago
        if record.date < today or (now - record_dt.replace(tzinfo=now.tzinfo)) > timedelta(hours=14):
            # Attempt to find assigned schedule end time
            user_sched = Schedule.query.filter_by(user_id=record.user_id).first()
            assigned_end = (
                user_sched.end_time if user_sched and user_sched.end_time else default_end
            )

            record.clock_out = assigned_end or record.clock_in
            updated_count += 1
            system_log_entry(
                action="Auto Clock Out",
                details=f"System automatically clocked out user {record.user_id} for shift on {record.date}.",
                user_id=record.user_id,
            )

    if updated_count > 0:
        try:
            db.session.commit()
            logger.info(f"Auto clocked-out {updated_count} lingering attendance records.")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to commit auto clock-outs: {e}")

    return updated_count
