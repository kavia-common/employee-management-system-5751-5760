"""
Additional CORS header tests.

These tests verify that the backend consistently includes "Vary: Origin" on both
success and error responses, even when the Origin header is not provided by the client.
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
    # Use a temporary SQLite file database for isolation per test
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
    # Override app's DB dependency to use the test session
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_vary_header_present_on_401_without_origin(client: TestClient):
    # Act: invalid login without any Origin header
    r = client.post("/auth/login", json={"email": "noone@example.com", "password": "WrongPass123"})
    # Assert: 401 with Vary including Origin
    assert r.status_code == 401
    vary = r.headers.get("vary", "")
    assert "origin" in vary.lower()


def test_vary_header_present_on_success_without_origin(client: TestClient):
    # Arrange: create a user
    signup_payload = {"email": "noorigin@example.com", "password": "StrongPass123"}
    r_signup = client.post("/auth/signup", json=signup_payload)
    assert r_signup.status_code in (201, 409)

    # Act: login successfully without any Origin header
    r_login = client.post("/auth/login", json=signup_payload)

    # Assert: 200 with Vary including Origin and token shape
    assert r_login.status_code == 200, r_login.text
    vary = r_login.headers.get("vary", "")
    assert "origin" in vary.lower()
    body = r_login.json()
    assert isinstance(body.get("access_token"), str) and body["access_token"].strip() != ""
    assert body.get("token_type") == "bearer"
