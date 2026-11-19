from datetime import datetime, time, timedelta

import holidays
from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import func

from models.models import Attendance, GlobalSettings, Logs, Schedule, User, db
from utils.decorators import admin_required
from utils.timezone import get_now, get_time_ago

admin_bp = Blueprint("admin", __name__)


# Auto Logout redirect
@admin_bp.route("/logout")
def logout():
    return redirect(url_for("auth.logout"))


@admin_bp.route("/dashboard")
@login_required
@admin_required
def dashboard():
    now = get_now()
    today = now.date()

    # 1. METRICS (Employees, Present, Logs)
    total_employees = User.query.filter(
        User.role.notin_(["superadmin", "admin"]), User.status == "active"
    ).count()

    on_duty_list_today = (
        db.session.query(func.count(func.distinct(Attendance.user_id)))
        .filter(Attendance.date == today, Attendance.clock_in.isnot(None))
        .scalar()
        or 0
    )

    late_employees = 0
    pending_approvals = 0

    # Fetch 3 most recent activities
    recent_logs = (
        db.session.query(Logs, User)
        .outerjoin(User, Logs.user_id == User.user_id)
        .filter(Logs.user_id != "superadmin")
        .order_by(Logs.timestamp.desc())
        .limit(3)
        .all()
    )

    recent_activities = []
    for log, user in recent_logs:
        first_init = user.first_name[0].upper() if (user and user.first_name) else "S"
        last_init = user.last_name[0].upper() if (user and user.last_name) else "Y"
        user_name = f"{user.first_name} {user.last_name}" if user else "System"

        status_text = "Recorded"
        status_class = "neutral"
        action_lower = log.action.lower() if log.action else ""

        if "clock in" in action_lower:
            status_text = "Clock In"
            status_class = "on-time"
        elif "clock out" in action_lower:
            status_text = "Clock Out"
            status_class = "completed"
        elif "error" in action_lower or "failed" in action_lower:
            status_text = "Alert"
            status_class = "negative"

        recent_activities.append(
            {
                "initials": f"{first_init}{last_init}",
                "name": user_name,
                "action": log.details or log.action,
                "time": get_time_ago(log.timestamp),
                "status": status_text,
                "status_class": status_class,
            }
        )

    # 2. SHIFT PERFORMANCE METRICS
    completed_records = Attendance.query.filter(
        Attendance.date == today, Attendance.clock_out.isnot(None)
    ).all()

    total_seconds_worked = 0
    total_overtime_seconds = 0
    compliant_shifts_count = 0

    compliance_limit = timedelta(hours=4)
    overtime_threshold = timedelta(hours=4)

    for record in completed_records:
        if record.clock_in and record.clock_out:
            dt_in = datetime.combine(record.date, record.clock_in)
            dt_out = datetime.combine(today, record.clock_out)

            duration = dt_out - dt_in
            total_seconds_worked += duration.total_seconds()

            if duration > overtime_threshold:
                overtime_duration = duration - overtime_threshold
                total_overtime_seconds += overtime_duration.total_seconds()

            if duration <= compliance_limit:
                compliant_shifts_count += 1

    total_hours_worked = total_seconds_worked / 3600
    overtime_hours = round(total_overtime_seconds / 3600, 2)

    num_completed_shifts = len(completed_records)
    if num_completed_shifts > 0:
        average_hours_worked = round(total_hours_worked / num_completed_shifts, 2)
        compliance_rate = round((compliant_shifts_count / num_completed_shifts) * 100)
    else:
        average_hours_worked = 0.0
        compliance_rate = 0

    # 3. TREND CALCULATIONS
    avg_diff = round(average_hours_worked - 4, 2)
    average_trend_class = "positive" if average_hours_worked >= 4 else "negative"
    average_trend_text = f"+{avg_diff} hrs" if avg_diff > 0 else f"{avg_diff} hrs"

    overtime_trend_class = "negative" if overtime_hours > 0 else "positive"
    overtime_trend_text = f"+{overtime_hours} hrs" if overtime_hours > 0 else f"{overtime_hours} hrs"

    comp_diff = compliance_rate - 75
    compliance_trend_class = "positive" if compliance_rate >= 75 else "negative"
    compliance_trend_text = f"+{comp_diff}%" if comp_diff > 0 else f"{comp_diff}%"

    return render_template(
        "admin/dashboard.html",
        user=current_user,
        current_time=now.strftime("%A, %B %d, %Y"),
        total_employees=total_employees,
        on_duty_list_today=on_duty_list_today,
        late_employees=late_employees,
        pending_approvals=pending_approvals,
        recent_activities=recent_activities,
        average_hours_worked=average_hours_worked,
        average_trend_class=average_trend_class,
        average_trend_text=average_trend_text,
        overtime_hours=overtime_hours,
        overtime_trend_class=overtime_trend_class,
        overtime_trend_text=overtime_trend_text,
        compliance_rate=compliance_rate,
        compliance_trend_class=compliance_trend_class,
        compliance_trend_text=compliance_trend_text,
    )


