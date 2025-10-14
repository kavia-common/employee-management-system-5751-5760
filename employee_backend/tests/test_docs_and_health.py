"""
Basic tests to ensure the server starts cleanly and /docs loads,
and that health endpoint includes the correlation and Vary headers.
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
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_docs_load(client: TestClient):
    # FastAPI serves Swagger UI at /docs and openapi.json at /openapi.json
    r_ui = client.get("/docs")
    assert r_ui.status_code == 200

    r_openapi = client.get("/openapi.json")
    assert r_openapi.status_code == 200
    assert r_openapi.headers.get("content-type", "").lower().startswith("application/json")


def test_health_has_headers(client: TestClient):
    r = client.get("/")
    assert r.status_code == 200
    vary = r.headers.get("vary", "")
    assert "origin" in vary.lower()
    assert r.headers.get("X-Correlation-ID")
