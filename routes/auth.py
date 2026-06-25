from flask import Blueprint, request, jsonify, url_for, redirect
from flask_login import login_user, logout_user, login_required
from werkzeug.security import check_password_hash
from models.models import User
from routes.api import systemLogEntry
from routes.admin import update_strict_mode

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}

    gia_id = data.get('giaId')
    admin_id = data.get('adminId')
    password = data.get('password')

    # --- Input validation ---
    if not gia_id and not admin_id:
        return jsonify({'success': False, 'error': 'Missing credentials.'}), 400

    if gia_id and admin_id:
        return jsonify({'success': False, 'error': 'Provide only one login type.'}), 400

    # =========================
    # GIA LOGIN
    # =========================
    if gia_id:
        user = User.query.filter_by(user_id=gia_id).first()

        if not user or user.role != 'gia':
            return jsonify({'success': False, 'error': 'No account found with that ID.'}), 401

        if user.status != 'active':
            return jsonify({'success': False, 'error': 'The account is no longer active.'}), 403

        # NOTE: No password check (intentional based on your design)
        update_strict_mode()
        login_user(user)

        systemLogEntry(
            action="Login",
            details=f"User {user.first_name} {user.last_name} logged in to GIA portal."
        )

        return jsonify({'success': True, 'message': f'Welcome {user.first_name}!'}), 200

    # =========================
    # ADMIN LOGIN
    # =========================
    if admin_id:
        if not password:
            return jsonify({'success': False, 'error': 'Password is required.'}), 400

        user = User.query.filter_by(user_id=admin_id).first()

        if not user:
            return jsonify({'success': False, 'error': 'Invalid username or password.'}), 401
        

        if not check_password_hash(user.password, password):
            return jsonify({'success': False, 'error': 'Invalid username or password.'}), 401

        if user.role not in ['superadmin', 'admin']:
            return jsonify({'success': False, 'error': 'Unauthorized access.'}), 403
        
        if user.status != 'active':
            return jsonify({'success': False, 'error': 'The account is no longer active.'}), 403

        update_strict_mode()
        login_user(user)

        systemLogEntry(
            action="Login",
            details=f"Admin {user.first_name} {user.last_name} logged in to Admin portal."
        )

        return jsonify({'success': True, 'message': f'Welcome {user.first_name}!'}), 200

    return jsonify({'success': False, 'error': 'Invalid request.'}), 400


@auth_bp.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    systemLogEntry(
        action="Logout",
        details="User logged out."
    )

    logout_user()
    return redirect(url_for('index'))