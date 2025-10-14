# Employee Backend Validation Plan

## Overview

This Validation Plan defines the end-to-end approach to verify and validate the Employee Management System backend (FastAPI + SQLAlchemy + Alembic) for functionality, security, reliability, and maintainability. It consolidates the testing strategy, detailed validation procedures, and checklists to ensure adherence to enterprise engineering standards. The plan is kept in sync with the codebase and references the implemented routes, services, middleware, configuration, and automated tests present in the repository.

## Scope

This plan covers the backend container only (employee_backend). It includes REST API endpoints for authentication, employee CRUD operations, and dashboard metrics; database schema and migrations; configuration and environment handling; CORS and correlation middleware; logging; and automated tests. The frontend and any external systems are out of scope beyond API integration expectations documented by OpenAPI.

## Objectives

- Validate that all API endpoints function per contract (OpenAPI schema and implemented routers).
- Confirm that security controls (password hashing, JWT handling, input validation) are robust and align with enterprise standards.
- Ensure CORS behavior and correlation ID propagation are consistent across success and failure cases.
- Verify database schema and migrations are stable, repeatable, and aligned with ORM models.
- Establish automated, repeatable testing with meaningful coverage of business logic, error handling, and boundary conditions.
- Provide clear acceptance criteria and checklists suitable for CI/CD gating.

## References

