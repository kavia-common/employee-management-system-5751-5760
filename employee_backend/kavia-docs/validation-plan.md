# Employee Backend Validation Plan

## 1. Overview and Scope
This Validation Plan defines the end-to-end strategy to verify and validate the Employee Management System backend (FastAPI + SQLAlchemy + Alembic). It ensures the solution meets enterprise quality attributes across security, performance, reliability, usability, maintainability, and compliance. The scope covers:
- REST API endpoints for authentication, employees CRUD, and dashboard metrics
- Database schema and migrations
- Cross-cutting middleware (CORS, correlation ID), logging, and configuration
- Automated unit, integration, contract, and E2E validations run in CI
Out of scope: Frontend-specific UX and external upstream systems beyond API contract adherence.

## 2. Validation Objectives Mapped to Quality Attributes
- Security: Password hashing, JWT issuance/verification, authorization checks on protected routes, error messages without sensitive leakage, CORS correctness.
- Performance: Pagination correctness, efficient queries, basic latency sanity checks for list endpoints.
- Reliability: Deterministic startup with migration handling, stable error handlers, resilient responses with correlation IDs.
- Usability: Predictable API shapes aligned to OpenAPI, consistent error envelopes, clear auth flows.
- Maintainability: Layered architecture (routers/services/repositories), DTO/schema segregation, standardized logging, testability and DI seams.
- Compliance: No secrets in code; environment-driven configuration; JSON-structured logs; consistent HTTP status usage.

## 3. Responsibility Matrix (RACI)
| Activity | API Lead | QA Lead | Dev Engineers | DevOps | Security |
|---|---|---|---|---|---|
| Validation plan ownership | A | R | C | C | C |
| Unit test implementation | C | C | R | I | I |
| Integration/contract tests | R | A | R | I | C |
| Security validation | C | C | C | I | A |
| Performance checks | C | A | R | C | I |
| CI/CD gate configuration | C | C | C | A | I |
| Sign-off | A | A | C | C | C |

Legend: R = Responsible, A = Accountable, C = Consulted, I = Informed

## 4. Test Taxonomy with Entry/Exit Criteria
- Unit (services, repositories, schemas, security utils)
  - Entry: Component APIs stable; test doubles available; local DB isolated.
  - Exit: All tests green; coverage targets met; boundaries validated.
- Integration (routers + DI + middleware)
  - Entry: Routes wired; TestClient usable.
  - Exit: Success and error paths verified; CORS, Vary and correlation headers validated.
- Contract (OpenAPI schema conformance)
  - Entry: OpenAPI available; response models specified on routes.
  - Exit: No diff for existing endpoints; valid shapes and status codes return.
- E2E (smoke via example spec)
  - Entry: Backend started; E2E env variables set.
  - Exit: Login flow green; redirects and token storage confirmed or simulated.
- Security
  - Entry: JWT secret supplied; bcrypt functional.
  - Exit: Unauthorized/forbidden paths behave correctly; no sensitive leakage; token claims verified.
- Performance (sanity)
  - Entry: List endpoints and DB seeded.
  - Exit: Pagination consistent; no pathological latencies or N+1 in current scope.

## 5. Validation Workflows (Step-by-Step)
- Environment and Config:
  1) Prepare .env with DATABASE_URL, JWT_SECRET, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, ENV, LOG_LEVEL.
  2) Start uvicorn at port 3002; verify logs structured and no plaintext secrets.
- Migrations and Schema:
  1) Run alembic upgrade head from a clean DB.
  2) Verify core tables (users, employees), indexes and constraints.
  3) Start API with empty DB to confirm startup migration attempt and safe error handling.
- Authentication:
  1) POST /auth/signup -> 201 (UserRead).
  2) POST /auth/login -> 200 (Token) and decode claims sub, iat, exp.
  3) Negative cases: duplicate signup -> 409; invalid login -> 401; /auth/me without token -> 401.
- Employees:
  1) With token, verify GET list pagination defaults; POST create -> 201; duplicate email -> 400.
  2) GET by id, PUT update, DELETE then confirm 404 on subsequent read.
  3) Validate search/department/status filters and pagination metadata.
- Dashboard:
  1) Seed 2+ departments; verify /dashboard/summary and /dashboard/department-stats counts.
  2) Verify 401 without token.
- CORS and Correlation:
  1) OPTIONS preflight to /auth/signup with allowed Origin -> 200/204 and allow headers set; Vary: Origin.
  2) POST /auth/login with Origin -> Access-Control-Allow-Origin echoed; X-Correlation-ID exposed and present.

## 6. Defect Severity/Priority Matrix and SLAs
| Severity | Definition | Example | Target SLA (Fix/Workaround) |
|---|---|---|---|
| Critical (S1) | System unusable or security breach | 500 on login; token leakage | Immediate hotfix; <24h |
| High (S2) | Major functionality broken; no workaround | Create employee fails consistently | Fix in next sprint; <3 business days |
| Medium (S3) | Functional degradation with workaround | Incorrect pagination edge behavior | Scheduled; <2 sprints |
| Low (S4) | Minor issues, docs, cosmetic | Log message typos | Backlog |

Priority aligns with severity unless business impact dictates escalation.

