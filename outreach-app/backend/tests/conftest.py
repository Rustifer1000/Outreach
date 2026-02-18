"""Pytest fixtures: in-memory SQLite and FastAPI TestClient."""
import os
import sys
from pathlib import Path

import pytest

# Use in-memory DB for tests (set before any app import that might read config)
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

# Backend app on path
backend = Path(__file__).resolve().parent.parent
if str(backend) not in sys.path:
    sys.path.insert(0, str(backend))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app

# Ensure all models are registered on Base.metadata (app.main already loads them)
import app.models  # noqa: F401


@pytest.fixture
def test_engine():
    """Fresh in-memory engine with all tables, per test (no shared state)."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def client(test_engine):
    """TestClient with get_db overridden to use the test engine for this test."""
    Session = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def db_session(test_engine):
    """Session for seeding test data (same in-memory DB as client for this test)."""
    Session = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
