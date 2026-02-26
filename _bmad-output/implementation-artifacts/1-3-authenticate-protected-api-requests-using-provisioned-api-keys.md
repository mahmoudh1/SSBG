# Story 1.3: Authenticate Protected API Requests Using Provisioned API Keys

Status: done

## Story

As an operator or administrator,
I want protected API requests authenticated,
so that only valid credentials can access SSBG operations.

## Acceptance Criteria

1. Given a protected endpoint request without credentials, when the request is processed, then the API returns an authentication error and non-success HTTP status.
2. Given an invalid, expired, or revoked API key, when a protected endpoint is called, then access is denied and an auditable failure event is generated.
3. Given a valid API key, when a protected endpoint is called, then request processing continues to authorization/policy checks.

## Tasks / Subtasks

- [x] Implement API key auth middleware/dependency using `X-API-Key` header (AC: 1, 2, 3)
- [x] Add API key repository/model validation flow (invalid/revoked/expired) (AC: 2, 3)
- [x] Hash key material at rest and avoid raw secret leakage (AC: 2)
- [x] Emit auditable auth failure events (AC: 2)
- [x] Return documented auth error envelope on failures (AC: 1, 2)
- [x] Add tests for missing/invalid/revoked/expired/valid key flows (AC: 1, 2, 3)

## Dev Notes

### Scope

Authentication only. Successful auth should establish request/principal context and hand off to authorization/policy logic; do not implement RBAC/policy decisions in this story.

### Architecture Guardrails

- Security order: Auth -> MFA (when required) -> Authorization/Policy -> handler
- Keep auth enforcement centralized in middleware/dependencies, not repeated in routes
- Fail-secure on repository/dependency errors (deny, do not allow)
- Use shared error envelope (`error.code`, `message`, `details`, `correlation_id`)
- Do not leak raw key values in logs/errors/audit payloads

### Likely Files

- `app/api/middleware/auth.py` and/or `app/api/dependencies.py`
- `app/services/auth_service.py`
- `app/repositories/api_keys_repository.py`
- `app/infrastructure/db/models/api_key.py`
- `app/schemas/auth.py`
- `app/services/audit_service.py`
- `tests/unit/services/test_auth_service.py`
- `tests/integration/api/test_authentication.py`

### Testing Requirements

- Missing credential -> auth error + non-success status
- Invalid/expired/revoked key -> denied + audit event
- Valid key -> request reaches downstream dependency/handler
- Repository failure -> denied (fail-secure)
- Error response contract remains stable

### Previous Story / Git Intelligence

- Reuse Story 1.1 scaffold and Story 1.2 response/error conventions
- No `.git` repository detected; git intelligence unavailable

### Latest Tech Information (researched 2026-02-26)

- FastAPI PyPI latest observed: `0.133.1`
- SQLAlchemy PyPI latest observed: `2.0.47`
- Alembic PyPI latest observed: `1.18.4`
- Pydantic PyPI latest observed: `2.12.5`
- `pydantic-settings` PyPI latest observed: `2.13.1`

### References

- `_bmad-output/planning-artifacts/epics-and-stories/epic-1-provision-and-secure-the-ssbg-platform.md` (Story 1.3)
- `_bmad-output/planning-artifacts/prd.md` (`FR-01`)
- `_bmad-output/planning-artifacts/architecture.md` (Authentication & Security, boundaries, error patterns)
- `_bmad-output/implementation-artifacts/1-1-set-up-initial-project-from-selected-backend-starter-foundation.md`
- `_bmad-output/implementation-artifacts/1-2-expose-health-and-readiness-signals-for-gateway-and-dependencies.md`
- `https://pypi.org/project/fastapi/`
- `https://pypi.org/project/SQLAlchemy/`
- `https://pypi.org/project/alembic/`
- `https://pypi.org/project/pydantic/`
- `https://pypi.org/project/pydantic-settings/`

## Dev Agent Record

### Agent Model Used

GPT-5 (Codex)

### Completion Notes List

- Added API key model fields, repository lookups, and auth service validation logic.
- Enforced API key authentication on protected routes with error envelope responses.
- Emitted audit-service auth success/failure events without raw key leakage.
- Tests: `pytest`, `ruff`, `mypy`
- Code review fixes: added fail-secure auth dependency handling and repository/dependency failure deny test coverage

## File List

- `app/api/dependencies.py`
- `app/services/auth_service.py`
- `app/repositories/api_keys_repository.py`
- `app/infrastructure/db/models/api_key.py`
- `tests/integration/api/test_authentication.py`
- `tests/unit/services/test_auth_service.py`
- `_bmad-output/implementation-artifacts/1-3-authenticate-protected-api-requests-using-provisioned-api-keys.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

## Change Log

- 2026-02-26: Implemented API key authentication flow, audit events, and tests
- 2026-02-26: Code review fixes applied (fail-secure auth dependency error handling + additional auth-path test coverage + tracking/documentation sync)

## Senior Developer Review (AI)

### Review Date

2026-02-26

### Outcome

Approve

### Findings Addressed

- [x] Implemented fail-secure deny behavior for auth dependency exceptions in `require_api_key`
- [x] Added integration test for auth dependency failure deny path
- [x] Added supplemental auth unit coverage (`allowed_ips` deny path)
- [x] Added missing File List and Change Log sections
- [x] Synced story/sprint statuses to terminal review state (`done`)
