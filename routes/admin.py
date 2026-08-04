from flask import (Blueprint, render_template, redirect, url_for, request, flash, 
                   send_file, session, request)
from flask_login import login_required, logout_user, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from collections import defaultdict
from datetime import datetime, timedelta, date, time
from zoneinfo import ZoneInfo
from models.models import db, User, Attendance, Schedule, GlobalSettings, Logs
from sqlalchemy.exc import IntegrityError
from flask_apscheduler import APScheduler
from sqlalchemy import func
import holidays

# Create a Blueprint for admin routes
admin_bp = Blueprint('admin', __name__)

class Config:
    SCHEDULER_API_ENABLED = True

scheduler = APScheduler()

MANILA_TZ = ZoneInfo("Asia/Manila")
now = datetime.now(MANILA_TZ)

# Auto Logout
@admin_bp.route('/logout')
def logout():
    logout_user()  # Logs out the user
    session.clear()  # Clears session data
    return render_template('auth/login.html')  # Redirect to login page

def get_time_ago(log_time):
    now = now()
    diff = now - log_time
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return "Just now"
    elif seconds < 3600:
        mins = int(seconds // 60)
        return f"{mins} minute{'s' if mins != 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds // 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    else:
        days = int(seconds // 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"

from datetime import datetime, timedelta
from flask import render_template, redirect, url_for, flash
from sqlalchemy import func
# Ensure your models are imported: db, User, Attendance, Logs

def get_time_ago(log_time):
    """Converts a datetime object into a relative 'X minutes ago' string."""
    now = now()
    diff = now - log_time
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return "Just now"
    elif seconds < 3600:
        mins = int(seconds // 60)
        return f"{mins} minute{'s' if mins != 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds // 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    else:
        days = int(seconds // 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"


@admin_bp.route('/dashboard')
@login_required
def dashboard():
    # Security Check
    if current_user.role not in ["superadmin", "admin"]:
        flash("Access Denied!", "danger")
        return redirect(url_for('auth_bp.login')) 
    
    today = now().date()

    # ==========================================
    # 1. NEW METRICS (Employees, Present, Logs)
    # ==========================================
    
    total_employees = User.query.filter(User.role.notin_(["superadmin", "admin"]), User.status == "active").count()
    
    on_duty_list_today = db.session.query(func.count(func.distinct(Attendance.user_id))).filter(
        Attendance.date == today,
        Attendance.clock_in.isnot(None)
    ).scalar() or 0

    # TODO: Update these based on your specific models
    late_employees = 0 
    pending_approvals = 0

    # Fetch the 3 most recent activities, excluding superadmins
    recent_logs = db.session.query(Logs, User).join(
        User, Logs.user_id == User.user_id
    ).filter(
        User.role != 'superadmin'  # Exclude superadmin logs
    ).order_by(
        Logs.timestamp.desc()
    ).limit(3).all() # Limit to exactly 3

    recent_activities = []
    for log, user in recent_logs:
        # Extract initials safely
        first_init = user.first_name[0].upper() if user.first_name else ""
        last_init = user.last_name[0].upper() if user.last_name else ""
        
        # Determine status badge styling
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

        recent_activities.append({
            'initials': f"{first_init}{last_init}",
            'name': f"{user.first_name} {user.last_name}",
            'action': log.details or log.action, 
            'time': get_time_ago(log.timestamp),
            'status': status_text,
            'status_class': status_class
        })

    # ==========================================
    # 2. OLD METRICS (Hours & Compliance Math)
    # ==========================================

    completed_records = Attendance.query.filter(
        Attendance.date == today,
        Attendance.clock_out.isnot(None)
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
        # Convert compliance to a percentage
        compliance_rate = round((compliant_shifts_count / num_completed_shifts) * 100)
    else:
        average_hours_worked = 0.0
        compliance_rate = 0

    # ==========================================
    # 3. TREND CALCULATIONS
    # ==========================================

    # Average Hours Logic
    avg_diff = round(average_hours_worked - 4, 2)
    average_trend_class = "positive" if average_hours_worked >= 4 else "negative"
    average_trend_text = f"+{avg_diff} hrs" if avg_diff > 0 else f"{avg_diff} hrs"

    # Overtime Logic
    overtime_trend_class = "negative" if overtime_hours > 0 else "positive" # usually overtime is "negative" for employers, flip if needed
    overtime_trend_text = f"+{overtime_hours} hrs" if overtime_hours > 0 else f"{overtime_hours} hrs"

    # Compliance Logic
    comp_diff = compliance_rate - 75
    compliance_trend_class = "positive" if compliance_rate >= 75 else "negative"
    compliance_trend_text = f"+{comp_diff}%" if comp_diff > 0 else f"{comp_diff}%"

    # ==========================================
    # 4. RENDER TEMPLATE
    # ==========================================

    return render_template(
        'admin/dashboard.html',
        
        # Current User & Basics
        user=current_user,
        current_time=now().strftime("%A, %B %d, %Y"),
        
        # Summary Counters
        total_employees=total_employees,
        on_duty_list_today=on_duty_list_today,
        late_employees=late_employees,
        pending_approvals=pending_approvals,
        recent_activities=recent_activities,
        
        # Shift Performance Metrics
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
@admin_bp.route('/users')
@login_required
def users():
    if current_user.role not in ["superadmin", "admin"]:
        flash("Access Denied!", "danger")
        return render_template('auth/login.html')

    users = User.query.filter(User.role != "superadmin", User.status == "active").all()

    return render_template('admin/users.html', current_user=current_user)

# GIA SCHEDULE PAGE
@admin_bp.route('/gia-schedule')
@login_required
def gia_schedule():
    if current_user.role not in ["superadmin", "admin"]:
        flash("Access Denied!", "danger")
        return render_template('auth/login.html')
    
    users = User.query.filter(User.role == "gia", User.status == "active").all()
    schedules = Schedule.query.all()

    return render_template('admin/schedule.html')

# DAILY LOGS PAGE
@admin_bp.route('/daily-logs', methods=['GET'])
@login_required
def daily_logs():
    if current_user.role not in ["superadmin", "admin"]:
        flash("Access Denied!", "danger")
        return render_template('auth/login.html')
    
    users = User.query.filter(User.role == 'gia', User.status == "active").order_by(User.first_name).all()
    today = now().date()

    return render_template('admin/daily_logs.html', today=today, users=users)

# MANUAL LOGS PAGE
@admin_bp.route('/manual-logs')
@login_required
def manual_logs():
    if current_user.role not in ["superadmin", "admin"]:
        flash("Access Denied!", "danger")
        return render_template('auth/login.html')
    
    month = now().strftime("%Y-%m")

    return render_template('admin/manual_logs.html', month=month)

# EXPORT DTR PAGE
@admin_bp.route('/export-dtr')
@login_required
def export_dtr():
    if current_user.role not in ["superadmin", "admin"]:
        flash("Unauthorized access!", "danger")
        return render_template('auth/login.html')
    
    month = datetime.today().strftime('%Y-%m')

    return render_template('admin/export_dtr.html', month=month)

# DTR PRINT PAGE
@admin_bp.route('/export')
@login_required
def export_pdf():
    if current_user.role not in ["superadmin", "admin"]:
        return render_template('auth/login.html')

    unit_head = GlobalSettings.query.first()
    selected_month = request.args.get('month', '').strip() or datetime.today().strftime('%Y-%m')

    try:
        year, month = map(int, selected_month.split('-'))
    except ValueError:
        flash("Invalid month format. Defaulting to current month.", "warning")
        return redirect(url_for('admin.export_pdf', month=datetime.today().strftime('%Y-%m')))

    first_day = datetime(year, month, 1).date()
    last_day = (first_day + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    total_days = (last_day - first_day).days + 1

    local_holidays = holidays.country_holidays('PH', years=year)

    # --- NEW: Build Day Status Mapping for the Template ---
    day_status_dict = {}
    current_date = first_day
    while current_date <= last_day:
        date_str = current_date.strftime('%Y-%m-%d')
        
        if current_date in local_holidays:
            day_status_dict[date_str] = local_holidays.get(current_date) # e.g., "Christmas Day"
        elif current_date.weekday() == 6:  # 6 is Sunday in Python's datetime
            day_status_dict[date_str] = "Sunday"
        else:
            day_status_dict[date_str] = None
            
        current_date += timedelta(days=1)
    # -----------------------------------------------------

    users = User.query.filter(User.role.notin_(["superadmin", "admin"]), User.status == "active") \
                      .order_by(User.last_name).all()

    attendance_records = Attendance.query.filter(
        Attendance.date >= first_day,
        Attendance.date <= last_day
    ).order_by(Attendance.date, Attendance.id).all()

    attendance_dict = {}
    total_hours_dict = {str(user.user_id): "0:00" for user in users}

    def to_datetime(val, record_date):
        if val is None: return None
        if isinstance(val, datetime): return val
        if isinstance(val, time): return datetime.combine(record_date, val)
        try: return datetime.fromisoformat(str(val))
        except Exception: return None

    for record in attendance_records:
        user_key = str(record.user_id)
        date_key = record.date.strftime('%Y-%m-%d')

        attendance_dict.setdefault(user_key, {}).setdefault(date_key, {
            "shift1": {"in": None, "out": None},
            "shift2": {"in": None, "out": None}
        })

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

    for user in users:
        user_key = str(user.user_id)
        total_seconds = 0
        for date_key, shifts in attendance_dict.get(user_key, {}).items():
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

    user_pairs = [users[i:i + 2] for i in range(0, len(users), 2)]

    return render_template(
        'admin/dtr_report.html',
        now=now(),
        user_pairs=user_pairs,
        month=month,
        year=year,
        total_days=total_days,
        datetime=datetime,
        unit_head=unit_head.unit_head if unit_head else "N/A",
        attendance_dict=attendance_dict,
        total_hours_dict=total_hours_dict,
        day_status_dict=day_status_dict
    )

# Account Settings (Change Password)
@admin_bp.route('/account-settings', methods=['GET', 'POST'])
@login_required
def account_settings():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        # Validate current password
        if not check_password_hash(current_user.password, current_password):
            flash("Current password is incorrect!", "danger")
            return redirect(url_for('admin.account_settings'))

        # Check if new passwords match
        if new_password != confirm_password:
            flash("New passwords do not match!", "danger")
            return redirect(url_for('admin.account_settings'))

        # Enforce password strength
        if len(new_password) < 8 or not any(char.isdigit() for char in new_password):
            flash("Password must be at least 8 characters long and contain a number!", "danger")
            return redirect(url_for('admin.account_settings'))

        try:
            # Hash and update password
            current_user.password = generate_password_hash(new_password)
            db.session.commit()

            # Log the password change
            log_entry = Logs(
                admin_id=current_user.user_id,
                action="Updated Account Password",
                details="Password changed successfully."
            )
            db.session.add(log_entry)
            db.session.commit()

            flash("Password updated successfully!", "success")

        except Exception as e:
            db.session.rollback()
            flash(f"Error updating password: {e}", "danger")

    return render_template('admin/account_settings.html')

# SETTINGS PAGE
@admin_bp.route('/settings')
@login_required
def settings():
    if current_user.role not in ["superadmin", "admin"]:
        flash("Access Denied!", "danger")
        return render_template('auth/login.html')

    return render_template("admin/settings.html")

# auto-disable strict mode if expired
def update_strict_mode():
    settings = GlobalSettings.query.first()
    if not settings or settings.strict_duration is None:
        return

    today = now().date()

    if not settings.enable_strict_schedule:
        if today >= settings.strict_duration:
            settings.enable_strict_schedule = True
            settings.strict_duration = None

            entry = Logs(
                user_id="admin",
                action="Update",
                details=f"SYSTEM: Open mode expired on {today}, strict mode reactivated.",
                timestamp=now(),
            )
            db.session.add(entry)
            db.session.commit()


# ADMIN PROFILE PAGE
@admin_bp.route('/profile')
def profile():
    if current_user.role not in ["superadmin", "admin"]:
        flash("Access Denied!", "danger")
        return render_template('auth/login.html')

    return render_template("admin/profile.html", user=current_user)

# AUDIT LOG PAGE
@admin_bp.route('/audit-logs')
@login_required
def audit_logs():
    if current_user.role not in ["superadmin", "admin"]:
        flash("Unauthorized access!", "danger")
        return render_template('auth/login.html')
    
    today = now().date()

    return render_template('admin/audit_logs.html', today=today)