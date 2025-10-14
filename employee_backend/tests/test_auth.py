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
from src.core.security import decode_access_token


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

    # Duplicate signup should fail with 409 Conflict
    r2 = client.post("/auth/signup", json=payload)
    assert r2.status_code == 409
    assert "error" in r2.json()

    # Login
    r3 = client.post("/auth/login", json={"email": payload["email"], "password": payload["password"]})
    assert r3.status_code == 200, r3.text
    token = r3.json()["access_token"]
    assert token
    assert r3.json().get("token_type") == "bearer"
    # Ensure correlation header exists on success responses as well
    assert r3.headers.get("X-Correlation-ID")

    # Invalid login
    r4 = client.post("/auth/login", json={"email": payload["email"], "password": "WrongPass!"})
    assert r4.status_code == 401
    # Error payload shape and correlation header
    body4 = r4.json()
    assert "error" in body4 and body4["error"]["code"] == 401
    assert r4.headers.get("X-Correlation-ID")

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
    # Ensure correlation header on error responses
    assert r.headers.get("X-Correlation-ID")


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
    # Correlation header should be present on normal responses
    assert r.headers.get("X-Correlation-ID")


def test_cors_post_signup_includes_headers(client: TestClient):
    """
    Ensure that an actual POST to /auth/signup includes the proper
    Access-Control-Allow-Origin header and exposes X-Correlation-ID.
    """
    origin = "https://vscode-internal-19668-beta.beta01.cloud.kavia.ai:3000"
    payload = {"email": "cors@example.com", "password": "StrongPass123"}
    r = client.post("/auth/signup", json=payload, headers={"Origin": origin})
    # 201 on first run; if re-run, may return 409 (duplicate). We only check CORS headers.
    assert r.headers.get("access-control-allow-origin") == origin
    expose = r.headers.get("access-control-expose-headers", "")
    assert "X-Correlation-ID" in expose
    vary = r.headers.get("vary", "")
    assert "origin" in vary.lower()
    # Correlation header should be set
    assert r.headers.get("X-Correlation-ID")


def test_cors_post_login_invalid_includes_headers(client: TestClient):
    """
    Invalid login should return 401 with standardized body and include CORS headers
    so browsers surface the error to client code instead of failing CORS.
    """
    origin = "https://vscode-internal-19668-beta.beta01.cloud.kavia.ai:3000"
    r = client.post(
        "/auth/login",
        json={"email": "nouser@example.com", "password": "WrongPass!"},
        headers={"Origin": origin},
    )
    assert r.status_code == 401
    assert r.headers.get("access-control-allow-origin") == origin
    body = r.json()
    assert "error" in body and body["error"]["code"] == 401
    # Correlation header present on error responses
    assert r.headers.get("X-Correlation-ID")


def test_cors_post_login_success_includes_headers(client: TestClient):
    """
    Successful login should include CORS headers as well.
    """
    origin = "https://vscode-internal-19668-beta.beta01.cloud.kavia.ai:3000"
    # Ensure user exists
    client.post("/auth/signup", json={"email": "loginuser@example.com", "password": "StrongPass123"})
    r = client.post(
        "/auth/login",
        json={"email": "loginuser@example.com", "password": "StrongPass123"},
        headers={"Origin": origin},
    )
    assert r.status_code == 200, r.text
    assert r.headers.get("access-control-allow-origin") == origin
    # Ensure Vary includes Origin as per acceptance criteria
    vary = r.headers.get("vary", "")
    assert "origin" in vary.lower()
    expose = r.headers.get("access-control-expose-headers", "")
    assert "X-Correlation-ID" in expose
    # Correlation header present on success responses
    assert r.headers.get("X-Correlation-ID")


