import contextlib
import io
import logging
import re
import traceback
from datetime import date, datetime, time, timedelta

import pandas as pd
from flask import Blueprint, jsonify, request, send_file
from flask_login import current_user, login_required
from sqlalchemy import func, or_

from models.models import (
    Attendance,
    AttendanceInconsistency,
    GlobalSettings,
    Logs,
    Schedule,
    User,
    db,
)
from routes.gia import check_attendance_flags
from utils.decorators import admin_required, ip_whitelist_required
from utils.formatters import (
    format_philippine_phone,
    parse_time,
)
from utils.logging import system_log_entry, systemLogEntry  # noqa: F401
from utils.timezone import get_now

logger = logging.getLogger(__name__)

api_bp = Blueprint("api", __name__)


# ============================================================================
# USER MANAGEMENT APIS
# ============================================================================


@api_bp.route("/users-data", methods=["GET"])
@login_required
@admin_required
def get_data():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    search = request.args.get("search", "", type=str).strip()
    status = request.args.get("status", "", type=str).strip()
    role = request.args.get("role", "", type=str).strip()

    page = max(page, 1)
    per_page = max(1, min(per_page, 100))

    query = User.query.filter(User.role != "superadmin")

    if status:
        query = query.filter(User.status == status)
    if role:
        query = query.filter(User.role == role)
    if search:
        search_pattern = f"%{search}%"
        phone_digits = re.sub(r"\D+", "", search)
        filters = [
            User.first_name.ilike(search_pattern),
            User.last_name.ilike(search_pattern),
            User.user_id.ilike(search_pattern),
            User.phone_number.ilike(search_pattern),
            User.laboratory.ilike(search_pattern),
        ]
        if phone_digits:
            filters.append(User.phone_number.ilike(f"%{phone_digits}%"))
            if phone_digits.startswith("0"):
                local_digits = phone_digits[1:]
                filters.append(User.phone_number.ilike(f"%63{local_digits}%"))
            elif phone_digits.startswith("63"):
                filters.append(User.phone_number.ilike(f"%{phone_digits[2:]}%"))
        query = query.filter(or_(*filters))

    total = query.count()
    users = (
        query.order_by(User.role, User.first_name)
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    users_list = [
        {
            "user_id": user.user_id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "middle_name": user.middle_name,
            "role": user.role,
            "status": user.status,
            "phone_number": user.phone_number or "",
            "laboratory": user.laboratory or "",
        }
        for user in users
    ]

    return jsonify(
        {
            "success": True,
            "users": users_list,
            "total": total,
            "page": page,
            "per_page": per_page,
        }
    )


@api_bp.route("/add-user", methods=["POST"])
@login_required
@admin_required
def add_user():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "error": "Invalid or missing JSON data"}), 400

    user_id = str(data.get("userId", "")).strip()
    first_name = str(data.get("firstName", "")).strip()
    last_name = str(data.get("lastName", "")).strip()
    middle_initial = str(data.get("middleInitial", "")).strip()
    role = str(data.get("role", "")).strip()
    phone_number = format_philippine_phone(data.get("phoneNumber"))
    laboratory = data.get("laboratory")

    if not user_id or not first_name or not last_name or not role:
        return jsonify({"success": False, "error": "User ID, First Name, Last Name, and Role are required."}), 400

    if role not in ["admin", "gia"]:
        return jsonify({"success": False, "error": "Invalid role specified."}), 400

    # Check if user already exists
    if User.query.filter_by(user_id=user_id).first():
        return jsonify({"success": False, "error": "User ID already exists"}), 400

    # Create and save new user
    new_user = User(
        user_id=user_id,
        first_name=first_name,
        last_name=last_name,
        phone_number=phone_number,
        laboratory=laboratory,
        middle_name=middle_initial.upper() if middle_initial else None,
        role=role,
    )
    new_user.set_password("admin123")
    db.session.add(new_user)
    db.session.commit()

    system_log_entry(
        action="Created",
        details=f"User '{new_user.first_name} {new_user.last_name}' (ID: {new_user.user_id}) was created by {current_user.first_name} {current_user.last_name}.",
    )

    return jsonify({"success": True}), 200


@api_bp.route("/get-user/<string:user_id>", methods=["GET"])
@login_required
@admin_required
def get_user(user_id):
    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    user_data = {
        "user_id": user.user_id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "middle_name": user.middle_name[0] if user.middle_name else "",
        "role": user.role,
        "status": user.status,
        "phone_number": user.phone_number or "",
        "laboratory": user.laboratory or "",
    }

    return jsonify(user_data)


