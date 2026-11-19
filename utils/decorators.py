from functools import wraps

from flask import jsonify, redirect, request, url_for
from flask_login import current_user

from utils.network import is_ip_whitelisted


def admin_required(fn):
    """Decorator requiring the current user to be logged in with superadmin or admin role."""

    @wraps(fn)
    def decorated_view(*args, **kwargs):
        if not current_user.is_authenticated:
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"success": False, "error": "Authentication required."}), 401
            return redirect(url_for("auth.login"))

        if current_user.role not in ["superadmin", "admin"]:
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"success": False, "error": "Access Denied"}), 403
            return redirect(url_for("auth.login"))

        return fn(*args, **kwargs)

    return decorated_view


def gia_required(fn):
    """Decorator requiring the current user to be logged in with GIA role."""

    @wraps(fn)
    def decorated_view(*args, **kwargs):
        if not current_user.is_authenticated:
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"success": False, "error": "Authentication required."}), 401
            return redirect(url_for("auth.login"))

        if current_user.role != "gia":
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"success": False, "error": "Access Denied"}), 403
            return redirect(url_for("admin.dashboard"))

        return fn(*args, **kwargs)

    return decorated_view


def ip_whitelist_required(fn):
    """Decorator to enforce IP whitelist restrictions for GIA kiosk / attendance features."""

    @wraps(fn)
    def decorated_view(*args, **kwargs):
        if current_user.is_authenticated and not is_ip_whitelisted(user_id=current_user.user_id):
            if request.is_json or request.path.startswith("/api/"):
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Access denied. Your device is not allowed to use this feature.",
                        }
                    ),
                    403,
                )
            return redirect(url_for("gia.blocked"))
        return fn(*args, **kwargs)

    return decorated_view