# VIEW USERS PAGE
@admin_bp.route("/users")
@login_required
@admin_required
def users():
    users_list = User.query.filter(
        User.role != "superadmin", User.status == "active"
    ).all()
    return render_template("admin/users.html", current_user=current_user, users=users_list)


# GIA SCHEDULE PAGE
@admin_bp.route("/gia-schedule")
@login_required
@admin_required
def gia_schedule():
    users_list = User.query.filter(User.role == "gia", User.status == "active").all()
    schedules = Schedule.query.all()
    return render_template("admin/schedule.html", users=users_list, schedules=schedules)


# DAILY LOGS PAGE
@admin_bp.route("/daily-logs", methods=["GET"])
@login_required
@admin_required
def daily_logs():
    users_list = (
        User.query.filter(User.role == "gia", User.status == "active")
        .order_by(User.first_name)
        .all()
    )
    today = get_now().date()
    return render_template("admin/daily_logs.html", today=today, users=users_list)


# EXPORT DTR PAGE
@admin_bp.route("/export-dtr")
@login_required
@admin_required
def export_dtr():
    selected_month = request.args.get("month", "").strip() or get_now().strftime("%Y-%m")
    return render_template("admin/export_dtr.html", month=selected_month)


# DTR PRINT PAGE
@admin_bp.route("/export")
@login_required
@admin_required
def export_pdf():
    now = get_now()
    unit_head = GlobalSettings.get()
    selected_month = request.args.get("month", "").strip() or now.strftime("%Y-%m")

    try:
        parts = selected_month.split("-")
        year, month = int(parts[0]), int(parts[1])
        if not (1 <= month <= 12 and 2000 <= year <= 2100):
            raise ValueError()
    except (ValueError, IndexError):
        flash("Invalid month format. Defaulting to current month.", "warning")
        return redirect(url_for("admin.export_pdf", month=now.strftime("%Y-%m")))

    first_day = datetime(year, month, 1).date()
    last_day = (first_day + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    total_days = (last_day - first_day).days + 1

    try:
        local_holidays = holidays.country_holidays("PH", years=year)
    except Exception:
        local_holidays = {}

    day_status_dict = {}
    current_date = first_day
    while current_date <= last_day:
        date_str = current_date.strftime("%Y-%m-%d")
        if current_date in local_holidays:
            day_status_dict[date_str] = local_holidays.get(current_date)
        elif current_date.weekday() == 6:  # 6 is Sunday
            day_status_dict[date_str] = "Sunday"
        else:
            day_status_dict[date_str] = None
        current_date += timedelta(days=1)

    target_user_id = request.args.get("user_id", "").strip()
    if target_user_id:
        users_list = (
            User.query.filter(User.user_id == target_user_id)
            .all()
        )
        if not users_list:
            flash("Selected assistant not found.", "warning")
            return redirect(url_for("admin.export_pdf", month=selected_month))
    else:
        users_list = (
            User.query.filter(
                User.role.notin_(["superadmin", "admin"]), User.status == "active"
            )
            .order_by(User.last_name)
            .all()
        )

    attendance_records = (
        Attendance.query.filter(
            Attendance.date >= first_day, Attendance.date <= last_day
        )
        .order_by(Attendance.date, Attendance.id)
        .all()
    )

    attendance_dict = {}
    total_hours_dict = {str(u.user_id): 0.0 for u in users_list}

    def to_datetime(val, record_date):
        if val is None:
            return None
        if isinstance(val, datetime):
            return val
        if isinstance(val, time):
            return datetime.combine(record_date, val)
        try:
            return datetime.fromisoformat(str(val))
        except Exception:
            return None

    for record in attendance_records:
        user_key = str(record.user_id)
        date_key = record.date.strftime("%Y-%m-%d")

        attendance_dict.setdefault(user_key, {}).setdefault(
            date_key,
            {
                "shift1": {"in": None, "out": None},
                "shift2": {"in": None, "out": None},
            },
        )

        slot = attendance_dict[user_key][date_key]
        cin = to_datetime(record.clock_in, record.date)
        cout = to_datetime(record.clock_out, record.date)

        if cin and cout:
            if not slot["shift1"]["in"]:
                slot["shift1"]["in"] = cin
                slot["shift1"]["out"] = cout
            elif slot["shift1"]["out"] is None:
                slot["shift1"]["out"] = cout
            else:
                slot["shift2"]["in"] = cin
                slot["shift2"]["out"] = cout

    for user in users_list:
        user_key = str(user.user_id)
        total_seconds = 0
        for _date_key, shifts in attendance_dict.get(user_key, {}).items():
            for shift in ("shift1", "shift2"):
                t_in = shifts[shift]["in"]
                t_out = shifts[shift]["out"]
                if not t_in or not t_out:
                    continue
                start_dt = t_in
                end_dt = t_out
                if end_dt < start_dt:
                    end_dt += timedelta(days=1)
                total_seconds += (end_dt - start_dt).total_seconds()

        decimal_hours = round(total_seconds / 3600, 2)
        total_hours_dict[user_key] = decimal_hours

    user_pairs = [users_list[i : i + 2] for i in range(0, len(users_list), 2)]

    return render_template(
        "admin/dtr_report.html",
        now=now,
        user_pairs=user_pairs,
        month=month,
        year=year,
        total_days=total_days,
        datetime=datetime,
        unit_head=unit_head.unit_head if unit_head else "N/A",
        attendance_dict=attendance_dict,
        total_hours_dict=total_hours_dict,
        day_status_dict=day_status_dict,
    )


# Account Settings redirects to Profile (where password change is handled)
@admin_bp.route("/account-settings", methods=["GET", "POST"])
@login_required
@admin_required
def account_settings():
    return redirect(url_for("admin.profile"))


# SETTINGS PAGE
@admin_bp.route("/settings")
@login_required
@admin_required
def settings():
    return render_template("admin/settings.html")


# ADMIN PROFILE PAGE
@admin_bp.route("/profile")
@login_required
@admin_required
def profile():
    return render_template("admin/profile.html", user=current_user)


# AUDIT LOG PAGE
@admin_bp.route("/audit-logs")
@login_required
@admin_required
def audit_logs():
    today = get_now().date()
    return render_template("admin/audit_logs.html", today=today)


# GIA LOGS & ANALYTICS PAGE
@admin_bp.route("/gia-logs")
@login_required
@admin_required
def gia_logs():
    selected_user_id = request.args.get("user_id", "").strip()
    selected_month = request.args.get("month", "").strip() or get_now().strftime("%Y-%m")

    gia_users = (
        User.query.filter(User.role == "gia")
        .order_by(User.status.asc(), User.last_name.asc(), User.first_name.asc())
        .all()
    )

    selected_gia = None
    if selected_user_id:
        selected_gia = User.query.filter_by(user_id=selected_user_id).first()
    elif gia_users:
        selected_gia = gia_users[0]
        selected_user_id = selected_gia.user_id

    return render_template(
        "admin/gia_logs.html",
        gia_users=gia_users,
        selected_gia=selected_gia,
        selected_user_id=selected_user_id,
        selected_month=selected_month,
    )

