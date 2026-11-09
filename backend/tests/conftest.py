"""Run against migrated PostgreSQL. Every test rolls its own outer transaction back."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.security import passwords, token
from app.db.session import engine, get_db
from app.main import app
from app.models import User
from app.seed import seed_schemes
from sqlalchemy import select


@pytest.fixture
def db():
    with engine.connect() as connection:
        outer = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False) as session:
            yield session
        outer.rollback()


@pytest.fixture
def client(db):
    def override():
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
    app.dependency_overrides[get_db] = override
    with TestClient(app, raise_server_exceptions=True) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def no_scheduler(monkeypatch):
    from app.main import settings
    monkeypatch.setattr(settings, "enable_scheduler", False)


@pytest.fixture
def actors(db):
    users = {}
    for name, role in [("test_admin", "super_admin"), ("test_staff_a", "staff"), ("test_staff_b", "staff")]:
        if role == 'super_admin':
            existing = db.scalar(select(User).where(User.role == 'super_admin'))
            if existing:
                users[name] = {"user": existing, "headers": {"Authorization": "Bearer " + token(existing)}}
                continue
        user = User(username=name, full_name=name, role=role, password_hash=passwords.hash("TestPassword123!"))
        db.add(user)
        db.flush()
        users[name] = {"user": user, "headers": {"Authorization": "Bearer " + token(user)}}
    seed_schemes(db)
    db.commit()
    return users
