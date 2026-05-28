from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash
from sqlalchemy.sql import func
from datetime import time

db = SQLAlchemy()

### USER ###
class User(UserMixin, db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), unique=True, nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    middle_name = db.Column(db.String(50))
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='active')

    attendance_records = db.relationship(
        'Attendance',
        back_populates='user',
        cascade='all, delete-orphan',
        passive_deletes=True
    )

    schedules = db.relationship(
        'Schedule',
        back_populates='user',
        cascade='all, delete-orphan',
        passive_deletes=True
    )

    def set_password(self, password):
        if password:
            self.password = generate_password_hash(password)

    def get_id(self):
        return str(self.user_id)

    @property
    def is_active(self):
        """Override UserMixin is_active to check status column."""
        return self.status == 'active'

    def __repr__(self):
        return f"<User {self.user_id} ({self.role})>"

### ATTENDANCE ###
class Attendance(db.Model):
    __tablename__ = 'attendance'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), db.ForeignKey('user.user_id', ondelete="CASCADE", onupdate="CASCADE"), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    clock_in = db.Column(db.Time)
    clock_out = db.Column(db.Time)
    is_manual = db.Column(db.Boolean, default=False)

    user = db.relationship('User', back_populates='attendance_records')

    def __repr__(self):
        return f"<Attendance {self.user_id} on {self.date}>"

### SCHEDULE ###
class Schedule(db.Model):
    __tablename__ = 'schedule'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), db.ForeignKey('user.user_id', ondelete="CASCADE", onupdate="CASCADE"), nullable=False, index=True)
    day = db.Column(db.String(10), nullable=False)
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time)
    is_split_shift = db.Column(db.Boolean, default=False)
    split_start_time = db.Column(db.Time)
    split_end_time = db.Column(db.Time)

    user = db.relationship('User', back_populates='schedules')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'day', name='unique_schedule_per_user_day'),
    )

    def __repr__(self):
        return f"<Schedule {self.user_id} {self.day}>"

### GLOBAL SETTINGS ###
class GlobalSettings(db.Model):
    __tablename__ = 'global_settings'

    id = db.Column(db.Integer, primary_key=True, default=1)
    unit_head = db.Column(db.String(100), default="Unit Head Name")
    enable_strict_schedule = db.Column(db.Boolean, default=False)
    strict_duration = db.Column(db.Date) # supposed to be open_mode duration
    allow_early_out = db.Column(db.Boolean, default=True)
    allow_overtime = db.Column(db.Boolean, default=False)
    default_start = db.Column(db.Time, default=time(8, 0))
    default_end = db.Column(db.Time, default=time(17, 0))   
    allowed_early_in_mins = db.Column(db.Integer, default=5)

    @staticmethod
    def get():
        return db.session.get(GlobalSettings, 1)

    @property
    def default_schedule(self):
        return type('DefaultSchedule', (object,), {
            'start_time': self.default_start,
            'end_time': self.default_end
        })()

    def __repr__(self):
        return f"<GlobalSettings strict={self.enable_strict_schedule}>"

### LOGS ###
class Logs(db.Model):
    __tablename__ = 'system_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), db.ForeignKey('user.user_id', ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True)
    action = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, server_default=func.now(), nullable=False)
    details = db.Column(db.Text)
    client_ip = db.Column(db.String(45))

    user = db.relationship('User', back_populates='logs', lazy=True)

    def __repr__(self):
        return f"<Log {self.action} by {self.user_id} at {self.timestamp}>"