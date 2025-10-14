# Employee Backend - FastAPI + SQLAlchemy + Alembic

This backend exposes a REST API for authentication, employee CRUD, and dashboard statistics. It uses SQLAlchemy (ORM) and Alembic (schema migrations) with environment-driven configuration.

## Prerequisites

- Python 3.11+
- Virtual environment recommended

## Quick Start

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

5) Start the API locally (port 3001):
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
- CORS_ORIGINS (e.g., `http://localhost:3000`)
- LOG_LEVEL (e.g., `INFO`)
- ENV (`development` | `production`), default `development`

See `.env.example` for a template.

### CORS Configuration

CORS is configured in `src/api/main.py` with this fixed middleware ordering:
- CORSMiddleware -> Correlation middleware -> Routers
  (TrustedHostMiddleware and ProxyHeadersMiddleware temporarily removed to stabilize startup)

Effective configuration (hardcoded as requested):
- Allowed origins:
  - `https://vscode-internal-19668-beta.beta01.cloud.kavia.ai:3000`
  - `http://localhost:3000`
- Allow credentials: `true`
- Allowed methods: `GET, POST, PUT, DELETE, PATCH, OPTIONS`
- Allowed headers: `Authorization, Content-Type, X-Correlation-ID, X-Requested-With`
- Exposed headers: `X-Correlation-ID`
- `Vary: Origin` is added to all responses.
- A minimal safety-net route (`OPTIONS /{path:path}`) returns 200 with proper CORS headers for allowed origins (including `/auth/signup`).

Verification steps:
1) Start API: `uvicorn src.api.main:app --reload --host 0.0.0.0 --port 3001`
2) Preflight:
   ```
   curl -i -X OPTIONS http://localhost:3001/auth/signup \
     -H "Origin: https://vscode-internal-19668-beta.beta01.cloud.kavia.ai:3000" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: content-type,authorization,x-correlation-id"
   ```
   Expect:
   - `HTTP/1.1 200 OK` (or 204 from CORS middleware)
   - `Access-Control-Allow-Origin` with the same Origin
   - `Access-Control-Allow-Methods` includes POST
   - `Access-Control-Allow-Headers` includes Authorization, Content-Type, X-Correlation-ID
   - `Access-Control-Allow-Credentials: true`
   - `Vary: Origin`
3) Actual request:
   ```
   curl -i -X POST http://localhost:3001/auth/signup \
     -H "Origin: https://vscode-internal-19668-beta.beta01.cloud.kavia.ai:3000" \
     -H "Content-Type: application/json" \
     -d '{"email":"user@example.com","password":"StrongPass123"}'
   ```
   Expect:
   - 201 (first time) or 400 if already exists
   - `Access-Control-Allow-Origin` matches Origin
   - `Access-Control-Expose-Headers` includes `X-Correlation-ID`
   - `Vary: Origin`

Notes:
- For production, consider re-adding `TrustedHostMiddleware` and `ProxyHeadersMiddleware` with environment-driven configuration once startup/runtime conflicts are addressed.
- Make sure your frontend uses the exact Origin (scheme + host + port) listed in allowed origins.

TODO:
- For production, move CORS allowlist back to environment-driven configuration and set appropriate trusted hosts.

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
  - Set `CORS_ORIGINS=http://localhost:3000` for local runs
  - Or add your preview frontend URL
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

## Troubleshooting

- Backend won't start (uvicorn import error):
  - Ensure you run from the `employee_backend` directory:
    ```
    cd employee_backend
    uvicorn src.api.main:app --reload --host 0.0.0.0 --port 3001
    ```
  - Confirm Python dependencies: `pip install -r requirements.txt`
  - If there were local edits to `src/api/main.py`, verify there are no syntax errors and that middleware `add_middleware` calls do not pass invalid parameters.
- If imports fail during Alembic operations, ensure you invoke Alembic from the `employee_backend` directory so `src/` is correctly added to `PYTHONPATH` by `alembic/env.py`.
- For SQLite, schema changes like dropping enums or certain constraints may be limited; migrate carefully or use a full RDBMS in higher environments.
- If you see CORS errors in the browser, verify `CORS_ORIGINS` matches exactly your frontend URL (scheme + host + port), or rely on the built-in defaults (preview + localhost).
- If tokens appear to expire prematurely, verify server/system time and `ACCESS_TOKEN_EXPIRE_MINUTES`.
