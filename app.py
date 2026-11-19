import logging
import os

import click
from flask import Flask, redirect, render_template, url_for
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from sqlalchemy.exc import OperationalError

from config import Config, config_by_name
from flask_session import Session
from models.models import GlobalSettings, User, db
from routes.admin import admin_bp
from routes.api import api_bp
from routes.auth import auth_bp
from routes.gia import gia_bp

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("tickr")

migrate = Migrate()
login_manager = LoginManager()


def create_app(config_object=None) -> Flask:
    """Application factory for Tickr."""
    app = Flask(__name__)

    # Determine configuration
    if config_object is None:
        env_mode = os.getenv("FLASK_ENV", "default").lower()
        config_object = config_by_name.get(env_mode, Config)

    app.config.from_object(config_object)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Initialize session store
    if app.config.get("SESSION_TYPE") == "filesystem":
        session_dir = app.config.get("SESSION_FILE_DIR", "./flask_session")
        os.makedirs(session_dir, exist_ok=True)
        Session(app)

    # Initialize Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = "index"

    @login_manager.unauthorized_handler
    def unauthorized():
        from flask import jsonify, request
        if request.is_json or request.path.startswith("/api/"):
            return jsonify({"success": False, "error": "Authentication required."}), 401
        return redirect(url_for(login_manager.login_view))

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.filter_by(user_id=str(user_id)).first()

    # Register blueprints
    app.register_blueprint(gia_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(api_bp, url_prefix="/api")

    # Main entry route
    @app.route("/")
    def index():
        if current_user.is_authenticated:
            if current_user.role in ["superadmin", "admin"]:
                return redirect(url_for("admin.dashboard"))
            if current_user.role == "gia":
                return redirect(url_for("gia.dashboard"))
        return render_template("auth/login.html")

    # Error handling
    @app.errorhandler(OperationalError)
    def maintenance_mode(e):
        logger.error(f"Database Error: {e}")
        return render_template("maintenance.html"), 503

    # Register CLI commands
    register_commands(app)

    return app


def register_commands(app: Flask):
    """Register custom Flask CLI commands."""

    @app.cli.command("init-db")
    def init_db_cmd():
        """Initialize database tables and create initial settings."""
        db.create_all()
        GlobalSettings.get_or_create()
        click.echo("Database initialized successfully.")

    @app.cli.command("seed-admin")
    @click.option("--username", default=None, help="Superadmin username (defaults to SUPERADMIN_USER or 'superadmin')")
    @click.option("--password", default=None, help="Superadmin password (defaults to SUPERADMIN_PASS or 'admin123')")
    def seed_admin_cmd(username, password):
        """Create or verify the default superadmin account."""
        admin_user = username or os.getenv("SUPERADMIN_USER", "superadmin")
        admin_pass = password or os.getenv("SUPERADMIN_PASS", "admin123")

        existing = User.query.filter_by(user_id=admin_user).first()
        if not existing:
            new_admin = User(
                user_id=admin_user,
                first_name="Super",
                last_name="Admin",
                role="superadmin",
                status="active",
            )
            new_admin.set_password(admin_pass)
            db.session.add(new_admin)
            db.session.commit()
            click.echo(f"Created default superadmin user '{admin_user}'.")
        else:
            click.echo(f"Superadmin user '{admin_user}' already exists.")


# Top-level application instance for WSGI servers (waitress, gunicorn)
app = create_app()

if __name__ == "__main__":
    with app.app_context():
        # Ensure tables exist in development / standalone run
        db.create_all()
        GlobalSettings.get_or_create()

        # Seed superadmin if none exists
        default_admin = os.getenv("SUPERADMIN_USER", "superadmin")
        default_pass = os.getenv("SUPERADMIN_PASS", "admin123")
        if not User.query.filter_by(user_id=default_admin).first():
            admin = User(
                user_id=default_admin,
                first_name="Super",
                last_name="Admin",
                role="superadmin",
                status="active",
            )
            admin.set_password(default_pass)
            db.session.add(admin)
            db.session.commit()
            logger.info(f"Initialized default superadmin '{default_admin}'.")

    port = int(os.getenv("PORT", "3005"))
    app.run(host="0.0.0.0", port=port, debug=True)
