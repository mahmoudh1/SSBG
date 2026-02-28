# Story 4.3: Expose Authorized Audit Review Endpoints for Security Admins

Status: done

## Story

As a security administrator,
I want authorized access to audit review and validation operations,
so that I can investigate security events.

## Traceability

FR-17, UJ-05

## Acceptance Criteria

1. Given an authorized admin, when audit review endpoints are requested, then audit data and validation summaries are returned according to access rules.
2. Given an unauthorized caller, when audit endpoints are requested, then access is denied.
3. Given audit review actions occur, when requests are processed, then relevant access events are auditable.

## Tasks / Subtasks

- [x] Implement admin-authorized audit review endpoints with pagination/filtering baseline (AC: 1)
- [x] Integrate auth/RBAC dependencies for audit endpoints (AC: 1, 2)
- [x] Include validation summary retrieval/trigger integration from Story 4.2 (AC: 1)
- [x] Audit access and deny events for audit review operations (AC: 3)
- [x] Add tests for authorized access, unauthorized denial, and auditable access events (AC: 1, 2, 3)

## Dev Notes

### Scope

Securely expose audit review and validation results to authorized admins.

### Architecture Guardrails

- Reuse Epic 1 auth/RBAC pipeline; no endpoint-level bypasses.
- Keep response contract stable and minimize sensitive data exposure.
- Audit both successful review access and denied attempts.
- Keep heavy validation logic in services; endpoints should orchestrate only.

### Likely Files

- app/api/routes/audit.py
- app/services/audit_service.py
- app/api/dependencies.py
- app/schemas/audit.py
- tests/integration/api/test_audit_review_authorization.py

### Testing Requirements

- Authorized admin receives audit data and validation summaries
- Unauthorized caller denied with documented error contract
- Audit review actions generate auditable access events
- Paging/filtering contract remains consistent

### Previous Story / Implementation Intelligence

- Depends on Story 4.2 validation capability and existing auth/RBAC from Epic 1.
- Reuse completed Epics 1-3 implementation patterns for auth, policy, restore, and audit integration.
- Keep orchestration in services and persistence in repositories per architecture boundaries.

### Latest Tech Information (researched 2026-02-26)

- FastAPI PyPI latest observed (2026-02-26): 0.133.1 (released Feb 25, 2026)
- SQLAlchemy PyPI latest observed: 2.0.47 (released Feb 24, 2026)
- Alembic PyPI latest observed: 1.18.4 (released Feb 10, 2026)
- Pydantic PyPI latest observed: 2.12.5 (released Nov 26, 2025)
- pydantic-settings PyPI latest observed: 2.13.1 (released Feb 19, 2026)
- Uvicorn PyPI latest observed: 0.41.0 (released Feb 16, 2026)

### References

- _bmad-output/planning-artifacts/epics-and-stories/epic-4-produce-and-validate-tamper-evident-audit-trails.md
- _bmad-output/planning-artifacts/epics-and-stories/epic-5-detect-suspicious-activity-and-manage-incident-response-state.md
- _bmad-output/planning-artifacts/architecture.md
- _bmad-output/planning-artifacts/prd.md
- _bmad-output/implementation-artifacts/3-5-issue-time-limited-restore-access-tokens.md
- https://pypi.org/project/fastapi/
- https://pypi.org/project/SQLAlchemy/
- https://pypi.org/project/alembic/
- https://pypi.org/project/pydantic/
- https://pypi.org/project/pydantic-settings/
- https://pypi.org/project/uvicorn/

## Dev Agent Record

### Agent Model Used

GPT-5 (Codex)

- Post-review fixes: added transactional rollback-safe audit append retries, persisted auth-failure deny events in chain, extended chain hash validation to include created_at, and removed fixed-chain validation window.
- Ultimate context engine analysis completed - comprehensive developer guide created
- Story status set to ready-for-dev
- Added `GET /api/v1/audit/entries` with pagination and baseline action/resource/status filters for authorized audit reviewers.
- Added `GET /api/v1/audit/summary` that returns the audit chain validation summary from Story 4.2.
- Reused existing RBAC `audit` permission pipeline to deny unauthorized callers using the standard `POLICY_DENIED` contract.
- Added auditable review access events (`audit_review_accessed`, `audit_validation_reviewed`) for successful audit review operations.
- Added authorization/review integration tests for admin success, operator denial, and auditable access evidence.
- Validation passed: `python -m pytest ...audit...`, `python -m ruff check ...`, `python -m mypy app tests/...`.

## File List

- `app/api/routes/audit.py`
- `app/infrastructure/db/models/audit_log_entry.py`
- `app/repositories/audit_repository.py`
- `app/schemas/audit.py`
- `app/services/audit_service.py`
- `scripts/verify_audit_chain.py`
- `tests/integration/api/test_audit_validation.py`
- `tests/integration/api/test_audit_review_authorization.py`
- `tests/integration/workflows/test_audit_chain_append.py`
- `alembic/versions/20260228_0001_add_audit_chain_fields.py`
- `_bmad-output/implementation-artifacts/4-3-expose-authorized-audit-review-endpoints-for-security-admins.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

## Change Log

- 2026-02-28: Implemented Story 4.3 authorized audit review endpoints with auditable access events.
- 2026-02-28: Applied Epic 4 code-review remediation for retry rollback safety, deny-event chain coverage, created_at hash coverage, and full-chain validation scan

