# Employee Backend [STUB]

This is a no-dependency stub backend for local development previews. It preserves the REST API structure but replaces business logic, database, and authentication with an in-memory mock store.

Key points:
- No database or ORM; all data is stored in memory for the process lifetime.
- No real authentication; login returns a deterministic fake token.
- CORS enabled for http://localhost:3000.
- OpenAPI docs clearly mark endpoints as [STUB] via descriptions/tags.

Run locally:
uvicorn app.main:app --host 0.0.0.0 --port 3001

Endpoints:
- GET /health
- POST /auth/signup
- POST /auth/login
- POST /auth/logout
- GET /employees?page=<int>&page_size=<int>&q=<string>
- POST /employees
- GET /employees/{id}
- PUT /employees/{id}
- DELETE /employees/{id}

Notes:
- The data resets on server restart.
- No environment variables are required.
- This stub is intended for UI development and contract validation only. Do not use in production.
