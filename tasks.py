import logging
from datetime import datetime, timedelta

from models.models import Attendance, GlobalSettings, Schedule, db
from utils.logging import system_log_entry
from utils.timezone import get_now

logger = logging.getLogger(__name__)


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
