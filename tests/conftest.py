from datetime import time

import pytest

from app import create_app
from config import TestingConfig
from models.models import GlobalSettings, Schedule, User, db


@pytest.fixture
def app():
    """Create and configure a clean testing app instance with SQLite in memory."""
    application = create_app(TestingConfig)

    with application.app_context():
        db.create_all()

        # Seed global settings
        GlobalSettings.get_or_create()

        # Seed Superadmin
        superadmin = User(
            user_id="superadmin",
            first_name="Super",
            last_name="Admin",
            role="superadmin",
            status="active",
        )
        superadmin.set_password("admin123")
        db.session.add(superadmin)

        # Seed Admin
        admin = User(
            user_id="admin1",
            first_name="Admin",
            last_name="User",
            role="admin",
            status="active",
        )
        admin.set_password("admin123")
        db.session.add(admin)

        # Seed Active GIA
        gia = User(
            user_id="2024001",
            first_name="John",
            last_name="Doe",
            middle_name="Santos",
            role="gia",
            status="active",
            phone_number="+63 912 345 6789",
            laboratory="Lab 101",
        )
        gia.set_password("admin123")
        db.session.add(gia)

        # Seed Inactive GIA
        inactive_gia = User(
            user_id="2024002",
            first_name="Jane",
            last_name="Smith",
            role="gia",
            status="inactive",
        )
        inactive_gia.set_password("admin123")
        db.session.add(inactive_gia)

        # Seed a schedule for John Doe
        for block in ["mw", "tth", "fri", "sat"]:
            sched = Schedule(
                user_id="2024001",
                day=block,
                start_time=time(8, 0),
                end_time=time(17, 0),
                is_split_shift=False,
            )
            db.session.add(sched)

        db.session.commit()

        yield application

        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """An unauthenticated test client."""
    return app.test_client()


@pytest.fixture
def admin_client(app, client):
    """A test client authenticated as an admin user."""
    client.post(
        "/auth/login",
        json={"adminId": "admin1", "password": "admin123"},
    )
    return client


@pytest.fixture
def superadmin_client(app, client):
    """A test client authenticated as superadmin."""
    client.post(
        "/auth/login",
        json={"adminId": "superadmin", "password": "admin123"},
    )
    return client


@pytest.fixture
def gia_client(app, client):
    """A test client authenticated as GIA employee 2024001."""
    client.post(
        "/auth/login",
        json={"giaId": "2024001"},
    )
    return client
