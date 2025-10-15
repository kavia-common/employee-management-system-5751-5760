# Employee Backend [STUB] - Preview Connectivity Notes

This is a stubbed FastAPI backend intended for frontend preview and integration without database/auth dependencies.

Key behavior:
- CORS: allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"], expose_headers=["X-Correlation-ID"]
- Health: GET /health returns {"status":"ok"}
- Docs: /docs
- Routers: /auth (signup, login, logout, me), /employees (list/create/read/update/delete)
- Errors: standardized JSON envelope {"error":{"code": <int>, "message": "<str>", "correlationId": "<uuid>"}}

Run locally:
- uvicorn app.main:app --host 0.0.0.0 --port 3001
- The app also includes a __main__ guard that binds to 0.0.0.0:3001 by default if launched as a script.

Frontend preview defaults:
- Point API base to http://localhost:3001 (or override with window.__API_BASE__ / REACT_APP_API_BASE if available).

Acceptance checks:
- GET http://localhost:3001/health -> 200 {"status":"ok"}
- /docs loads
- Preflight OPTIONS and CRUD from http://localhost:3000 succeed (wildcard CORS enabled).

Notes:
- This stub avoids any DB drivers or environment dependencies.
- Email validation is minimal (string type) to keep requirements small.
