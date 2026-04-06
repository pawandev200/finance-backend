"""
Pytest fixtures shared across all test modules.
Uses an in-memory SQLite database that is freshly created per test session.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.session import get_db
from app.models import User, Transaction, AuditLog  # noqa: F401
from main import app

# ── In-memory test database ───────────────────────────────────────────────────
TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── Helper: Create users and get tokens ───────────────────────────────────────

def create_user_and_login(client, email, password, role, full_name="Test User"):
    from app.core.security import get_password_hash
    from app.models.user import User
    from app.core.permissions import Role

    # Directly insert user into test DB
    db = TestSessionLocal()
    existing = db.query(User).filter(User.email == email).first()
    if not existing:
        user = User(
            email=email,
            full_name=full_name,
            hashed_password=get_password_hash(password),
            role=role,
        )
        db.add(user)
        db.commit()
    db.close()

    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


@pytest.fixture
def admin_token(client):
    from app.core.permissions import Role
    return create_user_and_login(client, "admin@test.com", "Admin@123", Role.ADMIN, "Admin User")


@pytest.fixture
def analyst_token(client):
    from app.core.permissions import Role
    return create_user_and_login(client, "analyst@test.com", "Analyst@123", Role.ANALYST, "Analyst User")


@pytest.fixture
def viewer_token(client):
    from app.core.permissions import Role
    return create_user_and_login(client, "viewer@test.com", "Viewer@123", Role.VIEWER, "Viewer User")
