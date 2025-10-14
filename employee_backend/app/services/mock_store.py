"""
In-memory mock store [STUB].

Provides a simple, thread-safe in-memory store for users and employees
with deterministic seeded data. This replaces database/ORM for the stub.
"""
from __future__ import annotations

import itertools
import threading
from typing import Dict, List, Optional


class MockStore:
    """Thread-safe in-memory store. [STUB]"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._users: Dict[int, Dict] = {}
        self._employees: Dict[int, Dict] = {}
        self._user_id_seq = itertools.count(start=1)
        self._employee_id_seq = itertools.count(start=1)
        self._seed()

    # ---- Users ----
    def create_user(self, *, email: str, password: str) -> Dict:
        with self._lock:
            # NOTE: No hashing in stub
            user_id = next(self._user_id_seq)
            user = {"id": user_id, "email": email, "password": password, "is_active": True}
            self._users[user_id] = user
            return dict(user)

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        with self._lock:
            for u in self._users.values():
                if u["email"].lower() == email.lower():
                    return dict(u)
            return None

    # ---- Employees ----
    def _seed(self) -> None:
        """Seed deterministic employees for demo purposes."""
        first_names = ["Alice", "Bob", "Carol", "David", "Eve"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones"]
        departments = ["Engineering", "HR", "Sales", "Finance", "IT"]
        titles = ["Engineer", "Manager", "Analyst", "Specialist", "Coordinator"]

        # Create 25 deterministic employees
        for i in range(25):
            first = first_names[i % len(first_names)]
            last = last_names[i % len(last_names)]
            dept = departments[i % len(departments)]
            title = titles[i % len(titles)]
            email = f"{first.lower()}.{last.lower()}{i}@example.com"
            self.create_employee(
                {
                    "first_name": first,
                    "last_name": last,
                    "email": email,
                    "department": dept,
                    "title": title,
                    "phone": None,
                    "manager_id": None,
                    "salary": 90000 + i * 1000,
                    "date_hired": None,
                    "status": "ACTIVE",
                }
            )

    def list_employees(self) -> List[Dict]:
        with self._lock:
            return [dict(e) for e in self._employees.values()]

    def search_employees(self, query: str) -> List[Dict]:
        q = (query or "").strip().lower()
        with self._lock:
            if not q:
                return [dict(e) for e in self._employees.values()]
            results = []
            for e in self._employees.values():
                hay_name = f"{e.get('first_name', '')} {e.get('last_name', '')}".strip().lower()
                hay_email = (e.get("email") or "").lower()
                if q in hay_name or q in hay_email:
                    results.append(dict(e))
            return results

    def get_employee(self, employee_id: int) -> Optional[Dict]:
        with self._lock:
            emp = self._employees.get(employee_id)
            return dict(emp) if emp else None

    def get_employee_by_email(self, email: str) -> Optional[Dict]:
        with self._lock:
            for e in self._employees.values():
                if e["email"].lower() == email.lower():
                    return dict(e)
            return None

    def create_employee(self, data: Dict) -> Dict:
        with self._lock:
            emp_id = next(self._employee_id_seq)
            data = dict(data)
            data["id"] = emp_id
            # Default safe values if fields missing
            data.setdefault("status", "ACTIVE")
            self._employees[emp_id] = data
            return dict(data)

    def update_employee(self, employee_id: int, updates: Dict) -> Dict:
        with self._lock:
            if employee_id not in self._employees:
                raise KeyError("Employee not found")
            existing = dict(self._employees[employee_id])
            existing.update({k: v for k, v in updates.items() if v is not None})
            self._employees[employee_id] = existing
            return dict(existing)

    def delete_employee(self, employee_id: int) -> None:
        with self._lock:
            self._employees.pop(employee_id, None)


# Module-level singleton
store = MockStore()
