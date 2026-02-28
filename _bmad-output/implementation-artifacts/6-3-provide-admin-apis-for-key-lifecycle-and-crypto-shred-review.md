# Story 6.3: Provide Admin APIs for Key Lifecycle and Crypto-Shred Review

Status: review

## Story

As a security administrator,
I want authorized APIs to review key versions and destruction outcomes,
so that I can manage and audit key lifecycle operations.

## Traceability

FR-17, UJ-06

## Acceptance Criteria

1. Given an authorized admin, when key lifecycle endpoints are called, then key version metadata and statuses are returned without exposing sensitive key material.
2. Given crypto-shred outcomes are queried, when results are returned, then affected scope and status information is available for review.
3. Given an unauthorized caller, when key lifecycle admin endpoints are called, then access is denied.

## Tasks / Subtasks

- [x] Implement admin key lifecycle review endpoints (list/detail/status) with sensitive-field redaction (AC: 1)
- [x] Implement crypto-shred outcome review endpoints with affected-scope summaries (AC: 2)
- [x] Enforce auth/RBAC on all key lifecycle/crypto-shred review APIs (AC: 3)
- [x] Audit admin review access and outcome-query actions (AC: 1, 2, 3)
- [x] Add tests for authorized responses, unauthorized denial, and secret non-exposure (AC: 1, 2, 3)

## Dev Notes

### Scope

Expose secure, authorized review APIs for key lifecycle state and crypto-shred outcomes.

### Architecture Guardrails

- Never expose raw key material, secrets, or sensitive unwrap data in admin responses.
- Reuse Epic 1 auth/RBAC dependency chain for all admin endpoints.
- Keep outcome views consistent with audit trail and backup/key status source-of-truth data.
- Use stable response schema for operational automation and audit review tooling.

### Likely Files

- app/api/routes/admin/keys.py
- app/schemas/admin.py
- app/services/key_management_service.py
- app/repositories/key_versions_repository.py
- app/repositories/backups_repository.py
- app/services/audit_service.py
- tests/integration/api/test_admin_key_lifecycle_review.py

### Testing Requirements

- Authorized admin can view key metadata/status without secret exposure
- Crypto-shred outcome review returns affected scope/status info
- Unauthorized callers denied with documented contract
- Admin review actions are auditable

### Previous Story / Implementation Intelligence

- Builds on Story 6.1/6.2 outcomes and existing admin auth/authorization from Epic 1.
- Reuse completed Epics 1-5 patterns for admin auth, policy gating, restore restrictions, and tamper-evident auditing.
- Keep orchestration in services and state transitions in repositories with auditable outcomes.

### Latest Tech Information (researched 2026-02-26)

- FastAPI PyPI latest observed (2026-02-26): 0.133.1 (released Feb 25, 2026)
- SQLAlchemy PyPI latest observed: 2.0.47 (released Feb 24, 2026)
- Alembic PyPI latest observed: 1.18.4 (released Feb 10, 2026)
- Pydantic PyPI latest observed: 2.12.5 (released Nov 26, 2025)
- pydantic-settings PyPI latest observed: 2.13.1 (released Feb 19, 2026)
- Uvicorn PyPI latest observed: 0.41.0 (released Feb 16, 2026)

### References

- _bmad-output/planning-artifacts/epics-and-stories/epic-6-execute-key-lifecycle-management-and-crypto-shredding.md
- _bmad-output/planning-artifacts/architecture.md
- _bmad-output/planning-artifacts/prd.md
- _bmad-output/implementation-artifacts/5-2-manage-incident-response-state-transitions.md
- _bmad-output/implementation-artifacts/5-3-apply-incident-level-restrictions-across-restore-workflows.md
- https://pypi.org/project/fastapi/
- https://pypi.org/project/SQLAlchemy/
- https://pypi.org/project/alembic/
- https://pypi.org/project/pydantic/
- https://pypi.org/project/pydantic-settings/
- https://pypi.org/project/uvicorn/

## Dev Agent Record

### Agent Model Used

GPT-5 (Codex)

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created
- Story status set to ready-for-dev
- Added key lifecycle review endpoints for version detail and crypto-shred outcomes:
  - `GET /api/v1/admin/keys/versions/{version_id}`
  - `GET /api/v1/admin/keys/versions/{version_id}/crypto-shred-outcome`
- Extended key management service with review methods (`get_version`, `get_crypto_shred_outcome`) and not-found error handling.
- Added backup repository scope summary (`summarize_by_key_version`) for irreversible/active/processing/failed counts and latest shred timestamp.
- Added response schema for outcome review (`CryptoShredOutcomeResponse`) while keeping key material non-exposed.
- Added audit events for review actions (`key_version_reviewed`, `crypto_shred_outcome_reviewed`).
- Added integration API tests for authorized access, unauthorized RBAC denial, not-found contract, and no-secret-exposure checks.
- Validation passed: `python -m pytest ...`, `python -m ruff check ...`, `python -m mypy ...`.

## File List

- `app/api/routes/admin/keys.py`
- `app/services/key_management_service.py`
- `app/repositories/backups_repository.py`
- `app/schemas/admin.py`
- `tests/integration/api/test_admin_key_lifecycle_review.py`
- `_bmad-output/implementation-artifacts/6-3-provide-admin-apis-for-key-lifecycle-and-crypto-shred-review.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

## Change Log

- 2026-02-28: Implemented Story 6.3 admin review APIs for key lifecycle and crypto-shred outcomes with RBAC/audit coverage.
