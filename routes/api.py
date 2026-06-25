from flask import Blueprint, request, flash, send_file, jsonify
from flask_login import login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
import io, traceback
import re
import pandas as pd
from datetime import datetime, date, timedelta, time
from sqlalchemy import func, or_
from models.models import db, User, Attendance, Schedule, GlobalSettings, Logs
from routes.gia import WHITELIST, SPECIAL_IDS, get_client_ip
# from flask_apscheduler import APScheduler

# Create a Blueprint for admin routes
api_bp = Blueprint('api', __name__)

# System Log
def systemLogEntry(action, details):
    try:
        entry = Logs(
            action=action,
            details=details,
            user_id=getattr(current_user, 'user_id', None),
            timestamp=datetime.now(),
            client_ip=get_client_ip()

        )
        db.session.add(entry)
        db.session.commit()
    except Exception as e:
        db.session.rollback()


def normalize_philippine_phone(phone):
    if not phone:
        return ''

    digits = re.sub(r"\D+", "", str(phone))
    digits = re.sub(r"^00", "", digits)

    if digits == '63':
        return ''

    if digits.startswith('63'):
        pass
    elif digits.startswith('0'):
        digits = '63' + digits[1:]
    else:
        digits = '63' + digits

    return '' if digits == '63' else digits


def format_philippine_phone(phone):
    digits = normalize_philippine_phone(phone)
    if not digits:
        return ''

    rest = digits[2:]
    if len(rest) == 10:
        return f"+63 {rest[:3]} {rest[3:6]} {rest[6:]}"
    if len(rest) == 9:
        return f"+63 {rest[:1]} {rest[1:5]} {rest[5:]}"
    if len(rest) == 8:
        return f"+63 {rest[:3]} {rest[3:]}"
    if len(rest) == 7:
        return f"+63 {rest[:3]} {rest[3:]}"
    return f"+{digits}"


# GET ALL USER
@api_bp.route('/users-data', methods=['GET'])
@login_required
def get_data():
    if current_user.role not in ["superadmin", "admin"]:
        return jsonify({'success': False, 'error': 'Access Denied'}), 400

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    search = request.args.get('search', '', type=str).strip()
    status = request.args.get('status', '', type=str).strip()
    role = request.args.get('role', '', type=str).strip()

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
            User.laboratory.ilike(search_pattern)
        ]
        if phone_digits:
            filters.append(User.phone_number.ilike(f"%{phone_digits}%"))
            if phone_digits.startswith('0'):
                local_digits = phone_digits[1:]
                filters.append(User.phone_number.ilike(f"%63{local_digits}%"))
            elif phone_digits.startswith('63'):
                filters.append(User.phone_number.ilike(f"%{phone_digits[2:]}%"))
        query = query.filter(or_(*filters))

    total = query.count()
    users = query.order_by(User.role, User.first_name).offset((page - 1) * per_page).limit(per_page).all()

    users_list = []
    for user in users:
        users_list.append({
            'user_id': user.user_id,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'middle_name': user.middle_name,
            'role': user.role,
            'status': user.status,
            'phone_number': user.phone_number or '',
            'laboratory': user.laboratory or ''
        })

    return jsonify({'success': True, 'users': users_list, 'total': total, 'page': page, 'per_page': per_page})

# ADD NEW USER
@api_bp.route('/add-user', methods=['POST'])
@login_required
def add_user():
    if current_user.role not in ["superadmin", "admin"]:
        flash("Access Denied!", "danger")
        return jsonify({'success': False, 'error': 'Access Denied'}), 400

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Invalid or missing JSON data'}), 400

    user_id = data.get('userId')
    first_name = data.get('firstName')
    last_name = data.get('lastName')
    middle_initial = data.get('middleInitial')
    role = data.get('role')
    phone_number = format_philippine_phone(data.get('phoneNumber'))
    laboratory = data.get('laboratory')

    # Check if user already exists
    if User.query.filter_by(user_id=user_id).first():
        return jsonify({'success': False, 'error': 'User ID already exists'}), 400

    # Create and save new user
    new_user = User(
        user_id=user_id,
        first_name=first_name,
        last_name=last_name,
        phone_number=phone_number,
        laboratory=laboratory,
        middle_name=middle_initial.upper() if middle_initial else None,
        role=role,
        password=generate_password_hash('admin123')
    )
    db.session.add(new_user)
    db.session.commit()

    systemLogEntry(
        action="Created",
        details=f"User '{new_user.first_name} {new_user.last_name}' (ID: {new_user.user_id}) was created by {current_user.first_name} {current_user.last_name}."
    )
    
    return jsonify({
        'success': True,
    }), 200

