# Startup & Auth Troubleshooting

This guide documents common startup/import issues and 500s on /auth/signup, with reproduction commands and concrete fixes.

## Symptoms

- 500 Internal Server Error on `POST /auth/signup`
- Server fails to start or crashes during import

Example stack trace observed during reproduction:

```
Traceback (most recent call last):
  File "run.py", line 34, in main
    uvicorn.run("src.api.main:app", host=host, port=port, reload=False)
  ...
  File "src/core/security.py", line 18, in <module>
    from jose import jwt
ModuleNotFoundError: No module named 'jose'
```

Root cause: Missing Python dependencies (e.g., `python-jose`) in the runtime environment.

## Reproduction

Run the backend (port 3001) and reproduce the auth calls:

- Signup
  ```
  curl -s -X POST 'http://localhost:3001/auth/signup' \
    -H 'accept: application/json' -H 'Content-Type: application/json' \
    -d '{"email":"test@example.com","full_name":"Test User","password":"TestPass123!"}' -v
  ```

- Login
  ```
  curl -s -X POST 'http://localhost:3001/auth/login' \
    -H 'accept: application/json' -H 'Content-Type: application/json' \
    -d '{"email":"test@example.com","password":"TestPass123!"}' -v
  ```

- Me (replace <TOKEN> from login)
  ```
  curl -s -H "Authorization: Bearer <TOKEN>" 'http://localhost:3001/auth/me' -v
  ```

- Health
  ```
  curl -s 'http://localhost:3001/health' -v
  ```

Expected:
- `POST /auth/signup`: 201 with user info on first call, 409 on duplicate; never 500
- `POST /auth/login`: 200 with `{"access_token":"...", "token_type":"bearer"}`
- `GET /auth/me`: 200 with user info when valid Bearer token provided; 401 otherwise
- `GET /health`: 200 with `{"status":"ok"}`

## Fixes

1) Install Dependencies
- Always install from `requirements.txt` in this folder:
  ```
  pip install --no-input --disable-pip-version-check -r requirements.txt
  ```
- This includes:
  - `python-jose[cryptography]==3.3.0` for JWT encode/decode
  - `passlib[bcrypt]==1.7.4` and pinned `bcrypt==3.2.2` for password hashing
  - `email-validator` for Pydantic's `EmailStr`

2) Database & Migrations
- The app uses `DATABASE_URL` (defaults to `sqlite:///./employees.db`).
- On startup, the app attempts to detect missing core tables and run `alembic upgrade head`.
- You can run migrations manually as well:
  ```
  alembic upgrade head
  ```
- If connecting to Postgres/MySQL, set `DATABASE_URL` accordingly and ensure network access and credentials are correct.

3) Password Hashing Self-Test
- On startup, logs include a self-test:
  - `Password hashing self-test passed (bcrypt available).`
- If this fails, ensure `passlib[bcrypt]` and `bcrypt==3.2.2` are installed:
  ```
  pip install 'passlib[bcrypt]==1.7.4' 'bcrypt==3.2.2'
  ```

4) JWT Secret
- For local dev, a placeholder secret is allowed to avoid import failures.
- For staging/production, set a strong `JWT_SECRET` in environment or `.env`.
- See `.env.example` for a template.

5) Ports and Service Presence
- If you see:
  ```
  [Errno 98] error while attempting to bind on address ('0.0.0.0', 3001): address already in use
  ```
  it means a backend is already running on port 3001. Proceed to test endpoints directly; do not try to start another instance on the same port.

## Acceptance Criteria Verified

- Signup returns 201 on first run and 409 on duplicate; no 500
- Login returns 200 with `access_token` and `token_type="bearer"`
- Me returns 200 with proper user info when authorized; 401 otherwise
- Health returns `{"status":"ok"}` on port 3001

## Notes on CORS & Error Envelope

- CORS is configured to cover preview and localhost origins. Headers include `Vary: Origin` and expose `X-Correlation-ID`.
- Error responses use a consistent envelope:
  ```
  {"error": {"code": <int>, "message": "<string>", "correlationId": "<uuid>"}}
  ```
  This applies to 401/409/422/500, ensuring frontend can surface errors cleanly.
