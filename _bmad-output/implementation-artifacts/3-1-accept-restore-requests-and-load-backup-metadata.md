# Story 3.1: Accept Restore Requests and Load Backup Metadata

Status: done

## Story

As a restore requester,
I want the restore API to validate restore requests and load backup metadata,
so that restore processing can begin safely.

## Traceability

FR-07, FR-17, UJ-03

## Acceptance Criteria

1. Given an invalid restore request, when the API validates input, then it returns a documented validation error.
2. Given a valid restore request, when metadata lookup runs, then the system loads the referenced backup metadata or returns a not-found error.
3. Given metadata lookup fails, when the response is returned, then no restore token is issued.

## Tasks / Subtasks

- [x] Implement restore request schema validation and route handler in app/api/routes/restores.py (AC: 1, 2, 3)
- [x] Load backup metadata via repository/service using stable backup identifier (AC: 2)
- [x] Return documented not-found or validation error contract as appropriate (AC: 1, 2)
- [x] Ensure no restore token is issued on validation/metadata lookup failure (AC: 3)
- [x] Add tests for invalid request, not-found metadata, and valid metadata load path (AC: 1, 2, 3)

## Dev Notes

### Scope

Restore entrypoint validation and metadata loading only. Do not execute MFA, policy, decrypt, integrity validation, or TTL token issuance yet.

### Architecture Guardrails

- Reuse backup metadata model/repository conventions from Epic 2; do not duplicate lookup logic in routes.
- Keep restore route handlers thin and orchestrate via restore service.
- Error responses must use documented contract and distinguish validation vs not-found cleanly.
- No restore token issuance on any failure path in this story.

### Likely Files

- app/api/routes/restores.py
- app/schemas/restores.py
- app/services/restore_service.py
- app/repositories/backups_repository.py
- tests/integration/api/test_restore_request_validation.py

### Testing Requirements

- Invalid restore request returns documented validation error
- Valid request loads metadata or returns not-found error
- No restore token issued when lookup fails
- Response payloads remain contract-consistent

### Previous Story / Implementation Intelligence

- Build directly on Epic 2 backup metadata persistence outputs (especially stable backup identifiers and retrievable metadata in Story 2.5).
- Epic 1 and Epic 2 work should provide reusable auth/RBAC/policy/backup metadata patterns; do not duplicate security or repository plumbing in routes.
- Keep restore orchestration in app/services/restore_service.py and shared concerns in services/repositories per architecture boundaries.

### Latest Tech Information (researched 2026-02-26)

- FastAPI PyPI latest observed (2026-02-26): 0.133.1 (released Feb 25, 2026)
- SQLAlchemy PyPI latest observed: 2.0.47 (released Feb 24, 2026)
- Alembic PyPI latest observed: 1.18.4 (released Feb 10, 2026)
- Pydantic PyPI latest observed: 2.12.5 (released Nov 26, 2025)
- pydantic-settings PyPI latest observed: 2.13.1 (released Feb 19, 2026)
- Uvicorn PyPI latest observed: 0.41.0 (released Feb 16, 2026)

### References

- _bmad-output/planning-artifacts/epics-and-stories/epic-3-perform-authorized-restores-with-integrity-and-ttl-controls.md
- _bmad-output/planning-artifacts/architecture.md
- _bmad-output/planning-artifacts/prd.md
- _bmad-output/implementation-artifacts/2-4-encrypt-backup-payloads-before-object-storage-and-track-key-version.md
- _bmad-output/implementation-artifacts/2-5-persist-backup-metadata-lifecycle-status-and-audit-evidence.md
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

- Post-review fixes: enforced MFA before metadata existence checks, bound restore token use to issuing principal, added token-store expiry cleanup, and fail-secure handling for invalid metadata classification.
- Ultimate context engine analysis completed - comprehensive developer guide created
- Story status set to ready-for-dev
- Implemented restore request schema, route handler, and restore metadata lookup service for restore entrypoint
- Added documented not-found error contract and success payload for metadata-loaded restore preflight path
- Added integration tests for request validation, metadata-not-found, and successful metadata load (no restore token issuance)
- Validation passed: `python -m pytest tests/integration/api/test_restore_request_validation.py`, `python -m ruff check ...`, `python -m mypy app tests/integration/api/test_restore_request_validation.py`

## File List

- `app/api/dependencies.py`
- `app/api/routes/restores.py`
- `app/core/config.py`
- `app/core/enums.py`
- `app/infrastructure/crypto/key_store_fs.py`
- `app/schemas/restores.py`
- `app/services/audit_service.py`
- `app/services/auth_service.py`
- `app/services/incident_service.py`
- `app/services/policy_service.py`
- `app/services/restore_service.py`
- `app/services/restore_access_token_service.py`
- `tests/integration/api/test_restore_request_validation.py`
- `tests/integration/api/test_restore_mfa_policy.py`
- `tests/integration/api/test_restore_incident_restrictions.py`
- `tests/integration/workflows/test_restore_integrity.py`
- `tests/integration/api/test_restore_ttl_tokens.py`
- `_bmad-output/implementation-artifacts/3-1-accept-restore-requests-and-load-backup-metadata.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

## Change Log

- 2026-02-26: Implemented Story 3.1 restore request validation and backup metadata lookup preflight path
- 2026-02-26: Applied code-review remediation for MFA ordering, token principal binding, metadata-classification fail-secure handling, and token-store expiry cleanup