# GET USER DETAILS
@api_bp.route('/get-user/<string:user_id>', methods=['GET'])
@login_required
def get_user(user_id):
    if current_user.role not in ["superadmin", "admin"]:
        flash("Access Denied!", "danger")
        return jsonify({'success': False, 'error': 'Access Denied'}), 400
    
    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    user_data = {
        'user_id': user.user_id,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'middle_name': user.middle_name[0] if user.middle_name else '',
        'role': user.role,
        'status': user.status,
        'phone_number': user.phone_number or '',
        'laboratory': user.laboratory or ''
    }

    return jsonify(user_data)

# UPDATE USER DETAILS
@api_bp.route('/update-user/<string:user_id>', methods=['POST'])
@login_required
def update_user(user_id):
    if current_user.role not in ["superadmin", "admin"]:
        flash("Access Denied!", "danger")
        return jsonify({'success': False, 'error': 'Access Denied'}), 400

    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Invalid or missing JSON data'}), 400

    # Update user fields
    user.user_id = data.get('userId', user.user_id)
    user.first_name = data.get('firstName', user.first_name)
    user.last_name = data.get('lastName', user.last_name)
    middle_initial = data.get('middleInitial')
    if middle_initial is not None:
        user.middle_name = middle_initial.upper()
    user.phone_number = format_philippine_phone(data.get('phoneNumber')) or user.phone_number
    user.laboratory = data.get('laboratory', user.laboratory)
    user.role = data.get('role', user.role)
    user.status = data.get('status', user.status)

    try:
        db.session.commit()

        systemLogEntry(
            action="Updated",
            details=f"#{user.id} User '{user.first_name} {user.last_name}' (ID: {user.user_id}) was updated by {current_user.first_name} {current_user.last_name}."
        )

        return jsonify({'success': True, 'message': 'User updated successfully!'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f"Error updating user: {str(e)}"}), 500

# DELETE USER
@api_bp.route('/delete-user/<string:user_id>', methods=['POST'])
@login_required
def delete_user_page(user_id):
    if current_user.role not in ["superadmin", "admin"]:
        flash("Access Denied!", "danger")
        return jsonify({'success': False, 'error': 'Access Denied'}), 400
    
    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404

    try:
        # Delete related attendance records
        Attendance.query.filter_by(user_id=user.user_id).delete()

        systemLogEntry(
            action="Deleted",
            details=f"User '{user.first_name} {user.last_name}' (ID: {user.user_id}) was deleted by {current_user.first_name} {current_user.last_name}."
        )

        # Delete the user
        db.session.delete(user)
        db.session.commit()

        return jsonify({'success': True, 'message': 'User deleted successfully!'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f"Error deleting user: {str(e)}"}), 500

# EXPORT USERS
@api_bp.route('/export-users', methods=['GET'])
@login_required
def export_users():
    if current_user.role not in ["superadmin", "admin"]:
        flash("Access Denied!", "danger")
        return jsonify({'success': False, 'error': 'Access Denied'}), 400

    # Fetch and sort users (active only)
    users = sorted(
        User.query.filter(User.role == "gia", User.status == "active").all(),
        key=lambda x: (x.last_name, x.first_name)
    )

    # Prepare user data
    data = {
        'User ID': [user.user_id for user in users],
        'Last Name': [user.last_name for user in users],
        'First Name': [user.first_name for user in users],
        'Middle Initial': [user.middle_name[0].upper() if user.middle_name else '' for user in users],
        'Phone Number': [user.phone_number for user in users],
        'Laboratory': [user.laboratory for user in users]
    }

    df = pd.DataFrame(data)

    # Convert to CSV
    csv_data = df.to_csv(index=False)
    output = io.BytesIO()
    output.write(csv_data.encode('utf-8'))
    output.seek(0)

    # Filename with timestamp
    filename = f'GIA List {datetime.now().strftime("%m-%d-%Y")}.csv'

    return send_file(output, mimetype='text/csv', as_attachment=True, download_name=filename)

# Time to String
def serialize_schedule(s):
    return {
        'user_id': s.user_id,
        'day': s.day,
        'start_time': s.start_time.strftime("%I:%M %p") if s.start_time else '',
        'end_time': s.end_time.strftime("%I:%M %p") if s.end_time else '',
        'split_start_time': s.split_start_time.strftime("%I:%M %p") if s.split_start_time else '',
        'split_end_time': s.split_end_time.strftime("%I:%M %p") if s.split_end_time else ''
    }

@api_bp.route('/get-schedules', methods=['GET'])
@login_required
def get_schedules():
    if current_user.role not in ["superadmin", "admin"]:
        return jsonify({'success': False, 'error': 'Access Denied'}), 403
    
    users = User.query.filter(
        User.role != "superadmin", 
        User.role != "admin", 
        User.status == "active"
    ).order_by(User.first_name).all()

    # Only get schedules that fit the new block format
    schedules = Schedule.query.filter(Schedule.day.in_(['mw', 'tth', 'fri', 'sat'])).all()
    
    sched_list = [serialize_schedule(s) for s in schedules]
    users_list = []

    for user in users:
        users_list.append({
            'user_id': user.user_id,
            'first_name': user.first_name,
            'last_name': user.last_name,
            # Add any other specific fields you need for the table
        })

    return jsonify({
        'schedules': sched_list,
        'users': users_list
    })

