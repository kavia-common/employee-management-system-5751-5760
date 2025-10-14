"""
Additional tests validating that /auth/login returns a non-empty JWT access_token and token_type 'bearer',
and that the returned token authorizes access to /auth/me with proper headers present.

This test complements existing authentication tests by explicitly checking the response shape and
subsequent bearer auth usage in a minimal flow.
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
    # Use an isolated SQLite database file
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
    # Override get_db to use the function-scoped test session
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_login_returns_bearer_jwt_and_allows_me(client: TestClient):
    # Arrange: create a user
    signup_payload = {"email": "contract@example.com", "password": "StrongPass123"}
    r_signup = client.post("/auth/signup", json=signup_payload)
    assert r_signup.status_code in (201, 409)

    # Act: login to obtain token
    r_login = client.post("/auth/login", json=signup_payload)
    assert r_login.status_code == 200, r_login.text
    body = r_login.json()

    # Assert: Access token present and non-empty; token_type is 'bearer'
    token = body.get("access_token")
    assert isinstance(token, str) and token.strip() != ""
    assert body.get("token_type") == "bearer"

    # Assert: Headers include correlation ID and Vary: Origin
    assert r_login.headers.get("X-Correlation-ID")
    vary = r_login.headers.get("vary", "")
    assert "origin" in (vary or "").lower()

    # Act: call /auth/me with Authorization: Bearer <token>
    headers = {"Authorization": f"Bearer {token}"}
    r_me = client.get("/auth/me", headers=headers)
    assert r_me.status_code == 200, r_me.text

    me = r_me.json()
    assert me.get("email") == signup_payload["email"]

    # Assert: response headers include correlation id
    assert r_me.headers.get("X-Correlation-ID")
