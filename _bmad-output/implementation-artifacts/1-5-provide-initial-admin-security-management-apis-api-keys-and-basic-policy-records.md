# Story 1.5: Provide Initial Admin Security Management APIs (API Keys and Basic Policy Records)

Status: done

## Story

As a security administrator,
I want administrative APIs for basic security setup,
so that I can provision keys and baseline policy data for operations.

## Acceptance Criteria

1. Given an authorized admin, when API key management actions are performed, then the system persists and returns expected metadata without exposing raw secrets after creation.
2. Given an unauthorized caller, when admin security endpoints are requested, then access is denied.
3. Given admin security actions occur, when requests complete, then audit events are recorded.

## Tasks / Subtasks

- [x] Add admin API key endpoints in `app/api/routes/admin/keys.py` (create/list/revoke baseline set) (AC: 1, 2, 3)
- [x] Add admin policy record endpoints in `app/api/routes/admin/policies.py` (create/list/update baseline records) (AC: 2, 3)
- [x] Persist API key and policy record metadata via repositories/models (AC: 1)
- [x] Reuse auth + RBAC chain from Stories 1.3 and 1.4 on all admin endpoints (AC: 2)
- [x] Emit audit events for admin creates/updates/revokes/denies (AC: 3)
- [x] Add tests for authorized/unauthorized flows and secret non-exposure (AC: 1, 2, 3)

## Dev Notes

### Scope

Baseline admin security-management APIs only. Do not implement the full policy decision engine here; focus on CRUD needed to prepare the system for later operational stories.

### Architecture Guardrails

- Admin routes live under `app/api/routes/admin/*`
- Keep route handlers thin; use services/repositories
- Reuse shared auth and RBAC dependencies (no route-local bypasses)
- Never return raw API key secret after initial creation response
- Hash key material at rest
- Audit all admin actions and denies
- Keep response/error schema naming consistent (`snake_case`, shared envelope)

### Likely Files

- `app/api/routes/admin/keys.py`
- `app/api/routes/admin/policies.py`
- `app/schemas/admin.py`
- `app/services/auth_service.py`
- `app/services/policy_service.py`
- `app/services/audit_service.py`
- `app/repositories/api_keys_repository.py`
- `app/repositories/policies_repository.py` (if missing, add following existing patterns)
- `app/infrastructure/db/models/api_key.py`
- `app/infrastructure/db/models/policy_record.py` (if missing)
- `tests/integration/api/test_admin_keys.py`
- `tests/integration/api/test_admin_policies.py`

### Testing Requirements

- Authorized admin can create/list/revoke API keys
- API key create returns secret once (if server-generated), subsequent reads do not expose secret
- Unauthorized callers are denied for admin endpoints
- Audit events emitted for admin actions and denies
- Error responses follow documented contract

### Previous Story / Git Intelligence

- Reuse Story 1.3 auth and Story 1.4 RBAC directly
- No `.git` repository detected; git intelligence unavailable

### Latest Tech Information (researched 2026-02-26)

- FastAPI PyPI latest observed: `0.133.1`
- SQLAlchemy PyPI latest observed: `2.0.47`
- Alembic PyPI latest observed: `1.18.4`
- Pydantic PyPI latest observed: `2.12.5`
- `pydantic-settings` PyPI latest observed: `2.13.1`

### References

- `_bmad-output/planning-artifacts/epics-and-stories/epic-1-provision-and-secure-the-ssbg-platform.md` (Story 1.5)
- `_bmad-output/planning-artifacts/prd.md` (`FR-17`, `UJ-01`)
- `_bmad-output/planning-artifacts/architecture.md` (admin route layout, boundaries, security/audit patterns)
- `_bmad-output/implementation-artifacts/1-3-authenticate-protected-api-requests-using-provisioned-api-keys.md`
- `_bmad-output/implementation-artifacts/1-4-enforce-role-based-authorization-for-protected-operations.md`
- `https://pypi.org/project/fastapi/`
- `https://pypi.org/project/SQLAlchemy/`
- `https://pypi.org/project/alembic/`
- `https://pypi.org/project/pydantic/`
- `https://pypi.org/project/pydantic-settings/`

## Dev Agent Record

### Agent Model Used

GPT-5 (Codex)

### Completion Notes List

- Added admin API key and policy endpoints with repository-backed persistence and envelopes.
- Ensured API key secrets are only returned on create and never in list/revoke responses.
- Emitted audit events for admin actions and reused RBAC enforcement on admin routes.
- Added integration tests for authorized/unauthorized flows and secret non-exposure.
- Tests: `pytest`, `ruff`, `mypy`
- Code review fixes: expanded unauthorized admin endpoint coverage and added deny-audit assertions; synchronized tracking/docs

## File List

- `app/api/routes/admin/keys.py`
- `app/api/routes/admin/policies.py`
- `app/schemas/admin.py`
- `app/repositories/api_keys_repository.py`
- `app/repositories/policies_repository.py`
- `app/infrastructure/db/models/api_key.py`
- `app/infrastructure/db/models/policy_record.py`
- `tests/integration/api/test_admin_keys.py`
- `tests/integration/api/test_admin_policies.py`
- `_bmad-output/implementation-artifacts/1-5-provide-initial-admin-security-management-apis-api-keys-and-basic-policy-records.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

## Change Log

- 2026-02-26: Implemented admin key/policy endpoints with persistence, RBAC reuse, and integration tests
- 2026-02-26: Code review fixes applied (deny audit assertions + broader unauthorized endpoint coverage + tracking/documentation sync)

## Senior Developer Review (AI)

### Review Date

2026-02-26

### Outcome

Approve

### Findings Addressed

- [x] Added deny-audit assertions for unauthorized admin endpoint access
- [x] Expanded unauthorized coverage for list/revoke (keys) and list/update (policies)
- [x] Added missing File List and Change Log sections
- [x] Synced story/sprint statuses to terminal review state (`done`)
