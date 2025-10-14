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


def test_cors_preflight_signup(client: TestClient):
    """
    Simulate a browser preflight (OPTIONS) request to /auth/signup and
    verify CORS headers are present for the configured origin.
    """
    origin = "https://vscode-internal-19668-beta.beta01.cloud.kavia.ai:3000"
    headers = {
        "Origin": origin,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    }
    r = client.options("/auth/signup", headers=headers)
    assert r.status_code in (200, 204)
    assert r.headers.get("access-control-allow-origin") == origin
    vary = r.headers.get("vary", "")
    # Starlette sets Vary to include Origin for CORS handling
    assert "origin" in vary.lower()


def test_cors_post_signup_includes_headers(client: TestClient):
    """
    Ensure that an actual POST to /auth/signup includes the proper
    Access-Control-Allow-Origin header and exposes X-Correlation-ID.
    """
    origin = "https://vscode-internal-19668-beta.beta01.cloud.kavia.ai:3000"
    payload = {"email": "cors@example.com", "password": "StrongPass123"}
    r = client.post("/auth/signup", json=payload, headers={"Origin": origin})
    # 201 on first run; if re-run, may return 400 (duplicate). We only check CORS headers.
    assert r.headers.get("access-control-allow-origin") == origin
    expose = r.headers.get("access-control-expose-headers", "")
    assert "X-Correlation-ID" in expose
    vary = r.headers.get("vary", "")
    assert "origin" in vary.lower()
