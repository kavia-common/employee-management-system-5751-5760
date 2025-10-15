# Employee Backend - FastAPI + SQLAlchemy + Alembic

This backend exposes a REST API for authentication, employee CRUD, and dashboard statistics. It uses SQLAlchemy (ORM) and Alembic (schema migrations) with environment-driven configuration.

## Prerequisites

- Python 3.11+
- Virtual environment recommended

## Quick Start

Note on seed data:
- In development, the backend can optionally seed a few sample Employees on startup if the table is empty.
- Control via environment variable:
  - ENV=development enables seeding by default
  - Set SEED_ON_STARTUP=false to disable
  - In production, do not enable seeding.

1) Create and activate a virtual environment:
   - macOS/Linux:
     ```
     python3 -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     py -3 -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

2) Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3) Configure environment:
   - Copy `.env.example` to `.env`
   - Set values as needed for your environment
   - For local development, defaults use SQLite at `sqlite:///./employees.db`

4) Run database migrations:
   ```
   alembic upgrade head
   ```
   Note: The application attempts to auto-run Alembic migrations on startup if core tables are missing. Still, prefer running migrations explicitly as part of deployment pipelines.

5) Start the API locally (preview expects port 3001):
   - Using helper launcher:
     ```
     python run.py
     ```
   - Or directly with uvicorn:
     ```
     uvicorn src.api.main:app --reload --host 0.0.0.0 --port 3001
     ```
   - OpenAPI docs: http://localhost:3001/docs

## Environment Variables

These are read from the environment and `.env` for local dev:

- DATABASE_URL (e.g., `sqlite:///./employees.db` for dev)
- JWT_SECRET (required; set a secure random value)
- JWT_ALGORITHM (default: `HS256`)
- ACCESS_TOKEN_EXPIRE_MINUTES (e.g., `60`)
- ALLOWED_ORIGINS (comma-separated or JSON array; e.g., `https://vscode-internal-23063-beta.beta01.cloud.kavia.ai:3000,http://localhost:3000`)
  - Backward-compat: `CORS_ORIGINS` is also recognized if `ALLOWED_ORIGINS` is not set
- LOG_LEVEL (e.g., `INFO`)
- ENV (`development` | `production`), default `development`
- SEED_ON_STARTUP (`true`|`false`): in development only, seed sample employees if table is empty (default: true in development)

See `.env.example` for a template.

### CORS Configuration

CORS is configured in `src/api/main.py` with this middleware ordering:
- CORSMiddleware -> Correlation middleware -> Routers

Configuration:
- Allowed origins (from env):
  - `ALLOWED_ORIGINS` (comma-separated or JSON array). Default when not set:
    - `https://vscode-internal-23063-beta.beta01.cloud.kavia.ai:3000`
    - `http://localhost:3000`
- Allow credentials: `true`
- Allowed methods: `*` (all)
- Allowed headers: `*` (all; including `Authorization`, `Content-Type`)
- Exposed headers: `X-Correlation-Id` (both `X-Correlation-ID` and `X-Correlation-Id` are included)
- `Vary: Origin` is added to all responses.
- Preflight OPTIONS requests are handled for all routes (including `/auth/*`) without authentication:
  - CORSMiddleware intercepts preflight automatically
  - A minimal safety-net `OPTIONS /{path:path}` route reflects requested method/headers to ensure compliant responses if routing is reached

Verification steps:
1) Start API: `uvicorn src.api.main:app --reload --host 0.0.0.0 --port 3001`
2) Preflight (example for preview on 3000; adjust host/port as needed):
   ```
   curl -i -X OPTIONS http://localhost:3001/auth/signup \
     -H "Origin: https://vscode-internal-23063-beta.beta01.cloud.kavia.ai:3000" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: content-type,authorization,x-correlation-id"
   ```
   Expect:
   - `HTTP/1.1 200 OK` (or 204 from CORS middleware)
   - `Access-Control-Allow-Origin` with the same Origin
   - `Access-Control-Allow-Methods` includes OPTIONS and the requested method
   - `Access-Control-Allow-Headers` reflects requested headers
   - `Access-Control-Allow-Credentials: true`
   - `Vary: Origin`