- API entrypoint and middleware: src/api/main.py
- Security utilities (bcrypt/jwt): src/core/security.py
- Configuration and logging: src/core/config.py, src/core/logging_config.py
- ORM models and DB config: src/models/*.py, src/db/base.py, src/db/session.py
- Migrations: alembic/env.py, alembic/versions/0001_init.py
- Routers: src/routers/auth.py, src/routers/employees.py, src/routers/dashboard.py
- Services/Repositories: src/services/*, src/repositories/*
- OpenAPI: interfaces/openapi.json
- Tests: tests/*.py
- Backend README with operational guidance: employee_backend/README.md

## Testing Strategy

### Test Types

1. Unit Tests
   - Validate services and repositories in isolation (business logic, error pathways, uniqueness constraints).
   - Focus on input validation (e.g., pydantic schemas), token creation/decoding, and password hashing verification.
   - Example coverage: src/services/*.py, src/repositories/*.py, src/core/security.py, src/schemas/*.py.

2. API/Integration Tests
   - Use FastAPI TestClient to verify routers, dependency injection, middleware behaviors, and standardized error responses.
   - Cover happy-path and failure-path scenarios for:
     - Authentication: /auth/signup, /auth/login, /auth/me
     - Employees: list, create, get, update, delete with pagination and filters
     - Dashboard: /dashboard/summary, /dashboard/department-stats
     - Health and docs: /, /healthz, /docs, /openapi.json

3. Database Migration Validation
   - Confirm alembic upgrade head is successful starting from an empty database.
   - Validate schema consistency with ORM models (indexes, constraints, enums, and relationships).
   - Ensure rollback safety for development (downgrade) and reproducibility in CI.

4. Security Testing
   - Password hashing/verification self-test (already implemented in startup path).
   - JWT token issuance and claim validation (sub, iat, exp) with invalid token handling.
   - Authorization gates on protected endpoints returning 401/403 as appropriate.
   - Input validation of schemas, avoiding injection vectors via ORM parameterization and pydantic constraints.
   - Logging excludes sensitive data and includes correlation IDs.

5. CORS and Cross-Cutting Concerns
   - Confirm fixed CORS allow-list works for preview/local origins.
   - Check Vary: Origin added to all responses; Access-Control-Expose-Headers includes X-Correlation-ID.
   - Verify fallback OPTIONS route behavior for preflights.

6. Non-Functional Testing (selective)
   - Basic performance sanity via pagination for employee lists.
   - Resilience on startup: auto-migration attempt when core tables missing and safe error handling if DB unavailable.
   - Logging format and correlation ID injection.

### Environments

- Local/Dev: SQLite (file-based), uvicorn reload, hardcoded CORS origins (as per code), optional seed on startup in development.
- CI: SQLite temporary file DB created per test via fixtures; environment variables provided by tests/conftest.py.
- Higher Environments (staging/prod): RDBMS recommended; disable seeding; prefer env-driven CORS and trusted host middleware reintroduction; HTTPS termination; secrets from secure vault.

### Tooling and Frameworks

- Python 3.11+
- FastAPI, SQLAlchemy 2.x, Alembic
- Pytest for automated testing
- Passlib[bcrypt], python-jose for auth
- TestClient for API-level tests

## Validation Procedures

### 1) Environment and Configuration Validation

Procedure:
- Ensure .env is configured per README with DATABASE_URL, JWT_SECRET, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, ENV, LOG_LEVEL.
- Verify startup does not crash on missing JWT_SECRET in non-test contexts; confirm conftest.py sets JWT_SECRET for tests.
- Confirm logging outputs JSON with correlationId and without sensitive data.

Acceptance:
- Application starts with uvicorn on port 3002 without stack traces due to configuration errors.
- logs contain keys: timestamp, level, message, logger, env, correlationId.

Sources:
- src/core/config.py
- src/core/logging_config.py
- employee_backend/README.md
- tests/conftest.py

### 2) Database and Migrations Validation

Procedure:
- From a clean environment, run alembic upgrade head.
- Confirm users and employees tables exist with indexes and constraints.
- Validate enum employee_status creation and compatibility (on dialects supporting enums).
- In app startup, simulate missing core tables and confirm auto-migration attempt logs and safe behavior.

Acceptance:
- alembic upgrade head completes successfully.
- Tables and indexes present: ix_users_email, ix_employees_email, ix_employees_department, ix_employees_status; unique constraints on emails.
- No unhandled exceptions on startup when DB is unavailable; standardized error responses for operational errors.

Sources:
- alembic/env.py
- alembic/versions/0001_init.py
- src/api/main.py (startup migration helper)
- src/db/base.py, src/db/session.py

### 3) Authentication Validation

Procedure:
- POST /auth/signup with new email; expect 201 and JSON UserRead without sensitive fields.
- POST /auth/signup with duplicate email; expect 409 with standardized error envelope and correlation header.
- POST /auth/login with valid credentials; expect 200 with Token schema including non-empty access_token and token_type bearer. Validate token claims (sub, iat, exp).
- POST /auth/login with invalid credentials; expect 401 standardized error.
- GET /auth/me with valid Bearer token; expect 200 with correct user.
- GET /auth/me without token; expect 401 standardized error.

Acceptance:
- Tokens decode with expected claims and authorize protected endpoints.
- All error paths return JSON envelope {error: {code, message, correlationId}} and include X-Correlation-ID header.

Sources:
- src/routers/auth.py
- src/services/auth_service.py
- src/core/security.py
- tests/test_auth.py, tests/test_login_token_contract.py

### 4) Employee CRUD Validation

Procedure:
- Authenticate and obtain token.
- GET /employees empty list; verify pagination defaults page=1 size=10 and total=0.
- POST /employees to create record; validate response model matches EmployeeRead.
- POST duplicate email; expect 400 error envelope.
- GET /employees/{id} returns created record; subsequent GET after delete returns 404.
- PUT /employees/{id} update selected fields; verify changes persisted.
- GET /employees with search, department, status filters; verify pagination metadata and filter effectiveness.

Acceptance:
- Uniqueness enforced on email with graceful error handling.
- Pagination and search behave as specified in README and OpenAPI.
- Protected endpoints return 401 without token.

Sources:
- src/routers/employees.py
- src/services/employee_service.py
- src/repositories/employee_repository.py
- src/schemas/employee.py
- tests/test_employees.py

### 5) Dashboard Validation

Procedure:
- Seed or insert sample employees.
- GET /dashboard/summary returns total, active, inactive counts.
- GET /dashboard/department-stats returns array of department counts excluding nulls.
- Both endpoints require Bearer token.

Acceptance:
- Counts match seeded data; unauthorized requests receive 401.

Sources:
- src/routers/dashboard.py
- tests/test_dashboard.py

### 6) CORS and Correlation Validation

Procedure:
- OPTIONS preflight to /auth/signup with allowed origin; expect 200/204 with Access-Control-Allow-* headers plus Vary: Origin.
- POST /auth/signup and /auth/login with allowed Origin; verify Access-Control-Allow-Origin echoes Origin; Access-Control-Expose-Headers includes X-Correlation-ID; Vary: Origin always present.
- Validate that Vary: Origin is present on responses even when Origin is not supplied.
- Confirm X-Correlation-ID header present on success and error responses.

Acceptance:
- CORS headers behavior matches code’s fixed allowlist and middleware safety nets.
- Correlation IDs propagated consistently.

Sources:
- src/api/main.py (CORS config, fallback OPTIONS, common header application)
- src/middlewares/correlation.py
- tests/test_auth.py, tests/test_cors_headers.py

### 7) Health and Documentation

Procedure:
- GET /, /healthz return 200 and include Vary: Origin and X-Correlation-ID headers.
- GET /docs and /openapi.json return successfully and are consistent with router definitions.

Acceptance:
- Swagger UI and OpenAPI load without errors.
- Health endpoints behave as specified.

Sources:
- src/api/main.py
- tests/test_docs_and_health.py
- interfaces/openapi.json

## Test Data Management

- For unit/integration tests, use temporary SQLite DB files created per test module/function (see pytest fixtures) to ensure isolation and repeatability.
- Seed data for local development is optional and guarded by ENV and SEED_ON_STARTUP; must remain disabled in production.

## Entry/Exit Criteria

Entry:
- Dependencies installed from requirements.txt.
- Environment variables configured (tests configure minimal secure defaults).

Exit:
- All automated tests in tests/ pass in CI (pytest), including auth, employees, dashboard, docs, health, CORS.
- OpenAPI matches implemented endpoints; no mismatches found in smoke verification.
- Migrations apply cleanly from scratch.

## Risk Assessment and Mitigations

- Risk: CORS misconfiguration in production due to fixed allowlist.
  - Mitigation: Re-enable env-driven CORS and TrustedHost/ProxyHeaders middleware prior to production release; include separate validation for those paths.
- Risk: SQLite limitations for advanced schema changes.
  - Mitigation: Use full RDBMS in higher environments; validate migrations on staging DB.
- Risk: Secret misconfiguration.
  - Mitigation: Enforce non-placeholder JWT_SECRET in non-test contexts; CI checks can verify presence.

## Validation Checklist

Environment and Config
- [ ] .env configured (DATABASE_URL, JWT_SECRET, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, ENV, LOG_LEVEL)
- [ ] Logging emits JSON with correlationId and no sensitive data
- [ ] Application starts on port 3002 without configuration errors

Database and Migrations
- [ ] alembic upgrade head succeeds from clean state
- [ ] Tables and indexes/constraints created as expected
- [ ] Startup handles missing tables by attempting migration and logging outcomes

Authentication
- [ ] /auth/signup 201 returns UserRead without sensitive fields
- [ ] Duplicate /auth/signup returns 409 with error envelope and correlation header
- [ ] /auth/login returns bearer token with valid JWT claims
- [ ] Invalid credentials return 401 with standardized error
- [ ] /auth/me returns user details with valid token; 401 without token

Employee CRUD
- [ ] Listing returns pagination with defaults page=1, size=10
- [ ] Create returns 201 and EmployeeRead; duplicate email -> 400 error envelope
- [ ] Get/Update/Delete flows function and persist data
- [ ] Filters (search, department, status) work and return correct totals

Dashboard
- [ ] /dashboard/summary reflects counts by status
- [ ] /dashboard/department-stats returns department aggregates, excluding nulls
- [ ] Unauthorized access returns 401

CORS and Correlation
- [ ] OPTIONS preflight handled with correct CORS headers
- [ ] Vary: Origin present on all responses
- [ ] Access-Control-Allow-Origin echoes allowed Origin
- [ ] Access-Control-Expose-Headers contains X-Correlation-ID
- [ ] X-Correlation-ID header present on success and error responses

Health and Documentation
- [ ] /, /healthz return 200 with expected headers
- [ ] /docs and /openapi.json accessible and consistent

## CI/CD Integration

- Execute pytest with CI settings; ensure non-interactive runs and isolated temp DBs.
- Gate merges on all tests passing and linting success where applicable.
- Optional: Add a job to validate alembic migrations (upgrade head) against a fresh database artifact.
- Optional: Include OpenAPI generation verification (src/api/generate_openapi.py) to detect drift.

## Traceability to Codebase

- Authentication services and routers are validated by tests/test_auth.py and tests/test_login_token_contract.py against src/routers/auth.py and src/services/auth_service.py.
- Employee CRUD is validated by tests/test_employees.py against src/routers/employees.py, src/services/employee_service.py, and src/repositories/employee_repository.py.
- Dashboard endpoints are validated by tests/test_dashboard.py against src/routers/dashboard.py.
- CORS and correlation behaviors validated by tests/test_cors_headers.py and tests/test_auth.py against src/api/main.py and src/middlewares/correlation.py.
- Health and docs coverage in tests/test_docs_and_health.py.

## Future Enhancements

- Reintroduce environment-driven CORS, TrustedHost, and ProxyHeaders middleware with corresponding validation in staging/prod.
- Add load testing scenarios for listing endpoints with pagination.
- Extend security testing for token expiry handling and clock skew.
- Add database-level tests for more dialects (e.g., PostgreSQL) for enum lifecycle and constraints.

