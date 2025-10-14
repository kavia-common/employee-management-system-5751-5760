# Employee Backend - Database Layer (SQLAlchemy + Alembic)

This backend uses SQLAlchemy (ORM) and Alembic (schema migrations) with environment-driven configuration.

## Prerequisites

- Python 3.11+
- Virtual environment recommended

## Setup

1. Create and activate a virtual environment:
   - macOS/Linux:
     ```
     python3 -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     py -3 -m venv .venv
     .\\.venv\\Scripts\\Activate.ps1
     ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Configure environment:
   - Copy `.env.example` to `.env`
   - Adjust `DATABASE_URL`, `DB_POOL_SIZE`, and `DB_MAX_OVERFLOW` as needed
   - Default uses SQLite at `sqlite:///./employees.db` for local dev

## Migrations

Alembic is preconfigured. Common commands (run from `employee_backend` folder):

- Show current heads:
  ```
  alembic heads
  ```

- Generate a new migration (autogenerate based on model changes):
  ```
  alembic revision --autogenerate -m "some message"
  ```

- Apply migrations to latest:
  ```
  alembic upgrade head
  ```

- Downgrade (undo last migration):
  ```
  alembic downgrade -1
  ```

## Notes

- The Alembic environment (`alembic/env.py`) reads `DATABASE_URL` from `.env`.
- Models live under `src/models/` and share a common base in `src/db/base.py`.
- Use `get_db` from `src/db/session.py` as a FastAPI dependency to obtain a request-scoped DB session.

## Security

- Never store plaintext passwords; `User.password_hash` must contain a salted hash (e.g., bcrypt).
- Never log sensitive data (passwords, tokens, PII).
- Credentials and connection strings MUST be set via environment variables, not hardcoded.

## Troubleshooting

- If imports fail during Alembic operations, ensure you invoke Alembic from the `employee_backend` directory so `src/` is correctly added to `PYTHONPATH` by `alembic/env.py`.
- For SQLite, schema changes like dropping enums or certain constraints may be limited; migrate carefully or use a full RDBMS in higher environments.