@api_bp.route('/get-schedule/<string:user_id>', methods=['GET'])
@login_required
def get_user_schedule(user_id):
    if current_user.role not in ["superadmin", "admin"] and current_user.user_id != user_id:
            return jsonify({'success': False, 'error': 'Access Denied'}), 403

    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404

    schedule = Schedule.query.filter_by(user_id=user_id).all()

    user_data = {
        'user_id': user.user_id,
        'full_name': f"{user.first_name} {user.last_name}",
    }

    user_schedules = [
        {
            'id': s.id,
            'day': s.day,
            'start_time': s.start_time.strftime('%H:%M') if s.start_time else None,
            'end_time': s.end_time.strftime('%H:%M') if s.end_time else None,
            'is_split_shift': s.is_split_shift,
            'split_start_time': s.split_start_time.strftime('%H:%M') if s.split_start_time else None,
            'split_end_time': s.split_end_time.strftime('%H:%M') if s.split_end_time else None,
        }
        for s in schedule
    ]

    return jsonify({
        'user': user_data,
        'schedules': user_schedules,
        'success': True
    })


def parse_time(value):
    """Convert 'HH:MM' string to Python time object or None."""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%H:%M").time()
    except ValueError:
        return None

# UPDATE SCHEDULE
@api_bp.route('/update-schedule/<string:user_id>', methods=['POST'])
@login_required
def update_schedule(user_id):
    if current_user.role not in ["superadmin", "admin"]:
        return jsonify({'success': False, 'error': 'Access Denied'}), 403

    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404

    data = request.get_json(silent=True)
    if not data:
        return jsonify({'success': False, 'error': 'Invalid or missing JSON data'}), 400

    schedules = data.get('schedules', [])
    brokenScheds = data.get('brokenSched', [])

    try:
        # Updated to loop through the new schedule blocks instead of every single day
        for day in ['mw', 'tth', 'fri', 'sat']:
            match = next((s for s in schedules if s.get('day') == day), None)
            brokenMatch = next((b for b in brokenScheds if b.get('day') == day), None)

            # Parse times safely (may be None)
            start_time = parse_time(match.get('start_time')) if match else None
            end_time = parse_time(match.get('end_time')) if match else None
            split_start_time = parse_time(brokenMatch.get('split_start_time')) if brokenMatch else None
            split_end_time = parse_time(brokenMatch.get('split_end_time')) if brokenMatch else None

            # Determine split flag
            isBroken = bool(split_start_time and split_end_time)

            sched = Schedule.query.filter_by(user_id=user_id, day=day).first()

            if sched:
                # Update existing record
                sched.start_time = start_time
                sched.end_time = end_time
                sched.split_start_time = split_start_time
                sched.split_end_time = split_end_time
                sched.is_split_shift = isBroken
            elif match or brokenMatch:
                # Only create new if there’s relevant data
                new_sched = Schedule(
                    user_id=user_id,
                    day=day,
                    start_time=start_time,
                    end_time=end_time,
                    split_start_time=split_start_time,
                    split_end_time=split_end_time,
                    is_split_shift=isBroken
                )
                db.session.add(new_sched)

        db.session.commit()

        systemLogEntry(
            action="Updated",
            details=f"Schedule for user '{user.first_name} {user.last_name}' (ID: {user.user_id}) was updated by {current_user.first_name} {current_user.last_name}."
        )

        return jsonify({'success': True, 'message': 'Schedule updated successfully!'})

    except Exception as e:
        db.session.rollback()
        print("Error updating schedule:", e)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/purge-schedules', methods=['POST'])
@login_required
def purge_schedules():
    if current_user.role not in ["superadmin", "admin"]:
        return jsonify({'success': False, 'error': 'Access Denied'}), 403
    
    try:
        db.session.query(Schedule).update({
            Schedule.start_time: None,
            Schedule.end_time: None,
            Schedule.is_split_shift: None,
            Schedule.split_start_time: None,
            Schedule.split_end_time: None
        })
        db.session.commit()

        systemLogEntry(
            action="Deleted",
            details=f"All schedules were purged by {current_user.first_name} {current_user.last_name}."
        )

        return jsonify({'success': True, 'message': 'All schedules cleared successfully!'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f"Error clearing schedules: {str(e)}"}), 500

def serialize_logs(l):
    role = None
    if (l.user.role == "admin"):
        role = "Admin"
    else:
        role = 'GIA'

    return {
        'date': l.timestamp.strftime("%b %d, %Y"),
        'time': l.timestamp.strftime("%I:%M %p"),
        'full_name': f"{l.user.first_name} {l.user.last_name}",
        'role': role,
        'action': l.action,
        'details': l.details,
        'ip': l.client_ip
    }

