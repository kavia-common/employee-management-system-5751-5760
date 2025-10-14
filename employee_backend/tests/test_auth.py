"""
Tests for authentication endpoints: signup, login, and me.
"""

from __future__ import annotations

import os
import tempfile
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.api.main import app
from src.db.base import Base
from src.db.session import get_db


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    # Use a temporary SQLite database file per test to avoid cross-test state
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base.metadata.create_all(bind=engine)

        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
            engine.dispose()


@pytest.fixture(scope="function")
def client(db_session: Session) -> TestClient:
    # Override get_db dependency to use the test session
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_signup_login_me_flow(client: TestClient):
    # Signup
    payload = {"email": "user@example.com", "password": "StrongPass123", "full_name": "Test User"}
    r = client.post("/auth/signup", json=payload)
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["email"] == payload["email"]
    assert "id" in data and data["is_active"] is True

    # Duplicate signup should fail
    r2 = client.post("/auth/signup", json=payload)
    assert r2.status_code == 400
    assert "error" in r2.json()

    # Login
    r3 = client.post("/auth/login", json={"email": payload["email"], "password": payload["password"]})
    assert r3.status_code == 200, r3.text
    token = r3.json()["access_token"]
    assert token

    # Invalid login
    r4 = client.post("/auth/login", json={"email": payload["email"], "password": "WrongPass!"})
    assert r4.status_code == 401

    # Current user
    headers = {"Authorization": f"Bearer {token}"}
    r5 = client.get("/auth/me", headers=headers)
    assert r5.status_code == 200
    me = r5.json()
    assert me["email"] == payload["email"]


def test_me_requires_auth(client: TestClient):
    r = client.get("/auth/me")
    assert r.status_code == 401
    body = r.json()
    assert "error" in body and body["error"]["code"] == 401
