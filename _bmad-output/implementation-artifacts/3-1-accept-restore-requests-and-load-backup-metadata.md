# Story 3.1: Accept Restore Requests and Load Backup Metadata

Status: ready-for-dev

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

- [ ] Implement restore request schema validation and route handler in app/api/routes/restores.py (AC: 1, 2, 3)
- [ ] Load backup metadata via repository/service using stable backup identifier (AC: 2)
- [ ] Return documented not-found or validation error contract as appropriate (AC: 1, 2)
- [ ] Ensure no restore token is issued on validation/metadata lookup failure (AC: 3)
- [ ] Add tests for invalid request, not-found metadata, and valid metadata load path (AC: 1, 2, 3)

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

- Ultimate context engine analysis completed - comprehensive developer guide created
- Story status set to ready-for-dev