@api_bp.route("/update-user/<string:user_id>", methods=["POST"])
@login_required
@admin_required
def update_user(user_id):
    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify({"success": False, "error": "User not found"}), 404

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "error": "Invalid or missing JSON data"}), 400

    # Update user fields
    user.user_id = data.get("userId", user.user_id)
    user.first_name = data.get("firstName", user.first_name)
    user.last_name = data.get("lastName", user.last_name)
    middle_initial = data.get("middleInitial")
    if middle_initial is not None:
        user.middle_name = middle_initial.upper() if middle_initial else None
    user.phone_number = format_philippine_phone(data.get("phoneNumber")) or user.phone_number
    user.laboratory = data.get("laboratory", user.laboratory)
    user.role = data.get("role", user.role)
    user.status = data.get("status", user.status)

    try:
        db.session.commit()
        system_log_entry(
            action="Updated",
            details=f"#{user.id} User '{user.first_name} {user.last_name}' (ID: {user.user_id}) was updated by {current_user.first_name} {current_user.last_name}.",
        )
        return jsonify({"success": True, "message": "User updated successfully!"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": f"Error updating user: {e!s}"}), 500


@api_bp.route("/delete-user/<string:user_id>", methods=["POST"])
@login_required
@admin_required
def delete_user_page(user_id):
    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify({"success": False, "error": "User not found"}), 404

    if user.user_id == current_user.user_id:
        return jsonify({"success": False, "error": "You cannot delete your own account."}), 400

    try:
        # Delete related attendance records
        Attendance.query.filter_by(user_id=user.user_id).delete()

        system_log_entry(
            action="Deleted",
            details=f"User '{user.first_name} {user.last_name}' (ID: {user.user_id}) was deleted by {current_user.first_name} {current_user.last_name}.",
        )

        db.session.delete(user)
        db.session.commit()

        return jsonify({"success": True, "message": "User deleted successfully!"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": f"Error deleting user: {e!s}"}), 500


@api_bp.route("/export-users", methods=["GET"])
@login_required
@admin_required
def export_users():
    users = sorted(
        User.query.filter(User.role == "gia", User.status == "active").all(),
        key=lambda x: (x.last_name, x.first_name),
    )

    data = {
        "User ID": [u.user_id for u in users],
        "Last Name": [u.last_name for u in users],
        "First Name": [u.first_name for u in users],
        "Middle Initial": [u.middle_name[0].upper() if u.middle_name else "" for u in users],
        "Phone Number": [u.phone_number for u in users],
        "Laboratory": [u.laboratory for u in users],
    }

    df = pd.DataFrame(data)
    csv_data = df.to_csv(index=False)
    output = io.BytesIO()
    output.write(csv_data.encode("utf-8"))
    output.seek(0)

    filename = f"GIA List {get_now().strftime('%m-%d-%Y')}.csv"
    return send_file(output, mimetype="text/csv", as_attachment=True, download_name=filename)


@api_bp.route("/export-gia-logs", methods=["GET"])
@login_required
@admin_required
def export_gia_logs():
    user_id = request.args.get("user_id", "").strip()
    month_str = request.args.get("month", "").strip() or get_now().strftime("%Y-%m")

    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify({"success": False, "error": "User not found"}), 404

    try:
        parts = month_str.split("-")
        year, month = int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        now = get_now()
        year, month = now.year, now.month

    records = (
        Attendance.query.filter(
            Attendance.user_id == user_id,
            db.extract("year", Attendance.date) == year,
            db.extract("month", Attendance.date) == month,
        )
        .order_by(Attendance.date.asc(), Attendance.id.asc())
        .all()
    )

    data = []
    for r in records:
        cin = r.clock_in.strftime("%I:%M %p") if r.clock_in else ""
        cout = r.clock_out.strftime("%I:%M %p") if r.clock_out else ""
        hours = 0.0
        if r.clock_in and r.clock_out:
            clock_in_dt = datetime.combine(r.date, r.clock_in)
            clock_out_dt = datetime.combine(r.date, r.clock_out)
            hours = round(max(0.0, (clock_out_dt - clock_in_dt).total_seconds()) / 3600, 2)

        data.append(
            {
                "Date": r.date.strftime("%Y-%m-%d"),
                "User ID": user.user_id,
                "Name": f"{user.last_name}, {user.first_name}",
                "Clock In": cin,
                "Clock Out": cout,
                "Rendered Hours": hours,
                "Is Manual": "Yes" if r.is_manual else "No",
            }
        )

    df = pd.DataFrame(data)
    csv_data = df.to_csv(index=False)
    output = io.BytesIO()
    output.write(csv_data.encode("utf-8"))
    output.seek(0)

    filename = f"Attendance_Logs_{user.user_id}_{month_str}.csv"
    return send_file(output, mimetype="text/csv", as_attachment=True, download_name=filename)



# ============================================================================
# SCHEDULE APIS
# ============================================================================


def serialize_schedule(s):
    primary_h = 0.0
    split_h = 0.0
    if s.start_time and s.end_time:
        diff1 = (datetime.combine(date.min, s.end_time) - datetime.combine(date.min, s.start_time)).total_seconds()
        if diff1 < 0:
            diff1 += 86400
        primary_h = diff1 / 3600.0
    if s.is_split_shift and s.split_start_time and s.split_end_time:
        diff2 = (datetime.combine(date.min, s.split_end_time) - datetime.combine(date.min, s.split_start_time)).total_seconds()
        if diff2 < 0:
            diff2 += 86400
        split_h = diff2 / 3600.0

    daily_h = round(primary_h + split_h, 2)

    return {
        "user_id": s.user_id,
        "day": s.day,
        "start_time": s.start_time.strftime("%I:%M %p") if s.start_time else "",
        "end_time": s.end_time.strftime("%I:%M %p") if s.end_time else "",
        "is_split_shift": bool(s.is_split_shift),
        "split_start_time": s.split_start_time.strftime("%I:%M %p") if s.split_start_time else "",
        "split_end_time": s.split_end_time.strftime("%I:%M %p") if s.split_end_time else "",
        "daily_hours": daily_h,
    }


@api_bp.route("/get-schedules", methods=["GET"])
@login_required
@admin_required
def get_schedules():
    page = request.args.get("page", type=int)
    per_page = request.args.get("per_page", type=int)
    search = request.args.get("search", "", type=str).strip()
    status = request.args.get("status", "", type=str).strip()
    role = request.args.get("role", "", type=str).strip()

    query = User.query.filter(
        User.role != "superadmin",
        User.role != "admin",
    )

    if status:
        query = query.filter(User.status == status)
    if role:
        query = query.filter(User.role == role)
    if search:
        search_pattern = f"%{search}%"
        phone_digits = re.sub(r"\D+", "", search)
        filters = [
            User.first_name.ilike(search_pattern),
            User.last_name.ilike(search_pattern),
            User.user_id.ilike(search_pattern),
            User.laboratory.ilike(search_pattern),
        ]
        if phone_digits:
            filters.append(User.phone_number.ilike(f"%{phone_digits}%"))
        query = query.filter(or_(*filters))

    total = query.count()
    if page and per_page and per_page > 0:
        page = max(page, 1)
        users = (
            query.order_by(User.first_name)
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
    else:
        users = query.order_by(User.first_name).all()

    schedules = Schedule.query.filter(
        Schedule.day.in_(["mw", "tth", "fri", "sat", "mon", "tue", "wed", "thu"])
    ).all()
    sched_list = [serialize_schedule(s) for s in schedules]
    users_list = [
        {
            "user_id": u.user_id,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "role": u.role,
            "status": u.status,
            "laboratory": u.laboratory or "",
        }
        for u in users
    ]

    return jsonify({
        "schedules": sched_list,
        "users": users_list,
        "total": total,
        "page": page or 1,
        "per_page": per_page or len(users_list),
    })


@api_bp.route("/get-schedule/<string:user_id>", methods=["GET"])
@login_required
def get_user_schedule(user_id):
    if current_user.role not in ["superadmin", "admin"] and current_user.user_id != user_id:
        return jsonify({"success": False, "error": "Access Denied"}), 403

    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify({"success": False, "error": "User not found"}), 404

    schedules = Schedule.query.filter_by(user_id=user_id).all()

    user_data = {
        "user_id": user.user_id,
        "full_name": f"{user.first_name} {user.last_name}",
    }

    user_schedules = [
        {
            "id": s.id,
            "day": s.day,
            "start_time": s.start_time.strftime("%H:%M") if s.start_time else None,
            "end_time": s.end_time.strftime("%H:%M") if s.end_time else None,
            "is_split_shift": s.is_split_shift,
            "split_start_time": s.split_start_time.strftime("%H:%M") if s.split_start_time else None,
            "split_end_time": s.split_end_time.strftime("%H:%M") if s.split_end_time else None,
        }
        for s in schedules
    ]

    return jsonify(
        {
            "user": user_data,
            "schedules": user_schedules,
            "success": True,
        }
    )


@api_bp.route("/update-schedule/<string:user_id>", methods=["POST"])
@login_required
@admin_required
def update_schedule(user_id):
    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify({"success": False, "error": "User not found"}), 404

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "error": "Invalid or missing JSON data"}), 400

    schedule_mode = data.get("schedule_mode", "block")  # 'block' or 'daily'
    schedules = data.get("schedules", [])
    broken_scheds = data.get("brokenSched", [])

    all_allowed_days = ["mw", "tth", "fri", "sat", "mon", "tue", "wed", "thu"]
    active_target_days = ["mon", "tue", "wed", "thu", "fri", "sat"] if schedule_mode == "daily" else ["mw", "tth", "fri", "sat"]

    try:
        # If switching modes or updating, clear or nullify irrelevant days for this user
        # (e.g. if switching to 'daily', clear old 'mw' and 'tth'; if switching to 'block', clear 'mon', 'tue', 'wed', 'thu')
        days_to_clear = [d for d in all_allowed_days if d not in active_target_days]
        if days_to_clear:
            Schedule.query.filter(
                Schedule.user_id == user_id,
                Schedule.day.in_(days_to_clear)
            ).delete(synchronize_session="fetch")

        for day in active_target_days:
            match = next((s for s in schedules if s.get("day") == day), None)
            broken_match = next((b for b in broken_scheds if b.get("day") == day), None)

            start_time = parse_time(match.get("start_time")) if match else None
            end_time = parse_time(match.get("end_time")) if match else None
            split_start_time = parse_time(broken_match.get("split_start_time")) if broken_match else None
            split_end_time = parse_time(broken_match.get("split_end_time")) if broken_match else None

            is_broken = bool(split_start_time and split_end_time)

            sched = Schedule.query.filter_by(user_id=user_id, day=day).first()

            if sched:
                sched.start_time = start_time
                sched.end_time = end_time
                sched.split_start_time = split_start_time
                sched.split_end_time = split_end_time
                sched.is_split_shift = is_broken
            elif match or broken_match:
                new_sched = Schedule(
                    user_id=user_id,
                    day=day,
                    start_time=start_time,
                    end_time=end_time,
                    split_start_time=split_start_time,
                    split_end_time=split_end_time,
                    is_split_shift=is_broken,
                )
                db.session.add(new_sched)

        db.session.commit()
        system_log_entry(
            action="Updated",
            details=f"Schedule for user '{user.first_name} {user.last_name}' (ID: {user.user_id}) was updated by {current_user.first_name} {current_user.last_name}.",
        )
        return jsonify({"success": True, "message": "Schedule updated successfully!"})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating schedule: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/purge-schedules", methods=["POST"])
@login_required
@admin_required
def purge_schedules():
    try:
        db.session.query(Schedule).update(
            {
                Schedule.start_time: None,
                Schedule.end_time: None,
                Schedule.is_split_shift: False,
                Schedule.split_start_time: None,
                Schedule.split_end_time: None,
            }
        )
        db.session.commit()

        system_log_entry(
            action="Deleted",
            details=f"All schedules were purged by {current_user.first_name} {current_user.last_name}.",
        )
        return jsonify({"success": True, "message": "All schedules cleared successfully!"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": f"Error clearing schedules: {e!s}"}), 500


# ============================================================================
# AUDIT LOGS APIS
# ============================================================================


def serialize_logs(log_entry):
    role = "GIA"
    user_name = "System"

    if log_entry.user:
        user_name = f"{log_entry.user.first_name} {log_entry.user.last_name}"
        role = "Admin" if log_entry.user.role in ["superadmin", "admin"] else "GIA"
    elif log_entry.user_id:
        user_name = f"User ({log_entry.user_id})"

    return {
        "date": log_entry.timestamp.strftime("%b %d, %Y"),
        "time": log_entry.timestamp.strftime("%I:%M %p"),
        "full_name": user_name,
        "role": role,
        "action": log_entry.action,
        "details": log_entry.details or "",
        "ip": log_entry.client_ip or "",
    }


@api_bp.route("/get-logs", methods=["GET"])
@login_required
@admin_required
def get_logs():
    now = get_now()
    today_str = now.strftime("%Y-%m-%d")

    from_date = request.args.get("from", "").strip() or today_str
    to_date = request.args.get("to", "").strip() or today_str
    user_filter = request.args.get("user", "", type=str)
    action_filter = request.args.get("action", "", type=str)
    search_term = request.args.get("search", "", type=str)
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    try:
        from_date_obj = datetime.strptime(from_date, "%Y-%m-%d")
    except ValueError:
        from_date_obj = now.replace(hour=0, minute=0, second=0, microsecond=0)

    try:
        to_date_obj = datetime.strptime(to_date, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)
    except ValueError:
        to_date_obj = now.replace(hour=23, minute=59, second=59, microsecond=999999)

    query = Logs.query.outerjoin(User).filter(
        Logs.timestamp >= from_date_obj,
        Logs.timestamp <= to_date_obj,
    )

    if user_filter:
        user_term = user_filter.strip().lower()
        query = query.filter(
            or_(
                func.lower(User.first_name).contains(user_term),
                func.lower(User.last_name).contains(user_term),
                func.lower(User.role).contains(user_term),
            )
        )

    if action_filter:
        query = query.filter(func.lower(Logs.action) == action_filter.strip().lower())

    if search_term:
        search_value = f"%{search_term.strip().lower()}%"
        query = query.filter(
            or_(
                func.lower(Logs.action).contains(search_value),
                func.lower(Logs.details).contains(search_value),
                func.lower(User.first_name).contains(search_value),
                func.lower(User.last_name).contains(search_value),
                func.lower(User.role).contains(search_value),
            )
        )

    pagination = query.order_by(Logs.id.desc()).paginate(page=page, per_page=per_page, error_out=False)
    logs_list = [serialize_logs(item) for item in pagination.items]

    return jsonify(
        {
            "logs": logs_list,
            "page": pagination.page,
            "pages": pagination.pages,
            "total": pagination.total,
            "per_page": pagination.per_page,
        }
    )


# ============================================================================
# DAILY ATTENDANCE LOGS APIS
# ============================================================================


def serialize_drecords(s):
    if s.clock_in and s.clock_out:
        clock_in_dt = datetime.combine(s.date, s.clock_in)
        clock_out_dt = datetime.combine(s.date, s.clock_out)
        time_diff = clock_out_dt - clock_in_dt
        t_hours = round(max(0.0, time_diff.total_seconds()) / 3600, 2)
    else:
        t_hours = 0.0

    name_init = "NA"
    full_name = "Unknown"
    user_id = s.user_id

    if s.user:
        first_i = s.user.first_name[0].upper() if s.user.first_name else ""
        last_i = s.user.last_name[0].upper() if s.user.last_name else ""
        name_init = f"{first_i}{last_i}" or "NA"
        full_name = f"{s.user.first_name} {s.user.last_name}"

    return {
        "name_initial": name_init,
        "full_name": full_name,
        "user_id": user_id,
        "log_id": s.id,
        "date": s.date.strftime("%Y-%m-%d"),
        "clock_in": s.clock_in.strftime("%I:%M %p").lower() if s.clock_in else "",
        "clock_out": s.clock_out.strftime("%I:%M %p").lower() if s.clock_out else "",
        "total_hours": t_hours,
    }


@api_bp.route("/get-daily-logs", methods=["GET"])
@login_required
@admin_required
def get_daily_logs():
    today_str = request.args.get("today", "").strip() or get_now().strftime("%Y-%m-%d")

    try:
        query_date = datetime.strptime(today_str, "%Y-%m-%d").date()
    except ValueError:
        query_date = get_now().date()

    records = (
        Attendance.query.join(User)
        .filter(Attendance.date == query_date, User.status == "active")
        .order_by(Attendance.id.desc())
        .all()
    )

    records_list = [serialize_drecords(s) for s in records]
    return jsonify(records_list)


@api_bp.route("/get-user-log/<string:log_id>", methods=["GET"])
@login_required
@admin_required
def get_user_log(log_id):
    record = db.session.get(Attendance, log_id)
    if not record:
        return jsonify({"success": False, "error": "Log record not found"}), 404

    user_name = f"{record.user.first_name} {record.user.last_name}" if record.user else "Unknown"
    user_record = {
        "log_id": record.id,
        "full_name": user_name,
        "clock_in": record.clock_in.strftime("%H:%M") if record.clock_in else "",
        "clock_out": record.clock_out.strftime("%H:%M") if record.clock_out else "",
    }

    return jsonify(user_record)


@api_bp.route("/update-log/<string:log_id>", methods=["POST"])
@login_required
@admin_required
def update_log(log_id):
    data = request.get_json(silent=True)
    if not data or not data.get("clockIn") or not data.get("clockOut"):
        return jsonify({"success": False, "error": "Both clockIn and clockOut are required"}), 400

    log = db.session.get(Attendance, log_id)
    if not log:
        return jsonify({"success": False, "error": "Log record not found"}), 404

    clock_in_time = parse_time(data.get("clockIn"))
    clock_out_time = parse_time(data.get("clockOut"))

    if not clock_in_time or not clock_out_time:
        return jsonify({"success": False, "error": "Invalid time format (expected HH:MM)"}), 400

    log.clock_in = clock_in_time
    log.clock_out = clock_out_time

    try:
        db.session.commit()
        user_name = f"{log.user.first_name} {log.user.last_name}" if log.user else log.user_id
        system_log_entry(
            action="Updated",
            details=f"#{log.id} Attendance record updated for {user_name}.",
        )
        return jsonify({"success": True, "message": "Log updated successfully!"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": f"Error updating log: {e!s}"}), 500


@api_bp.route("/add-log", methods=["POST"])
@login_required
@admin_required
def add_log():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "error": "Missing JSON request body"}), 400

    user_id = str(data.get("userId", "")).strip()
    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify({"success": False, "error": "User not found"}), 404

    date_str = data.get("date")
    clock_in_str = data.get("clockIn")
    clock_out_str = data.get("clockOut")

    if not date_str or not clock_in_str:
        return jsonify({"success": False, "error": "Date and clockIn are required"}), 400

    try:
        record_date = datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"success": False, "error": "Invalid date format (expected YYYY-MM-DD)"}), 400

    clock_in_time = parse_time(clock_in_str)
    clock_out_time = parse_time(clock_out_str) if clock_out_str else None

    if not clock_in_time:
        return jsonify({"success": False, "error": "Invalid clockIn time format"}), 400

    new_log = Attendance(
        user_id=user_id,
        date=record_date,
        clock_in=clock_in_time,
        clock_out=clock_out_time,
        is_manual=True,
    )

    try:
        db.session.add(new_log)
        db.session.commit()

        system_log_entry(
            action="Created",
            details=f"New manual attendance record added for {user.first_name} {user.last_name}.",
        )
        return jsonify({"success": True, "message": "Log added successfully!"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": f"Error adding log: {e!s}"}), 500


# ============================================================================
# SYSTEM SETTINGS APIS
# ============================================================================


@api_bp.route("/get-settings", methods=["GET"])
@login_required
def get_settings():
    s = GlobalSettings.get_or_create()

    settings = {
        "unit_head": s.unit_head,
        "strict": s.enable_strict_schedule,
        "strict_duration": s.strict_duration.strftime("%Y-%m-%d") if s.strict_duration else None,
        "early": s.allow_early_out,
        "overtime": s.allow_overtime,
        "def_start": s.default_start.strftime("%H:%M") if s.default_start else "08:00",
        "def_end": s.default_end.strftime("%H:%M") if s.default_end else "17:00",
        "early_allowance": s.allowed_early_in_mins,
    }

    return jsonify(settings)


@api_bp.route("/update-settings", methods=["POST"])
@login_required
@admin_required
def update_settings():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "error": "Invalid JSON data"}), 400

    settings = GlobalSettings.get_or_create()

    old_values = {
        "unit_head": settings.unit_head,
        "enable_strict_schedule": settings.enable_strict_schedule,
        "strict_duration": settings.strict_duration,
        "allowed_early_in_mins": settings.allowed_early_in_mins,
        "allow_early_out": settings.allow_early_out,
        "allow_overtime": settings.allow_overtime,
        "default_start": settings.default_start.strftime("%H:%M") if settings.default_start else None,
        "default_end": settings.default_end.strftime("%H:%M") if settings.default_end else None,
    }

    if "unitHeadName" in data:
        settings.unit_head = str(data.get("unitHeadName", "")).strip() or "Unit Head Name"

    if "enableStrictMode" in data:
        settings.enable_strict_schedule = bool(data.get("enableStrictMode"))

    if "earlyInMinutes" in data:
        with contextlib.suppress(ValueError, TypeError):
            settings.allowed_early_in_mins = max(0, int(data.get("earlyInMinutes", 0)))

    if "allowEarlyOut" in data:
        settings.allow_early_out = bool(data.get("allowEarlyOut"))

    if "allowOvertime" in data:
        settings.allow_overtime = bool(data.get("allowOvertime"))

    if "defaultStartTime" in data:
        parsed_start = parse_time(data.get("defaultStartTime"))
        if parsed_start:
            settings.default_start = parsed_start

    if "defaultEndTime" in data:
        parsed_end = parse_time(data.get("defaultEndTime"))
        if parsed_end:
            settings.default_end = parsed_end

    if not data.get("enableStrictMode"):
        duration_str = data.get("strictDuration")
        if duration_str:
            try:
                settings.strict_duration = datetime.strptime(duration_str.strip(), "%Y-%m-%d").date()
            except ValueError:
                settings.strict_duration = None
        else:
            settings.strict_duration = None
    else:
        settings.strict_duration = None

    changes = []
    for key, old_val in old_values.items():
        new_val = getattr(settings, key)
        if key in ["default_start", "default_end"] and isinstance(new_val, time):
            new_val = new_val.strftime("%H:%M")
        if str(old_val) != str(new_val):
            changes.append(f"{key}: {old_val} -> {new_val}")

    try:
        db.session.commit()
        if changes:
            system_log_entry(action="Updated", details="Settings changed: " + "; ".join(changes))
        return jsonify({"success": True, "message": "Settings updated successfully!"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": f"Error updating settings: {e!s}"}), 500


# ============================================================================
# USER PROFILE & PASSWORD APIS
# ============================================================================


@api_bp.route("/update-profile", methods=["POST"])
@login_required
def update_profile():
    data = request.get_json(silent=True) or {}

    first_name = str(data.get("firstName", "")).strip()
    last_name = str(data.get("lastName", "")).strip()
    middle_name = data.get("middleName")

    if not first_name or not last_name:
        return jsonify({"success": False, "error": "First Name and Last Name are required"}), 400

    current_user.first_name = first_name
    current_user.last_name = last_name
    current_user.middle_name = str(middle_name).strip() if middle_name else None

    try:
        db.session.commit()
        system_log_entry(
            action="Updated",
            details=f"User {current_user.user_id} updated their profile",
        )
        return (
            jsonify(
                {
                    "success": True,
                    "updated": {
                        "firstName": current_user.first_name,
                        "lastName": current_user.last_name,
                        "middleName": current_user.middle_name,
                    },
                }
            ),
            200,
        )
    except Exception:
        db.session.rollback()
        return jsonify({"success": False, "error": "Database error occurred"}), 500


@api_bp.route("/change-password", methods=["POST"])
@login_required
def change_password():
    data = request.get_json(silent=True) or {}

    current_password = data.get("currentPassword")
    new_password = data.get("newPassword")
    confirm_password = data.get("confirmPassword")

    if not current_password or not new_password or not confirm_password:
        return jsonify({"success": False, "error": "All password fields are required"}), 400

    if new_password != confirm_password:
        return jsonify({"success": False, "error": "New passwords do not match"}), 400

    if len(new_password) < 6:
        return jsonify({"success": False, "error": "Password must be at least 6 characters"}), 400

    if not current_user.check_password(current_password):
        return jsonify({"success": False, "error": "Current password is incorrect"}), 400

    current_user.set_password(new_password)

    try:
        db.session.commit()
        system_log_entry(
            action="Password Changed",
            details=f"User {current_user.user_id} updated their password",
        )
        return jsonify({"success": True}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": f"Database error occurred: {e!s}"}), 500


# ============================================================================
# GIA ATTENDANCE & STATUS APIS
# ============================================================================


@api_bp.route("/status", methods=["GET"])
@login_required
def status():
    user_id = request.args.get("user_id")

    if not user_id:
        return jsonify({"error": "Missing user_id"}), 400

    if current_user.role not in ["superadmin", "admin"] and str(current_user.user_id) != str(user_id):
        return jsonify({"success": False, "error": "Access Denied"}), 403

    now_dt = get_now()
    today = now_dt.date()

    day_name = now_dt.strftime("%A").lower()
    day_short_map = {
        "monday": "mon",
        "tuesday": "tue",
        "wednesday": "wed",
        "thursday": "thu",
        "friday": "fri",
        "saturday": "sat",
    }
    day_map = {
        "monday": "mw",
        "wednesday": "mw",
        "tuesday": "tth",
        "thursday": "tth",
        "friday": "fri",
        "saturday": "sat",
    }
    short_day = day_short_map.get(day_name)
    target_block = day_map.get(day_name)

    last_record = (
        Attendance.query.filter(Attendance.user_id == user_id, Attendance.date == today)
        .order_by(Attendance.id.desc())
        .first()
    )

    user_schedules = []
    if short_day:
        user_schedules = Schedule.query.filter_by(user_id=user_id, day=short_day).all()
    if not user_schedules and target_block:
        user_schedules = Schedule.query.filter_by(user_id=user_id, day=target_block).all()

    global_settings = GlobalSettings.get()
    strict_schedule = bool(global_settings and global_settings.enable_strict_schedule)

    schedule_end = None
    is_grace = False

    if not last_record or not last_record.clock_in:
        return (
            jsonify(
                {
                    "clocked_in": False,
                    "clocked_out": False,
                    "is_grace": False,
                }
            ),
            200,
        )

    clock_in_time = last_record.clock_in

    for sched in user_schedules:
        if sched.start_time and sched.end_time:
            dt_start = datetime.combine(today, sched.start_time)
            dt_end = datetime.combine(today, sched.end_time)
            dt_early = dt_start - timedelta(hours=1)
            dt_clock_in = datetime.combine(today, clock_in_time)

            if dt_early <= dt_clock_in <= dt_end:
                schedule_end = sched.end_time
                break

        if sched.is_split_shift and sched.split_start_time and sched.split_end_time:
            dt_split_start = datetime.combine(today, sched.split_start_time)
            dt_split_end = datetime.combine(today, sched.split_end_time)
            dt_split_early = dt_split_start - timedelta(hours=1)
            dt_clock_in = datetime.combine(today, clock_in_time)

            if dt_split_early <= dt_clock_in <= dt_split_end:
                schedule_end = sched.split_end_time
                break

    if strict_schedule and schedule_end:
        now_time = now_dt.time()
        sched_end_dt = datetime.combine(today, schedule_end)
        grace_limit = (sched_end_dt + timedelta(minutes=60)).time()
        if now_time > grace_limit:
            is_grace = True

    return (
        jsonify(
            {
                "clocked_in": bool(last_record.clock_in and not last_record.clock_out),
                "clocked_out": bool(last_record.clock_out),
                "is_grace": is_grace,
            }
        ),
        200,
    )


def evaluate_attendance_status(record, schedules_by_block=None, settings=None, current_date=None):
    """Evaluate attendance status into generic standard categories:
    - 'Completed': Both clock-in and clock-out are recorded
    - 'On Duty': Clocked in today and currently active (no clock-out yet)
    - 'Incomplete': Missing clock-out from previous days, or missing clock times
    """
    if current_date is None:
        current_date = get_now().date()

    # Both clock in and clock out are present
    if record.clock_in and record.clock_out:
        return {
            "status": "Completed",
            "badge_type": "success",
            "details": "Shift completed",
        }

    # Clock in exists but clock out is missing
    if record.clock_in and not record.clock_out:
        if record.date == current_date:
            return {
                "status": "On Duty",
                "badge_type": "info",
                "details": "Currently on duty today",
            }
        else:
            return {
                "status": "Incomplete",
                "badge_type": "warning",
                "details": "Missing clock-out on previous day",
            }

    # Neither clock in nor clock out
    return {
        "status": "Incomplete",
        "badge_type": "secondary",
        "details": "Incomplete attendance record",
    }


def serialize_records(s, schedules_by_block=None, settings=None, current_date=None):
    if s.clock_in and s.clock_out:
        clock_in_dt = datetime.combine(s.date, s.clock_in)
        clock_out_dt = datetime.combine(s.date, s.clock_out)
        time_difference = clock_out_dt - clock_in_dt
        t_hours = round(max(0.0, time_difference.total_seconds()) / 3600, 2)
    else:
        t_hours = 0.0

    if current_date is None:
        current_date = get_now().date()

    is_today = (s.date == current_date)

    schedule_eval = None
    if schedules_by_block is not None:
        schedule_eval = evaluate_attendance_status(s, schedules_by_block, settings, current_date=current_date)

    default_status = "Completed" if (s.clock_in and s.clock_out) else ("On Duty" if (s.clock_in and is_today) else "Incomplete")
    default_badge = "success" if (s.clock_in and s.clock_out) else ("info" if (s.clock_in and is_today) else "secondary")

    return {
        "id": s.id,
        "date": s.date.strftime("%b %d, %Y"),
        "raw_date": s.date.strftime("%Y-%m-%d"),
        "is_today": is_today,
        "clock_in": s.clock_in.strftime("%I:%M %p").lower() if s.clock_in else "",
        "clock_out": s.clock_out.strftime("%I:%M %p").lower() if s.clock_out else "",
        "total_hours": t_hours,
        "is_manual": bool(s.is_manual),
        "status": schedule_eval["status"] if schedule_eval else default_status,
        "badge_type": schedule_eval["badge_type"] if schedule_eval else default_badge,
        "status_details": schedule_eval["details"] if schedule_eval else "",
    }


@api_bp.route("/gia-data", methods=["GET"])
@login_required
def gia_data():
    user_id = request.args.get("user_id")

    if current_user.role not in ["superadmin", "admin"] and str(current_user.user_id) != str(user_id):
        return jsonify({"success": False, "error": "Access Denied"}), 403

    month_str = request.args.get("month", "").strip() or get_now().strftime("%Y-%m")
    try:
        parts = month_str.split("-")
        year, month = int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        now = get_now()
        year, month = now.year, now.month

    records = (
        Attendance.query.filter(
            Attendance.user_id == user_id,
            db.extract("year", Attendance.date) == year,
            db.extract("month", Attendance.date) == month,
        )
        .order_by(Attendance.date.desc(), Attendance.id.desc())
        .all()
    )

    current_date = get_now().date()

    # Fetch user schedules and global settings for schedule checking
    user_schedules = Schedule.query.filter_by(user_id=user_id).all()
    schedules_by_block = {s.day.lower(): s for s in user_schedules}
    global_settings = GlobalSettings.get()

    user_records = [serialize_records(r, schedules_by_block, global_settings, current_date=current_date) for r in records]

    sum_hours = 0.0
    today_hours = 0.0
    active_dates = set()

    for record in records:
        t_hours = 0.0
        if record.clock_in and record.clock_out:
            clock_in_dt = datetime.combine(record.date, record.clock_in)
            clock_out_dt = datetime.combine(record.date, record.clock_out)
            time_difference = clock_out_dt - clock_in_dt
            t_hours = round(max(0.0, time_difference.total_seconds()) / 3600, 2)

        sum_hours += t_hours

        if t_hours > 0:
            active_dates.add(record.date)

        if record.date == current_date:
            today_hours += t_hours

    target_hours = 100

    # Query attendance inconsistencies for flags/punctuality
    inconsistencies = (
        AttendanceInconsistency.query.filter(
            AttendanceInconsistency.user_id == user_id,
            db.extract("year", AttendanceInconsistency.date) == year,
            db.extract("month", AttendanceInconsistency.date) == month,
        )
        .order_by(AttendanceInconsistency.date.desc(), AttendanceInconsistency.id.desc())
        .all()
    )

    late_count = sum(1 for inc in inconsistencies if inc.issue_type == "Late")
    early_out_count = sum(1 for inc in inconsistencies if inc.issue_type == "Early Out")
    overtime_count = sum(1 for inc in inconsistencies if inc.issue_type == "Overtime")

    # Group daily hours for bar/trend visualization
    import calendar
    days_in_month = calendar.monthrange(year, month)[1]
    daily_hours_map = {d: 0.0 for d in range(1, days_in_month + 1)}

    for record in records:
        if record.clock_in and record.clock_out:
            clock_in_dt = datetime.combine(record.date, record.clock_in)
            clock_out_dt = datetime.combine(record.date, record.clock_out)
            diff = max(0.0, (clock_out_dt - clock_in_dt).total_seconds()) / 3600
            daily_hours_map[record.date.day] = round(daily_hours_map[record.date.day] + diff, 2)

    daily_trend = [
        {"day": d, "hours": daily_hours_map[d], "label": f"{month:02d}/{d:02d}"}
        for d in range(1, days_in_month + 1)
    ]

    summary = {
        "total_hours": round(sum_hours, 2),
        "target_hours": target_hours,
        "today_hours": round(today_hours, 2),
        "active_days": len(active_dates),
        "flags": {
            "late": late_count,
            "early_out": early_out_count,
            "overtime": overtime_count,
            "total_inconsistencies": len(inconsistencies),
        },
        "inconsistencies": [
            {
                "id": inc.id,
                "date": inc.date.strftime("%b %d, %Y"),
                "issue_type": inc.issue_type,
                "details": inc.details or "",
            }
            for inc in inconsistencies
        ],
        "daily_trend": daily_trend,
    }

    return jsonify({"records": user_records, "summary": summary})


@api_bp.route("/clock-in", methods=["POST"])
@login_required
@ip_whitelist_required
def clock_in():
    data = request.get_json(silent=True)
    if isinstance(data, dict):
        user_id = data.get("user_id") or data.get("userId")
    elif isinstance(data, str):
        user_id = data
    else:
        user_id = current_user.user_id

    if not user_id:
        user_id = current_user.user_id

    if str(current_user.user_id) != str(user_id) and current_user.role not in ["superadmin", "admin"]:
        return jsonify({"success": False, "error": "Access Denied"}), 403

    try:
        now_dt = get_now()
        now_time = now_dt.time()
        today_date = now_dt.date()

        day_name = now_dt.strftime("%A").lower()
        day_short_map = {
            "monday": "mon",
            "tuesday": "tue",
            "wednesday": "wed",
            "thursday": "thu",
            "friday": "fri",
            "saturday": "sat",
        }
        day_map = {
            "monday": "mw",
            "wednesday": "mw",
            "tuesday": "tth",
            "thursday": "tth",
            "friday": "fri",
            "saturday": "sat",
        }
        short_day = day_short_map.get(day_name)
        target_block = day_map.get(day_name)

        user_schedules = []
        if short_day:
            user_schedules = Schedule.query.filter_by(user_id=user_id, day=short_day).all()
        if not user_schedules and target_block:
            user_schedules = Schedule.query.filter_by(user_id=user_id, day=target_block).all()

        global_settings = GlobalSettings.get()

        if not user_schedules and day_name != "sunday":
            return jsonify({"success": False, "error": "You don't have a schedule for today."}), 400

        allowed_early_in = global_settings.allowed_early_in_mins if global_settings else 0
        split_early_in = (
            allowed_early_in // 2
            if any(getattr(s, "is_split_shift", False) for s in user_schedules)
            else allowed_early_in
        )
        special_early_in = split_early_in

        if any(s.start_time == time(7, 30) for s in user_schedules if s.start_time):
            special_early_in += 30

        valid_schedule_start = None
        is_split_shift = False

        if day_name == "sunday":
            valid_schedule_start = global_settings.default_end if global_settings else None
        else:
            for sched in user_schedules:
                if sched.start_time and sched.end_time:
                    earliest_in = (
                        datetime.combine(today_date, sched.start_time) - timedelta(minutes=special_early_in)
                    ).time()
                    if earliest_in <= now_time <= sched.end_time:
                        valid_schedule_start = sched.start_time
                        break

                if getattr(sched, "is_split_shift", False) and sched.split_start_time and sched.split_end_time:
                    earliest_second_in = (
                        datetime.combine(today_date, sched.split_start_time) - timedelta(minutes=split_early_in)
                    ).time()
                    if earliest_second_in <= now_time <= sched.split_end_time:
                        valid_schedule_start = sched.split_start_time
                        is_split_shift = True
                        break

        if global_settings and global_settings.enable_strict_schedule and not valid_schedule_start:
            return jsonify({"success": False, "error": "You're outside your allowed schedule window."}), 400

        active_shifts_today = Attendance.query.filter(
            Attendance.user_id == user_id,
            Attendance.date == today_date,
            Attendance.clock_in.isnot(None),
        ).all()

        if len(active_shifts_today) >= 2:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "You've already reached the daily limit of two clock-ins.",
                    }
                ),
                400,
            )

        # Check if currently already clocked in without clocking out
        already_open = any(s.clock_out is None for s in active_shifts_today)
        if already_open:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "You are already clocked in. Please clock out first.",
                    }
                ),
                400,
            )

        new_entry = Attendance(
            user_id=user_id,
            date=today_date,
            clock_in=now_time,
        )
        db.session.add(new_entry)
        db.session.commit()

        shift_label = "second" if is_split_shift else "first"
        system_log_entry(
            action="Clock In",
            details=f"User {current_user.first_name} {current_user.last_name} clocked in for {shift_label} shift.",
        )

        # Run inconsistency flag check safely
        check_attendance_flags(new_entry)

        return (
            jsonify(
                {
                    "success": True,
                    "message": "Clock-in successful!",
                    "data": {
                        "user_id": user_id,
                        "time_record": new_entry.clock_in.strftime("%I:%M %p"),
                        "date": new_entry.date.strftime("%Y-%m-%d"),
                        "shift": shift_label,
                    },
                }
            ),
            200,
        )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Clock-in Error: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/clock-out", methods=["POST"])