@api_bp.route('/get-logs')
@login_required
def get_logs():
    if current_user.role not in ["superadmin", "admin"]:
        return jsonify({'success': False, 'error': 'Access Denied'}), 403

    from_date = request.args.get("from")
    to_date = request.args.get("to")
    user_filter = request.args.get("user", "", type=str)
    action_filter = request.args.get("action", "", type=str)
    search_term = request.args.get("search", "", type=str)
    page = request.args.get("page", 1, type=int)       # current page
    per_page = request.args.get("per_page", 20, type=int)  # items per page

    from_date_obj = datetime.strptime(from_date, "%Y-%m-%d")
    to_date_obj = datetime.strptime(to_date, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)

    query = Logs.query.outerjoin(User).filter(
        Logs.user_id != 'superadmin',
        Logs.timestamp >= from_date_obj,
        Logs.timestamp <= to_date_obj
    )

    if user_filter:
        user_term = user_filter.strip().lower()
        query = query.filter(or_(
            func.lower(User.first_name).contains(user_term),
            func.lower(User.last_name).contains(user_term),
            func.lower(User.role).contains(user_term)
        ))

    if action_filter:
        query = query.filter(func.lower(Logs.action) == action_filter.strip().lower())

    if search_term:
        search_value = f"%{search_term.strip().lower()}%"
        query = query.filter(or_(
            func.lower(Logs.action).contains(search_term.strip().lower()),
            func.lower(Logs.details).contains(search_term.strip().lower()),
            func.lower(User.first_name).contains(search_term.strip().lower()),
            func.lower(User.last_name).contains(search_term.strip().lower()),
            func.lower(User.role).contains(search_term.strip().lower())
        ))

    pagination = query.order_by(Logs.id.desc()).paginate(page=page, per_page=per_page, error_out=False)

    logs_list = [serialize_logs(l) for l in pagination.items]

    return jsonify({
        "logs": logs_list,
        "page": pagination.page,
        "pages": pagination.pages,
        "total": pagination.total,
        "per_page": pagination.per_page
    })

def serialize_drecords(s):
    if s.clock_in and s.clock_out:
        clock_in_dt = datetime.combine(date.today(), s.clock_in)
        clock_out_dt = datetime.combine(date.today(), s.clock_out)
        time_difference = clock_out_dt - clock_in_dt
        t_hours = round(time_difference.total_seconds() / 3600, 2)
    else:
        t_hours = 0

    return {
        'name_initial': f"{s.user.first_name[0]}{s.user.last_name[0]}",
        'full_name': f"{s.user.first_name} {s.user.last_name}",
        'user_id': s.user.user_id,
        'log_id': s.id,
        'date': s.date.strftime("%Y-%m-%d"),
        'clock_in': s.clock_in.strftime("%I:%M %p").lower() if s.clock_in else '',
        'clock_out': s.clock_out.strftime("%I:%M %p").lower() if s.clock_out else '',
        'total_hours': t_hours,
    }

@api_bp.route('/get-daily-logs')
@login_required
def get_daily_logs():
    if current_user.role not in ["superadmin", "admin"]:
        return jsonify({'success': False, 'error': 'Access Denied'}), 403
    
    today = request.args.get('today')

    records = Attendance.query.join(User).filter(
        Attendance.date == today,
        User.status == "active"
    ).order_by(Attendance.id.desc()).all()
    records_list = [serialize_drecords(s) for s in records]

    return jsonify(records_list)

@api_bp.route('/get-user-log/<string:log_id>')
@login_required
def get_user_log(log_id):
    
    if current_user.role not in ["superadmin", "admin"]:
        return jsonify({'success': False, 'error': 'Access Denied'}), 403
    
    record = Attendance.query.get(log_id)
    user_record = {
        'log_id': record.id,
        'full_name': f"{record.user.first_name} {record.user.last_name}",
        'clock_in': record.clock_in.strftime("%H:%M") if record.clock_in else '',
        'clock_out': record.clock_out.strftime("%H:%M") if record.clock_out else '',
        # 'notes': record.notes if record.notes else '',
    }

    return jsonify(user_record)

@api_bp.route('/update-log/<string:log_id>', methods=['POST'])
@login_required
def update_log(log_id):
    if current_user.role not in ["superadmin", "admin"]:
        return jsonify({'success': False, 'error': 'Access Denied'}), 403
    
    data = request.get_json()
    log = Attendance.query.get(log_id)
    
    log.clock_in = data.get('clockIn', log.clock_in)
    log.clock_out = data.get('clockOut', log.clock_out)

    try:
        db.session.commit()

        systemLogEntry(
            action="Updated",
            details=f"#{log.id} Attendance record updated for {log.user.first_name} {log.user.last_name}."
        )

        return jsonify({'success': True, 'message': 'Log updated successfully!'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f"Error updating log: {str(e)}"}), 500

