# employee-management-system-5751-5760

Backend workspace for the Employee Management System.

- Container root: `employee_backend/`
- Tech: FastAPI, SQLAlchemy, Alembic

Quick steps:
1) cd `employee_backend`
2) Create venv and `pip install -r requirements.txt`
3) Copy `.env.example` to `.env`, set:
   - DATABASE_URL (e.g., `sqlite:///./employees.db` for dev)
   - JWT_SECRET
   - ENV=development, LOG_LEVEL=INFO

Note: CORS is hardcoded to allow:
- `https://vscode-internal-19668-beta.beta01.cloud.kavia.ai:3000`
- `http://localhost:3000`
These ensure preflight and actual requests from the preview/local frontend succeed. For production, migrate to env-driven CORS.
4) Run migrations: `alembic upgrade head`
5) Start API: `uvicorn src.api.main:app --reload --port 3001`

OpenAPI docs: http://localhost:3001/docs

See `employee_backend/README.md` for full documentation and smoke tests.