3) Actual request:
   ```
   curl -i -X POST http://localhost:3001/auth/signup \
     -H "Origin: https://vscode-internal-23063-beta.beta01.cloud.kavia.ai:3000" \
     -H "Content-Type: application/json" \
     -d '{"email":"user@example.com","password":"StrongPass123"}'
   ```
   Expect:
   - 201 (first time) or an error (e.g., 409 if already exists)
   - `Access-Control-Allow-Origin` matches Origin
   - `Access-Control-Expose-Headers` includes `X-Correlation-Id`
   - `Vary: Origin`
   - On error responses (e.g., 400/401/409/422/500) the same CORS headers are present, due to centralized handlers.

Notes:
- Make sure your frontend uses the exact Origin (scheme + host + port) included in `ALLOWED_ORIGINS`.
- For production, set `ALLOWED_ORIGINS` explicitly. The defaults are only for preview/local development.

## Migrations

Alembic is preconfigured. Common commands (run from `employee_backend` folder):

- Show current heads:
  ```
  alembic heads
  ```

- Generate a new migration (autogenerate based on model changes):
  ```
  alembic revision --autogenerate --message "some message"
  ```

- Apply migrations to latest:
  ```
  alembic upgrade head
  ```

- Downgrade (undo last migration):
  ```
  alembic downgrade -1
  ```

Notes:
- The Alembic environment (`alembic/env.py`) reads `DATABASE_URL` from `.env`.
- Models live under `src/models/` and share a common base in `src/db/base.py`.
- Use `get_db` from `src/db/session.py` as a FastAPI dependency to obtain a request-scoped DB session.

## API Surface (High-Level)

- Health: `GET /`
- Auth:
  - `POST /auth/signup`
  - `POST /auth/login`
  - `GET /auth/me` (Bearer)
- Employees (Bearer):
  - `GET /employees` with `page`, `size`, `search?`, `department?`, `status?`
  - `POST /employees`
  - `GET /employees/{id}`
  - `PUT /employees/{id}`
  - `DELETE /employees/{id}`
- Dashboard (Bearer):
  - `GET /dashboard/summary`
  - `GET /dashboard/department-stats`

## Integration Checklist

- Ensure backend CORS allows your frontend origin:
  - Set `ALLOWED_ORIGINS` (defaults already include preview 3000 and localhost 3000)
- Ensure frontend points to backend:
  - In frontend `.env.local`, set `REACT_APP_API_BASE_URL` to the backend URL (e.g., `http://localhost:3001`)
- Run migrations before first start:
  - `alembic upgrade head`

## Smoke Tests (End-to-End)

After both containers are running:

1) Sign up
   - POST `/auth/signup` from Swagger UI or via frontend signup form
   - Expect 201 and returned user object (no sensitive fields)

2) Login
   - POST `/auth/login` with the same credentials
   - Expect 200 and a bearer `access_token`
   - Frontend should store token and navigate to `/dashboard`

3) Employees
   - Create a new employee via UI or `POST /employees`
   - List employees (with pagination/search)
   - View detail, update, and delete
   - Confirm list reflects changes

4) Dashboard
   - Open `/dashboard`
   - Verify summary counts and department stats are returned

5) Auth and CORS
   - Confirm protected endpoints return 401 without token
   - Confirm no CORS errors in browser console
   - Confirm 401 handling logs out client and redirects to `/login`

## Security

- Never store plaintext passwords; `User.password_hash` contains a salted hash (bcrypt).
- Never log sensitive data (passwords, tokens, PII).
- Credentials and connection strings MUST be set via environment variables, not hardcoded.
- Use HTTPS in production.