@api_bp.route('/add-log', methods=['POST'])
def add_log():
    if current_user.role not in ["superadmin", "admin"]:
        return jsonify({'success': False, 'error': 'Access Denied'}), 403
    
    data = request.get_json()

    user_id = data.get('userId')
    user = User.query.filter_by(user_id=user_id).first()

    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404

    new_log = Attendance(
        user_id = user_id,
        date = data.get('date'),
        clock_in = data.get('clockIn'),
        clock_out = data.get('clockOut'),
        is_manual = True 
    )

    try:
        db.session.add(new_log)

        systemLogEntry(
            action="Created",
            details=f"New attendance record added for {user.first_name} {user.last_name}."
        )

        return jsonify({'success': True, 'message': 'Log updated successfully!'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f"Error updating log: {str(e)}"}), 500
    
@api_bp.route('/get-settings', methods=['GET'])
def get_settings():
    s = GlobalSettings.query.first()
    
    settings = {
        'unit_head': s.unit_head,
        'strict': s.enable_strict_schedule,
        'strict_duration': s.strict_duration.strftime("%Y-%m-%d") if s.strict_duration else None,
        'early': s.allow_early_out,
        'overtime': s.allow_overtime,
        'def_start': s.default_start.strftime("%H:%M"),
        'def_end': s.default_end.strftime("%H:%M"),
        'early_allowance': s.allowed_early_in_mins
    }
    
    try:
        return jsonify(settings)
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f"Error updating log: {str(e)}"}), 500

@api_bp.route('/update-settings', methods=['POST'])
def update_settings():
    if current_user.role not in ["superadmin", "admin"]:
        return jsonify({'success': False, 'error': 'Access Denied'}), 403
    
    data = request.get_json()
    settings = GlobalSettings.query.first()

    old_values = {
        "unit_head": settings.unit_head,
        "enable_strict_schedule": settings.enable_strict_schedule,
        "strict_duration": settings.strict_duration,
        "allowed_early_in_mins": settings.allowed_early_in_mins,
        "allow_early_out": settings.allow_early_out,
        "allow_overtime": settings.allow_overtime,
        "default_start": settings.default_start.strftime("%H:%M") if settings.default_start else None,
        "default_end": settings.default_end.strftime("%H:%M")
    }

    settings.unit_head = data.get('unitHeadName')
    settings.enable_strict_schedule = data.get('enableStrictMode')
    settings.allowed_early_in_mins = int(data.get('earlyInMinutes'))
    settings.allow_early_out = data.get('allowEarlyOut')
    settings.allow_overtime = data.get('allowOvertime')
    settings.default_start = data.get('defaultStartTime')
    settings.default_end = data.get('defaultEndTime')

    if not data.get('enableStrictMode'):
        settings.strict_duration = data.get('strictDuration') or None

    # detect changed fields only
    changes = []
    for key, old_value in old_values.items():
        new_value = getattr(settings, key)
        if old_value != new_value:
            changes.append(f"{key}: {old_value} → {new_value}")

    try:
        db.session.commit()

        if changes:
            systemLogEntry(
                action="Updated",
                details="; ".join(changes)
            )

        return jsonify({'success': True, 'message': 'Settings updated successfully!'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f"Error updating settings: {str(e)}"}), 500