@login_required
@ip_whitelist_required
def clock_out():
    data = request.get_json(silent=True)
    if isinstance(data, dict):
        user_id = data.get("user_id") or data.get("userId")
    elif isinstance(data, str):
        user_id = data
    else:
        user_id = current_user.user_id

    if not user_id:
        user_id = current_user.user_id

    if str(current_user.user_id) != str(user_id) and current_user.role not in ["superadmin", "admin"]:
        return jsonify({"success": False, "error": "Access Denied"}), 403

    try:
        now = get_now()
        actual_clock_out = now.time()
        today = now.date()

        day_name = now.strftime("%A").lower()
        day_short_map = {
            "monday": "mon",
            "tuesday": "tue",
            "wednesday": "wed",
            "thursday": "thu",
            "friday": "fri",
            "saturday": "sat",
        }
        day_map = {
            "monday": "mw",
            "wednesday": "mw",
            "tuesday": "tth",
            "thursday": "tth",
            "friday": "fri",
            "saturday": "sat",
        }
        short_day = day_short_map.get(day_name)
        target_block = day_map.get(day_name)

        last_record = (
            Attendance.query.filter(
                Attendance.user_id == user_id,
                Attendance.clock_in.isnot(None),
                Attendance.clock_out.is_(None),
                Attendance.date == today,
            )
            .order_by(Attendance.clock_in.desc())
            .first()
        )

        if not last_record:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "You can't clock out without clocking in first today.",
                    }
                ),
                400,
            )

        clock_in_time = last_record.clock_in
        global_settings = GlobalSettings.get()
        strict_schedule = bool(global_settings and global_settings.enable_strict_schedule)

        user_schedules = []
        if short_day:
            user_schedules = Schedule.query.filter_by(user_id=user_id, day=short_day).all()
        if not user_schedules and target_block:
            user_schedules = Schedule.query.filter_by(user_id=user_id, day=target_block).all()

        schedule_end = None
        is_split_shift = False

        if strict_schedule:
            if not user_schedules and day_name == "sunday":
                schedule_end = global_settings.default_end if global_settings else None

            for sched in user_schedules:
                if sched.start_time and sched.end_time:
                    early_start = (datetime.combine(today, sched.start_time) - timedelta(hours=1)).time()
                    if early_start <= clock_in_time <= sched.end_time:
                        schedule_end = sched.end_time
                        break

                if getattr(sched, "is_split_shift", False) and sched.split_start_time and sched.split_end_time:
                    early_second_start = (
                        datetime.combine(today, sched.split_start_time) - timedelta(hours=1)
                    ).time()
                    if early_second_start <= clock_in_time <= sched.split_end_time:
                        schedule_end = sched.split_end_time
                        is_split_shift = True
                        break

            if schedule_end:
                actual_clock_out_dt = datetime.combine(today, actual_clock_out)
                schedule_end_dt = datetime.combine(today, schedule_end)

                grace_limit = schedule_end_dt + timedelta(minutes=60)
                if actual_clock_out_dt > grace_limit:
                    return (
                        jsonify(
                            {
                                "success": False,
                                "error": "Exceeded the 60-minute grace period after your shift.",
                            }
                        ),
                        400,
                    )

                evening_cutoff = datetime.combine(today, time(18, 30))
                if schedule_end_dt < actual_clock_out_dt < evening_cutoff:
                    last_record.clock_out = schedule_end
                else:
                    last_record.clock_out = actual_clock_out
            else:
                last_record.clock_out = actual_clock_out
        else:
            last_record.clock_out = actual_clock_out

        db.session.commit()

        system_log_entry(
            action="Clock Out",
            details=f"User {current_user.first_name} {current_user.last_name} clocked out.",
        )

        # Run inconsistency flag check safely
        check_attendance_flags(last_record)

        return (
            jsonify(
                {
                    "success": True,
                    "message": "Clock-out successful!",
                    "data": {
                        "user_id": user_id,
                        "time_record": last_record.clock_out.strftime("%I:%M %p"),
                        "date": last_record.date.strftime("%Y-%m-%d"),
                        "shift": "second" if is_split_shift else "first",
                    },
                }
            ),
            200,
        )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Clock-out Error: {traceback.format_exc()}")
        return jsonify({"success": False, "error": f"An error occurred: {e!s}"}), 500
