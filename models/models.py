from datetime import time

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


### USER ###
class User(UserMixin, db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    middle_name = db.Column(db.String(50))
    phone_number = db.Column(db.String(30))
    laboratory = db.Column(db.String(100))
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'superadmin', 'admin', 'gia'
    status = db.Column(db.String(20), nullable=False, default="active")

    attendance_records = db.relationship(
        "Attendance",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    schedules = db.relationship(
        "Schedule",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    logs = db.relationship(
        "Logs",
        back_populates="user",
        passive_deletes=True,
    )

    inconsistencies = db.relationship(
        "AttendanceInconsistency",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def set_password(self, password: str) -> None:
        if password:
            self.password = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        if not self.password or not password:
            return False
        return check_password_hash(self.password, password)

    def get_id(self) -> str:
        return str(self.user_id)

    @property
    def is_active(self) -> bool:
        """Override UserMixin is_active to check status column."""
        return self.status == "active"

    @property
    def full_name(self) -> str:
        middle = f" {self.middle_name[0]}." if self.middle_name else ""
        return f"{self.first_name}{middle} {self.last_name}"

    def __repr__(self) -> str:
        return f"<User {self.user_id} ({self.role})>"


### ATTENDANCE ###
class Attendance(db.Model):
    __tablename__ = "attendance"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.String(50),
        db.ForeignKey("user.user_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    date = db.Column(db.Date, nullable=False, index=True)
    clock_in = db.Column(db.Time)
    clock_out = db.Column(db.Time)
    is_manual = db.Column(db.Boolean, default=False)

    user = db.relationship("User", back_populates="attendance_records")

    __table_args__ = (
        db.Index("idx_attendance_user_date", "user_id", "date"),
    )

    def __repr__(self) -> str:
        return f"<Attendance {self.user_id} on {self.date}>"


### SCHEDULE ###
class Schedule(db.Model):
    __tablename__ = "schedule"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.String(50),
        db.ForeignKey("user.user_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    day = db.Column(db.String(10), nullable=False)  # 'mw', 'tth', 'fri', 'sat', or daily: 'mon', 'tue', 'wed', 'thu'
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time)
    is_split_shift = db.Column(db.Boolean, default=False)
    split_start_time = db.Column(db.Time)
    split_end_time = db.Column(db.Time)

    user = db.relationship("User", back_populates="schedules")

    __table_args__ = (
        db.UniqueConstraint("user_id", "day", name="unique_schedule_per_user_day"),
    )

    def __repr__(self) -> str:
        return f"<Schedule {self.user_id} {self.day}>"


### GLOBAL SETTINGS ###
class GlobalSettings(db.Model):
    __tablename__ = "global_settings"

    id = db.Column(db.Integer, primary_key=True, default=1)
    unit_head = db.Column(db.String(100), default="Unit Head Name")
    enable_strict_schedule = db.Column(db.Boolean, default=False)
    strict_duration = db.Column(db.Date)  # open mode expiration date
    allow_early_out = db.Column(db.Boolean, default=True)
    allow_overtime = db.Column(db.Boolean, default=False)
    default_start = db.Column(db.Time, default=time(8, 0))
    default_end = db.Column(db.Time, default=time(17, 0))
    allowed_early_in_mins = db.Column(db.Integer, default=5)
    allowed_late_mins = db.Column(db.Integer, default=10)

    @classmethod
    def get(cls) -> "GlobalSettings":
        settings = db.session.get(cls, 1)
        if not settings:
            settings = cls.query.first()
        return settings

    @classmethod
    def get_or_create(cls) -> "GlobalSettings":
        settings = cls.get()
        if not settings:
            settings = cls(
                id=1,
                unit_head="Unit Head Name",
                enable_strict_schedule=False,
                allow_early_out=True,
                allow_overtime=False,
                default_start=time(8, 0),
                default_end=time(17, 0),
                allowed_early_in_mins=5,
                allowed_late_mins=10,
            )
            db.session.add(settings)
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
                settings = cls.query.first()
        return settings

    def __repr__(self) -> str:
        return f"<GlobalSettings strict={self.enable_strict_schedule}>"


### LOGS ###
class Logs(db.Model):
    __tablename__ = "system_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.String(50),
        db.ForeignKey("user.user_id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    action = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, server_default=func.now(), nullable=False, index=True)
    details = db.Column(db.Text)
    client_ip = db.Column(db.String(45))

    user = db.relationship("User", back_populates="logs", lazy=True)

    def __repr__(self) -> str:
        return f"<Log {self.action} by {self.user_id} at {self.timestamp}>"


### ATTENDANCE INCONSISTENCIES ###
class AttendanceInconsistency(db.Model):
    __tablename__ = "attendance_inconsistencies"
    __table_args__ = {
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_general_ci",
    }

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.String(50),
        db.ForeignKey("user.user_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    date = db.Column(db.Date, nullable=False, index=True)
    issue_type = db.Column(db.String(50), nullable=False)  # 'Late', 'Early Out', 'Overtime'
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, server_default=func.now(), nullable=False)

    user = db.relationship("User", back_populates="inconsistencies")

    def __repr__(self) -> str:
        return f"<AttendanceInconsistency {self.user_id} {self.issue_type} on {self.date}>"