def test_duplicate_signup_returns_409_with_cors(client: TestClient):
    """
    Duplicate signup should return 409 Conflict and include proper CORS headers when Origin is supplied.
    """
    origin = "https://vscode-internal-19668-beta.beta01.cloud.kavia.ai:3000"
    payload = {"email": "dup@example.com", "password": "StrongPass123"}
    r1 = client.post("/auth/signup", json=payload)
    assert r1.status_code in (201, 409)

    r2 = client.post("/auth/signup", json=payload, headers={"Origin": origin})
    assert r2.status_code == 409
    assert r2.headers.get("access-control-allow-origin") == origin
    body = r2.json()
    assert "error" in body and body["error"]["code"] == 409
    assert r2.headers.get("X-Correlation-ID")


def test_signup_validation_error_returns_422_with_cors(client: TestClient):
    """
    Invalid signup payload (missing password) should return 422 and include CORS headers, not 500.
    """
    origin = "https://vscode-internal-19668-beta.beta01.cloud.kavia.ai:3000"
    r = client.post("/auth/signup", json={"email": "bad@example.com"}, headers={"Origin": origin})
    assert r.status_code == 422
    assert r.headers.get("access-control-allow-origin") == origin
    body = r.json()
    assert "error" in body and body["error"]["code"] == 422
    assert r.headers.get("X-Correlation-ID")


def test_login_validation_error_returns_422_with_cors(client: TestClient):
    """
    Invalid login payload (password too short) should return 422 and include CORS headers.
    """
    origin = "https://vscode-internal-19668-beta.beta01.cloud.kavia.ai:3000"
    r = client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "short"},
        headers={"Origin": origin},
    )
    assert r.status_code == 422
    assert r.headers.get("access-control-allow-origin") == origin
    body = r.json()
    assert "error" in body and body["error"]["code"] == 422
    assert r.headers.get("X-Correlation-ID")


def test_login_response_token_shape(client: TestClient):
    """
    Login success should return a JSON object containing:
      - access_token: string (non-empty JWT)
      - token_type: 'bearer'
    And the JWT should decode with expected claims including 'sub', 'iat' and 'exp'.
    """
    email = "shape@example.com"
    password = "StrongPass123"
    # Ensure user exists
    client.post("/auth/signup", json={"email": email, "password": password})
    # Login
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    body = r.json()
    # Assert token shape
    assert isinstance(body.get("access_token"), str) and body["access_token"]
    assert body.get("token_type") == "bearer"
    # Decode and assert essential claims exist
    payload = decode_access_token(body["access_token"])
    assert "sub" in payload and payload["sub"]
    assert "iat" in payload and "exp" in payload


def test_login_returns_token_and_token_type(client: TestClient):
    """
    Ensure that a successful login returns a non-empty JWT access_token and token_type 'bearer'.
    """
    # Arrange: create a test user
    email = "named_check@example.com"
    password = "StrongPass123"
    client.post("/auth/signup", json={"email": email, "password": password})

    # Act: login
    r = client.post("/auth/login", json={"email": email, "password": password})

    # Assert: token shape and presence
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body.get("access_token"), str) and body["access_token"].strip() != ""
    assert body.get("token_type") == "bearer"
    # Correlation header should be present
    assert r.headers.get("X-Correlation-ID")


def test_login_invalid_credentials_401_with_cors(client: TestClient):
    """
    Invalid credentials should return 401 with standardized error JSON and include CORS headers and Vary: Origin.
    """
    origin = "https://vscode-internal-19668-beta.beta01.cloud.kavia.ai:3000"

    # Act: login attempt with nonexistent user
    r = client.post(
        "/auth/login",
        json={"email": "noone@example.com", "password": "WrongPass123"},
        headers={"Origin": origin},
    )

    # Assert: 401 with proper JSON envelope and CORS headers
    assert r.status_code == 401
    body = r.json()
    assert "error" in body and body["error"]["code"] == 401
    assert r.headers.get("access-control-allow-origin") == origin
    vary = r.headers.get("vary", "")
    assert "origin" in (vary or "").lower()
    # Correlation header should be present
    assert r.headers.get("X-Correlation-ID")