## 7. CI/CD Validation Gates (Automated)
- Install + Lint + Type checks (Python)
- Unit + Integration tests (pytest) with CI=true and isolated temp DBs
- Alembic migration validation (upgrade head on fresh DB artifact)
- OpenAPI contract check (generate/validate spec, ensure no drift)
- Security checks:
  - Ensure required envs are provided (JWT_SECRET non-empty for non-test)
  - No secrets detected in code
- Artifacts:
  - Publish coverage reports and OpenAPI spec
- Promotion rules:
  - Block on any test failures or migration errors
  - Optional manual gate for production with sign-off

## 8. Traceability Matrix (Requirements ↔ Tests ↔ Artifacts)
| Requirement | Tests | Artifacts/Modules |
|---|---|---|
| Auth: signup/login/me per contract | tests/test_auth.py, tests/test_login_token_contract.py | src/routers/auth.py, src/services/auth_service.py, src/schemas/user.py, interfaces/openapi.json |
| Employees CRUD + pagination/filtering | tests/test_employees.py | src/routers/employees.py, src/services/employee_service.py, src/repositories/employee_repository.py, src/schemas/employee.py |
| Dashboard summary & department stats | tests/test_dashboard.py | src/routers/dashboard.py, models |
| CORS + correlation headers | tests/test_auth.py, tests/test_cors_headers.py | src/api/main.py, src/middlewares/correlation.py |
| Health/docs availability | tests/test_docs_and_health.py | src/api/main.py, interfaces/openapi.json |
| Security: token claims & errors | tests/test_auth.py | src/core/security.py, auth_service |

## 9. Data Validation and Migration Checks
- Schema correctness: fields, constraints, enumerations (EmployeeStatus)
- Index/constraint presence: unique emails, department/status indices
- Migration idempotency: multiple upgrade runs safe; downgrade safe for dev
- Data migration (future): validate transforms with pre/post counts, sampling, and rollback plan

## 10. API Contract Validation and Negative Testing
- OpenAPI diff: compare current interfaces/openapi.json to generated schema; fail CI on breaking changes without version bump.
- Schema validation: ensure response_model declarations align with OpenAPI components.
- Negative tests: 401/403/404/409/422 handled with standardized envelope and no stack traces; verify Vary: Origin on errors.

## 11. Environmental Matrix (Dev/Stage/Prod)
| Aspect | Dev | Stage | Prod |
|---|---|---|---|
| DB | SQLite (default) | Managed Postgres | Managed Postgres |
| CORS | Fixed allowlist (dev origins) | Env-driven | Env-driven; strict |
| Seeding | Optional (ENV=development) | Disabled | Disabled |
| Logging | DEBUG/INFO | INFO | INFO/WARN; structured JSON |
| Secrets | .env local | Vault/Secrets Manager | Vault/Secrets Manager |
| TLS | Local HTTP | HTTPS via ingress | HTTPS |
| Host/Proxy middleware | Off (stability) | On | On |

Feature toggles: SEED_ON_STARTUP (dev), LOG_LEVEL, ACCESS_TOKEN_EXPIRE_MINUTES.

## 12. Risk Register and Mitigation
| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| CORS misconfiguration | Broken frontend integration | Medium | Externalize and validate CORS in stage/prod; regression tests |
| Secret mismanagement | Security incident | Low-Med | Enforce env-driven secrets; CI checks; rotate regularly |
| SQLite limitations | Migration surprises | Medium | Use Postgres in stage/prod; validate alembic there |
| Token clock skew | Auth failures | Low | Validate time sync; allow minimal skew in validation |
| Performance under load | UX degradation | Low | Add load tests for list endpoints; index review |

## 13. Acceptance Criteria and Sign-off
- All CI validation gates pass (tests, migrations, contract check)
- No Critical/High open defects
- Security controls verified (authZ/authN, no PII leakage, headers)
- OpenAPI is current and published
- Environment matrix implemented per environment
Sign-off: API Lead and QA Lead jointly approve before production promotion.

## 14. Appendices: Checklists, Templates, Commands

### Checklists
- Pre-merge: tests green, migrations valid, contract check passed
- Release: environment variables confirmed; secrets configured; monitoring dashboards prepared
- Security: JWT secret present; logs redaction verified; error messages generic

### Templates
- Defect report: Title, Severity, Priority, Environment, Steps, Expected, Actual, Logs (correlationId)
- Test case: ID, Title, Preconditions, Steps, Expected, Postconditions, References (requirement)

### Commands
- Run API (dev): uvicorn src.api.main:app --reload --host 0.0.0.0 --port 3002
- Run tests: CI=true pytest -q
- Migrations: alembic upgrade head
- OpenAPI docs: visit /docs; raw spec at /openapi.json

## References
- API entrypoint: src/api/main.py
- OpenAPI spec: interfaces/openapi.json
- Routers: src/routers/auth.py, src/routers/employees.py, src/routers/dashboard.py
- Schemas: src/schemas/user.py, src/schemas/employee.py
- Services: src/services/auth_service.py, src/services/employee_service.py
- Repositories: src/repositories/*
- Tests: tests/*
- README: employee_backend/README.md