@api_bp.route('/update-profile', methods=['POST'])
@login_required
def update_profile():
    data = request.get_json()

    # update fields
    current_user.first_name = data.get('firstName')
    current_user.last_name = data.get('lastName')
    current_user.middle_name = data.get('middleName')

    try:
        db.session.commit()

        systemLogEntry(
            action="Updated",
            details=f"User {current_user.user_id} updated their profile"
        )

        return jsonify({
            'success': True,
            'updated': {
                'firstName': current_user.first_name,
                'lastName': current_user.last_name,
                'middleName': current_user.middle_name
            }
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': 'Database error occurred'}), 500

@api_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    data = request.get_json()

    current_password = data.get('currentPassword')
    new_password = data.get('newPassword')
    confirm_password = data.get('confirmPassword')

    if not current_password or not new_password or not confirm_password:
        return jsonify({'success': False, 'error': 'All fields are required'}), 400

    if new_password != confirm_password:
        return jsonify({'success': False, 'error': 'Passwords do not match'}), 400

    # verify old password
    if not check_password_hash(current_user.password, current_password):
        return jsonify({'success': False, 'error': 'Current password is incorrect'}), 400

    # update password
    current_user.password = generate_password_hash(new_password)

    try:
        db.session.commit()

        # Optional logging
        systemLogEntry(
            action="Password Changed",
            details=f"User {current_user.user_id} updated their password"
        )

        return jsonify({'success': True}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Database error occurred: {str(e)}'}), 500


#    █████████  █████   █████████        █████████   ███████████  █████
#   ███░░░░░███░░███   ███░░░░░███      ███░░░░░███ ░░███░░░░░███░░███ 
#  ███     ░░░  ░███  ░███    ░███     ░███    ░███  ░███    ░███ ░███ 
# ░███          ░███  ░███████████     ░███████████  ░██████████  ░███ 
# ░███    █████ ░███  ░███░░░░░███     ░███░░░░░███  ░███░░░░░░   ░███ 
# ░░███  ░░███  ░███  ░███    ░███     ░███    ░███  ░███         ░███ 
#  ░░█████████  █████ █████   █████    █████   █████ █████        █████
#   ░░░░░░░░░  ░░░░░ ░░░░░   ░░░░░    ░░░░░   ░░░░░ ░░░░░        ░░░░░ 


@api_bp.route('/status', methods=['GET'])
@login_required
def status():
    user_id = request.args.get('user_id')

    if not user_id:
        return jsonify({'error': 'Missing user_id'}), 400

    if current_user.user_id != user_id:
        return jsonify({'success': False, 'error': 'Access Denied'}), 403 # Changed to 403

    today = date.today()
    
    # 1. Map actual day name to your block identifiers
    day_name = datetime.today().strftime('%A').lower()
    day_map = {
            'monday': 'mw', 'wednesday': 'mw', 
            'tuesday': 'tth', 'thursday': 'tth',
            'friday': 'fri', 'saturday': 'sat'
        }
    target_block = day_map.get(day_name) # Will be None on Sundays

    # 2. Get latest attendance for today
    last_record = Attendance.query.filter(
        Attendance.user_id == user_id,
        Attendance.date == today
    ).order_by(Attendance.id.desc()).first()

    # 3. Get today's schedule using the target_block
    user_schedules = []
    if target_block:
        user_schedules = Schedule.query.filter_by(
            user_id=user_id,
            day=target_block
        ).all()

    # Check global settings for strict schedule enforcement
    global_settings = GlobalSettings.query.first()
    strict_schedule = bool(global_settings and global_settings.enable_strict_schedule)

    schedule_end = None
    is_grace = False

    # No record = not clocked in yet
    if not last_record or not last_record.clock_in:
        return jsonify({
            'clocked_in': False,
            'clocked_out': False,
            'is_grace': False
        }), 200

    clock_in_time = last_record.clock_in

    # Determine applicable shift end time
    for sched in user_schedules:
        # Check first shift
        if sched.start_time and sched.end_time:
            # Lookback 1 hour before start to 1 second before end
            early_start = (datetime.combine(today, sched.start_time) - timedelta(hours=1)).time()
            if early_start <= clock_in_time <= sched.end_time:
                schedule_end = sched.end_time
                break

        # Check second shift (split schedule)
        if sched.is_split_shift and sched.split_start_time and sched.split_end_time:
            early_second_start = (datetime.combine(today, sched.split_start_time) - timedelta(hours=1)).time()
            if early_second_start <= clock_in_time <= sched.split_end_time:
                schedule_end = sched.split_end_time
                break

    # 4. Check if user exceeded the 60-min grace period (based on your logic)
    if strict_schedule and schedule_end:
        now = datetime.now()
        # grace_limit is shift end + 60 mins
        grace_limit = datetime.combine(today, schedule_end) + timedelta(minutes=60)
        if now > grace_limit:
            is_grace = True

    # Response
    return jsonify({
        'clocked_in': bool(last_record.clock_in and not last_record.clock_out),
        'clocked_out': bool(last_record.clock_out),
        'is_grace': is_grace
    }), 200

def serialize_records(s):
    if s.clock_in and s.clock_out:
        clock_in_dt = datetime.combine(date.today(), s.clock_in)
        clock_out_dt = datetime.combine(date.today(), s.clock_out)
        time_difference = clock_out_dt - clock_in_dt
        t_hours = round(time_difference.total_seconds() / 3600, 2)
    else:
        t_hours = 0

    return {
        'date': s.date.strftime("%b %d, %Y"),
        'clock_in': s.clock_in.strftime("%I:%M %p").lower() if s.clock_in else '',
        'clock_out': s.clock_out.strftime("%I:%M %p").lower() if s.clock_out else '',
        'total_hours': t_hours,
    }

@api_bp.route('/gia-data', methods=['GET'])
@login_required
def gia_data():
    user_id = request.args.get('user_id')

    # Ensure type matching for the comparison just in case user_id from args is a string
    if str(current_user.user_id) != str(user_id):
        return jsonify({'success': False, 'error': 'Access Denied'}), 400
    
    month = request.args.get('month')
    year, month = map(int, month.split('-'))

    records = Attendance.query.filter(
        Attendance.user_id == user_id,
        db.extract('year', Attendance.date) == year,
        db.extract('month', Attendance.date) == month,
    ).order_by(Attendance.date.desc(), Attendance.id.desc()).all()
    
    user_records = [serialize_records(r) for r in records]

    sum_hours = 0.0
    today_hours = 0.0
    active_dates = set() # Using a set to easily count unique days worked
    
    current_date = date.today()

    for record in records:
        t_hours = 0.0
        if record.clock_in and record.clock_out:
            # Better to use record.date rather than date.today() for historical accuracy
            clock_in_dt = datetime.combine(record.date, record.clock_in)
            clock_out_dt = datetime.combine(record.date, record.clock_out)
            time_difference = clock_out_dt - clock_in_dt
            t_hours = round(time_difference.total_seconds() / 3600, 2)
        
        sum_hours += t_hours

        # Count as an active day if they actually rendered time
        if t_hours > 0:
            active_dates.add(record.date)

        # Calculate progress for the current day
        if record.date == current_date:
            today_hours += t_hours

    # If you eventually add a 'target_hours' column to your User model, 
    # you can replace the hardcoded 60 with: getattr(current_user, 'target_hours', 60)
    target_hours = 100

    summary = {
        'total_hours': round(sum_hours, 2),
        'target_hours': target_hours,
        'today_hours': round(today_hours, 2),
        'active_days': len(active_dates)
    }

    return jsonify({
        'records': user_records,
        'summary': summary
    })

# Whitelist verification
def ip_whitelist():
    if current_user.is_authenticated and current_user.user_id not in SPECIAL_IDS:
        client_ip = get_client_ip()
        if client_ip not in WHITELIST:
            return({'success': False, 'error': 'Access denied. Your device isn’t allowed to use this feature.'}), 400
        
    return None

@api_bp.route('/clock-in', methods=['POST'])
@login_required
def clock_in():
    # Safely get user_id from JSON
    data = request.get_json()
    user_id = data if isinstance(data, str) else data.get('user_id')

    if current_user.user_id != user_id:
        return jsonify({'success': False, 'error': 'Access Denied'}), 403
    
    check = ip_whitelist()
    if check:
        return check
        
    try:
        now_dt = datetime.now()
        now_time = now_dt.time()
        today_date = now_dt.date()
        
        # 1. Map actual day to our new blocks
        day_name = now_dt.strftime('%A').lower()
        day_map = {
            'monday': 'mw', 'wednesday': 'mw', 
            'tuesday': 'tth', 'thursday': 'tth',
            'friday': 'fri', 'saturday': 'sat'
        }
        target_block = day_map.get(day_name) # Sunday returns None

        # 2. Get Schedules and Global Settings 
        user_schedules = []
        if target_block:
            user_schedules = Schedule.query.filter_by(user_id=user_id, day=target_block).all()
        
        global_settings = GlobalSettings.query.first()

        # # 3. Apply default schedule if no personal one exists (and it's not Sunday)
        # if not user_schedules and target_block and global_settings and global_settings.default_start and global_settings.default_end:
        #     user_schedules = [Schedule(
        #         user_id=user_id,
        #         day=target_block,
        #         start_time=global_settings.default_start,
        #         end_time=global_settings.default_end
        #     )]

        # No schedule check
        if not user_schedules and day_name != "sunday":
            return jsonify({'success': False, 'error': 'You don’t have a schedule for today.'}), 400

        # 4. Early-in Rules 
        allowed_early_in = global_settings.allowed_early_in_mins if global_settings else 0
        special_early_in = allowed_early_in

        # Add special 30min early-in for 7:30 AM shifts on weekday blocks (mw/tth/fri)
        if target_block in ["mw", "tth", "fri", "sat"]:
            if any(s.start_time == time(7, 30) for s in user_schedules):
                special_early_in += 30

        # 5. Determine Valid Schedule 
        valid_schedule_start = None
        is_split_shift = False

        if day_name == "sunday":
            valid_schedule_start = global_settings.default_end if global_settings else None

        else:
            for sched in user_schedules:
                # First Shift Check
                if sched.start_time and sched.end_time:
                    earliest_in = (datetime.combine(today_date, sched.start_time) - timedelta(minutes=special_early_in)).time()
                    if earliest_in <= now_time <= sched.end_time:
                        valid_schedule_start = sched.start_time
                        break

                # Second Shift Check (Split)
                if getattr(sched, 'is_split_shift', False) and sched.split_start_time and sched.split_end_time:
                    earliest_second_in = (datetime.combine(today_date, sched.split_start_time) - timedelta(minutes=allowed_early_in)).time()
                    if earliest_second_in <= now_time <= sched.split_end_time:
                        valid_schedule_start = sched.split_start_time
                        is_split_shift = True
                        break

        # 6. Enforce strict schedule
        if global_settings and global_settings.enable_strict_schedule and not valid_schedule_start:
            # Special bypass logic for weekends if allowed in your workflow, otherwise:
            return jsonify({'success': False, 'error': 'You\'re outside your allowed schedule window.'}), 400

        # 7. Check Attendance Rules 
        active_shifts_today = Attendance.query.filter(
            Attendance.user_id == user_id,
            Attendance.date == today_date,
            Attendance.clock_in.is_not(None)
        ).all()

        # Limit to 2 clock-ins per day
        if len(active_shifts_today) >= 2:
            return jsonify({'success': False, 'error': 'You’ve already reached the daily limit of two clock-ins.'}), 400

        # 8. Create and Save Attendance Entry 
        new_entry = Attendance(
            user_id=user_id,
            date=today_date,
            clock_in=now_time
        )
        db.session.add(new_entry)
        db.session.commit()

        systemLogEntry(
            action="Clock In",
            details=f"User {current_user.first_name} {current_user.last_name} clocked in for {'second' if is_split_shift else 'first'} shift."
        )

        return jsonify({
            'success': True,
            'message': 'Clock-in successful!',
            'data': {
                'user_id': user_id,
                'time_record': new_entry.clock_in.strftime("%I:%M %p"),
                'date': new_entry.date.strftime("%Y-%m-%d"),
                'shift': 'second' if is_split_shift else 'first'
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Clock-in Error: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
@api_bp.route('/clock-out', methods=['POST'])
@login_required
def clock_out():
    # Safely handle JSON data
    data = request.get_json()
    user_id = data if isinstance(data, str) else data.get('user_id')

    if not user_id:
        return jsonify({'success': False, 'error': 'Missing user_id'}), 400
    if current_user.user_id != user_id:
        return jsonify({'success': False, 'error': 'Access Denied'}), 403
    
    check = ip_whitelist()
    if check:
        return check
    
    try:
        now = datetime.now()
        actual_clock_out = now.time()
        today = now.date()
        
        # 1. Map current day to the schedule blocks
        day_name = now.strftime('%A').lower()
        day_map = {
            'monday': 'mw', 'wednesday': 'mw', 
            'tuesday': 'tth', 'thursday': 'tth',
            'friday': 'fri', 'saturday': 'sat'
        }
        target_block = day_map.get(day_name)

        # 2. Find the active record (Clocked in today, but not yet clocked out)
        last_record = Attendance.query.filter(
            Attendance.user_id == user_id,
            Attendance.clock_in.isnot(None),
            Attendance.clock_out.is_(None),
            Attendance.date == today,
        ).order_by(Attendance.clock_in.desc()).first()

        if not last_record:
            return jsonify({'success': False, 'error': 'You can’t clock out without clocking in first today.'}), 400
        
        clock_in_time = last_record.clock_in 

        # 3. Get Schedules and Enforcement Rules
        global_settings = GlobalSettings.query.first()
        strict_schedule = bool(global_settings and global_settings.enable_strict_schedule)
        
        user_schedules = []
        if target_block:
            user_schedules = Schedule.query.filter_by(user_id=user_id, day=target_block).all()

        schedule_end = None
        is_split_shift = False

        # 4. Determine which shift the user is currently finishing
        if strict_schedule:
            # If no personal schedule exists, check for weekend default bypass
            if not user_schedules and day_name in ["sunday"]:
                schedule_end = global_settings.default_end if global_settings else None
            
            for sched in user_schedules:
                # Check regular shift window
                if sched.start_time and sched.end_time:
                    early_start = (datetime.combine(today, sched.start_time) - timedelta(hours=1)).time()
                    if early_start <= clock_in_time <= sched.end_time:
                        schedule_end = sched.end_time
                        break

                # Check split shift window
                if getattr(sched, 'is_split_shift', False) and sched.split_start_time and sched.split_end_time:
                    early_second_start = (datetime.combine(today, sched.split_start_time) - timedelta(hours=1)).time()
                    if early_second_start <= clock_in_time <= sched.split_end_time:
                        schedule_end = sched.split_end_time
                        is_split_shift = True
                        break

            # 5. Handle Grace Period and Time Capping
            if schedule_end:
                actual_clock_out_dt = datetime.combine(today, actual_clock_out)
                schedule_end_dt = datetime.combine(today, schedule_end)
                
                # Exceeded 60-minute grace period check
                grace_limit = schedule_end_dt + timedelta(minutes=60)
                if actual_clock_out_dt > grace_limit:
                    return jsonify({
                        'success': False,
                        'error': 'Exceeded the 60-minute grace period after your shift.'
                    }), 400

                # Auto-cap logic: if they clock out after shift end but before 6:30 PM, 
                # record it as exactly the shift end time (standard office rules).
                evening_cutoff = datetime.combine(today, time(18, 30))
                if schedule_end_dt < actual_clock_out_dt < evening_cutoff:
                    last_record.clock_out = schedule_end
                else:
                    last_record.clock_out = actual_clock_out
            else:
                # No schedule end found or not in strict mode
                last_record.clock_out = actual_clock_out
        else:
            # Strict mode disabled
            last_record.clock_out = actual_clock_out

        db.session.commit()

        systemLogEntry(
            action="Clock Out",
            details=f"User {current_user.first_name} {current_user.last_name} clocked out."
        )

        return jsonify({
            'success': True,
            'message': 'Clock-out successful!',
            'data': {
                'user_id': user_id,
                'time_record': last_record.clock_out.strftime("%I:%M %p"),
                'date': last_record.date.strftime("%Y-%m-%d"),
                'shift': 'second' if is_split_shift else 'first'
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'An error occurred: {str(e)}'
        }), 500