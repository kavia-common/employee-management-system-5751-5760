"""
Tests for dashboard summary and department stats endpoints.
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
from src.models.employee import Employee, EmployeeStatus


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


def _signup_and_login(client: TestClient) -> str:
    client.post("/auth/signup", json={"email": "viewer@example.com", "password": "StrongPass123"})
    r = client.post("/auth/login", json={"email": "viewer@example.com", "password": "StrongPass123"})
    assert r.status_code == 200
    return r.json()["access_token"]


def test_dashboard_stats(client: TestClient, db_session: Session):
    token = _signup_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    # Seed employees directly for simplicity
    e1 = Employee(first_name="John", last_name="Doe", email="john@a.com", department="Sales", status=EmployeeStatus.ACTIVE)
    e2 = Employee(first_name="Jane", last_name="Roe", email="jane@a.com", department="Sales", status=EmployeeStatus.INACTIVE)
    e3 = Employee(first_name="Ann", last_name="Kay", email="ann@a.com", department="Engineering", status=EmployeeStatus.ACTIVE)
    db_session.add_all([e1, e2, e3])
    db_session.commit()

    r1 = client.get("/dashboard/summary", headers=headers)
    assert r1.status_code == 200
    body = r1.json()
    assert body["total"] == 3
    assert body["active"] == 2
    assert body["inactive"] == 1

    r2 = client.get("/dashboard/department-stats", headers=headers)
    assert r2.status_code == 200
    stats = r2.json()
    # Convert list to dict for easy asserts
    stats_map = {row["department"]: row["count"] for row in stats}
    assert stats_map["Sales"] == 2
    assert stats_map["Engineering"] == 1


def test_dashboard_protected(client: TestClient):
    r = client.get("/dashboard/summary")
    assert r.status_code == 401
