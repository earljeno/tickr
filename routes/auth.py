from flask import Blueprint, current_app, jsonify, redirect, request, session, url_for
from flask_login import current_user, login_user, logout_user

from models.models import GlobalSettings, Logs, User, db
from utils.logging import system_log_entry
from utils.timezone import get_now

auth_bp = Blueprint("auth", __name__)


def update_strict_mode() -> None:
    """Auto-reactivate strict mode if temporary open-mode duration has expired."""
    settings_obj = GlobalSettings.get()
    if not settings_obj or settings_obj.strict_duration is None:
        return

    now = get_now()
    today = now.date()

    if not settings_obj.enable_strict_schedule and today >= settings_obj.strict_duration:
        settings_obj.enable_strict_schedule = True
        settings_obj.strict_duration = None

        entry = Logs(
            user_id="admin",
            action="Update",
            details=f"SYSTEM: Open mode expired on {today}, strict mode reactivated.",
            timestamp=now,
        )
        db.session.add(entry)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}

    gia_id = data.get("giaId")
    admin_id = data.get("adminId")
    password = data.get("password")

    # --- Input validation ---
    if not gia_id and not admin_id:
        return jsonify({"success": False, "error": "Missing credentials."}), 400

    if gia_id and admin_id:
        return jsonify({"success": False, "error": "Provide only one login type."}), 400

    # =========================
    # GIA LOGIN (Kiosk-style by ID)
    # =========================
    if gia_id:
        user = User.query.filter_by(user_id=str(gia_id).strip()).first()

        if not user or user.role != "gia":
            return jsonify({"success": False, "error": "No account found with that ID."}), 401

        if user.status != "active":
            return jsonify({"success": False, "error": "The account is no longer active."}), 403

        update_strict_mode()
        login_user(user, remember=True)

        system_log_entry(
            action="Login",
            details=f"User {user.first_name} {user.last_name} logged in to GIA portal.",
            user_id=user.user_id,
        )

        return (
            jsonify(
                {
                    "success": True,
                    "message": f"Welcome {user.first_name}!",
                    "redirect": url_for("gia.dashboard"),
                }
            ),
            200,
        )

    # =========================
    # ADMIN LOGIN
    # =========================
    if admin_id:
        if not password:
            return jsonify({"success": False, "error": "Password is required."}), 400

        user = User.query.filter_by(user_id=str(admin_id).strip()).first()

        if not user or not user.check_password(password):
            return jsonify({"success": False, "error": "Invalid username or password."}), 401

        if user.role not in ["superadmin", "admin"]:
            return jsonify({"success": False, "error": "Unauthorized access."}), 403

        if user.status != "active":
            return jsonify({"success": False, "error": "The account is no longer active."}), 403

        update_strict_mode()
        login_user(user, remember=True)

        system_log_entry(
            action="Login",
            details=f"Admin {user.first_name} {user.last_name} logged in to Admin portal.",
            user_id=user.user_id,
        )

        return (
            jsonify(
                {
                    "success": True,
                    "message": f"Welcome {user.first_name}!",
                    "redirect": url_for("admin.dashboard"),
                }
            ),
            200,
        )

    return jsonify({"success": False, "error": "Invalid request."}), 400


@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():
    if current_user.is_authenticated:
        system_log_entry(
            action="Logout",
            details=f"User {current_user.first_name} {current_user.last_name} logged out.",
            user_id=current_user.user_id,
        )
    session.clear()
    logout_user()

    response = redirect(url_for("index"))

    cookie_name = current_app.config.get("REMEMBER_COOKIE_NAME", "remember_token")
    domain = current_app.config.get("REMEMBER_COOKIE_DOMAIN")
    path = current_app.config.get("REMEMBER_COOKIE_PATH", "/")
    response.delete_cookie(cookie_name, domain=domain, path=path)

    session_cookie = current_app.config.get("SESSION_COOKIE_NAME", "session")
    session_domain = current_app.config.get("SESSION_COOKIE_DOMAIN")
    session_path = current_app.config.get("SESSION_COOKIE_PATH", "/")
    response.delete_cookie(session_cookie, domain=session_domain, path=session_path)

    return response
