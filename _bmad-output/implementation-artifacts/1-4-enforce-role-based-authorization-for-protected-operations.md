# Story 1.4: Enforce Role-Based Authorization for Protected Operations

Status: done

## Story

As a security administrator,
I want role-based authorization enforced,
so that users can perform only the operations permitted by their role.

## Acceptance Criteria

1. Given a backup-only role, when restore or admin endpoints are requested, then the API denies the request and records an auditable deny event.
2. Given a privileged role with required permissions, when permitted endpoints are requested, then authorization succeeds and processing continues.
3. Given authorization decisions are evaluated, when responses are returned, then denied responses use the documented error contract.

## Tasks / Subtasks

- [x] Implement RBAC authorization dependency/service using authenticated principal context (AC: 1, 2, 3)
- [x] Define role/permission mapping for MVP protected operations (AC: 1, 2)
- [x] Wire authorization checks to restore and admin routes (AC: 1, 2)
- [x] Emit auditable deny events for authorization failures (AC: 1)
- [x] Return documented error envelope on denies (AC: 3)
- [x] Add tests for deny/allow outcomes and error contract consistency (AC: 1, 2, 3)

## Dev Notes

### Scope

RBAC authorization only. Do not implement full classification/incident policy evaluation yet (that belongs to later stories/FR-04 and FR-09).

### Architecture Guardrails

- Preserve auth -> authorization/policy ordering
- Keep role checks centralized; do not scatter hardcoded role checks in route handlers
- Prefer explicit allow/deny result objects over plain booleans for later policy composition
- Audit security denies before returning response where feasible
- Reuse shared error envelope and `snake_case` payload naming

### Likely Files

- `app/services/policy_service.py` (or dedicated authz logic with clear boundary)
- `app/api/dependencies.py`
- `app/core/enums.py`
- `app/schemas/auth.py` / `app/schemas/common.py`
- `app/api/routes/restores.py`
- `app/api/routes/admin/*.py`
- `app/services/audit_service.py`
- `tests/unit/services/test_policy_service_rbac.py`
- `tests/integration/api/test_rbac_authorization.py`

### Testing Requirements

- Backup-only role denied on restore/admin endpoints
- Privileged role allowed on permitted endpoint
- Denies emit audit event
- Denied response matches documented error contract
- Missing auth context remains denied/fail-secure

### Previous Story / Git Intelligence

- Reuse Story 1.3 auth context; do not re-parse API keys here
- No `.git` repository detected; git intelligence unavailable

### Latest Tech Information (researched 2026-02-26)

- FastAPI PyPI latest observed: `0.133.1`
- Pydantic PyPI latest observed: `2.12.5`
- SQLAlchemy PyPI latest observed: `2.0.47` (if role/policy state is persisted already)

### References

- `_bmad-output/planning-artifacts/epics-and-stories/epic-1-provision-and-secure-the-ssbg-platform.md` (Story 1.4)
- `_bmad-output/planning-artifacts/prd.md` (`FR-02`)
- `_bmad-output/planning-artifacts/architecture.md` (Authentication & Security, policy service boundary, error handling)
- `_bmad-output/implementation-artifacts/1-3-authenticate-protected-api-requests-using-provisioned-api-keys.md`
- `https://pypi.org/project/fastapi/`
- `https://pypi.org/project/pydantic/`
- `https://pypi.org/project/SQLAlchemy/`

## Dev Agent Record

### Agent Model Used

GPT-5 (Codex)

### Completion Notes List

- Added RBAC policy service with role-permission mapping.
- Enforced authorization dependencies for restore/admin routes and backups.
- Recorded authorization-denied audit events without leaking secrets.
- Added unit and integration tests for allow/deny flows and error envelopes.
- Tests: `pytest`, `ruff`, `mypy`
- Code review fixes: added deny-audit assertions to RBAC integration tests and synchronized tracking/docs

## File List

- `app/api/dependencies.py`
- `app/api/routes/__init__.py`
- `app/services/policy_service.py`
- `app/services/audit_service.py`
- `tests/unit/services/test_policy_service_rbac.py`
- `tests/integration/api/test_rbac_authorization.py`
- `_bmad-output/implementation-artifacts/1-4-enforce-role-based-authorization-for-protected-operations.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

## Change Log

- 2026-02-26: Implemented RBAC authorization flow and allow/deny tests for protected routes
- 2026-02-26: Code review fixes applied (deny audit-event assertions + tracking/documentation sync)

## Senior Developer Review (AI)

### Review Date

2026-02-26

### Outcome

Approve

### Findings Addressed

- [x] Added integration assertions that denied RBAC decisions record audit deny events
- [x] Added missing File List and Change Log sections
- [x] Synced story/sprint statuses to terminal review state (`done`)
