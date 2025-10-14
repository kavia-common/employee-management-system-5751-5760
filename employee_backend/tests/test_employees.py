"""
Tests for employee CRUD and listing behaviors.
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


def _signup_and_login(client: TestClient) -> str:
    client.post("/auth/signup", json={"email": "owner@example.com", "password": "StrongPass123"})
    r = client.post("/auth/login", json={"email": "owner@example.com", "password": "StrongPass123"})
    assert r.status_code == 200
    return r.json()["access_token"]


def test_employee_crud_flow(client: TestClient):
    token = _signup_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    # Initially empty list
    r0 = client.get("/employees", headers=headers)
    assert r0.status_code == 200
    assert r0.json()["pagination"]["total"] == 0

    # Create
    new_emp = {
        "first_name": "Alice",
        "last_name": "Smith",
        "email": "alice@example.com",
        "department": "Engineering",
        "title": "Engineer",
        "salary": 120000,
    }
    r1 = client.post("/employees", json=new_emp, headers=headers)
    assert r1.status_code == 201, r1.text
    emp_id = r1.json()["id"]

    # Duplicate email should fail
    r_dup = client.post("/employees", json=new_emp, headers=headers)
    assert r_dup.status_code == 400

    # Get by ID
    r2 = client.get(f"/employees/{emp_id}", headers=headers)
    assert r2.status_code == 200
    assert r2.json()["email"] == "alice@example.com"

    # Update
    r3 = client.put(f"/employees/{emp_id}", json={"title": "Senior Engineer"}, headers=headers)
    assert r3.status_code == 200
    assert r3.json()["title"] == "Senior Engineer"

    # List with search
    r4 = client.get("/employees", params={"search": "ali", "page": 1, "size": 10}, headers=headers)
    assert r4.status_code == 200
    assert r4.json()["pagination"]["total"] == 1

    # Delete
    r5 = client.delete(f"/employees/{emp_id}", headers=headers)
    assert r5.status_code == 204

    # Confirm deletion
    r6 = client.get(f"/employees/{emp_id}", headers=headers)
    assert r6.status_code == 404


def test_employees_protected(client: TestClient):
    r = client.get("/employees")
    assert r.status_code == 401
