# Story 2.1: Accept Backup Requests and Validate Base Request Contract

Status: ready-for-dev

## Story

As a backup operator,
I want the backup endpoint to validate request structure,
so that malformed requests are rejected consistently.

## Traceability

FR-04 (precondition for policy pipeline), FR-17 (operational API), UJ-02

## Acceptance Criteria

1. Given a malformed backup request, when it reaches the backup endpoint, then the API returns validation errors using the documented contract.
2. Given a well-formed request, when validation passes, then processing continues to classification and policy evaluation.
3. Given request validation fails, when the response is returned, then no backup object or metadata record is created.

## Tasks / Subtasks

- [ ] Implement backup request schema validation and route handling in app/api/routes/backups.py (AC: 1, 2, 3)
- [ ] Return documented validation error contract for malformed requests (AC: 1)
- [ ] Ensure valid requests hand off to classification/policy pipeline without performing storage writes yet (AC: 2, 3)
- [ ] Add tests for malformed vs well-formed requests and no-side-effects on validation failure (AC: 1, 2, 3)

## Dev Notes

### Scope

Validate request contract and handoff only. Do not perform encryption/object storage or final metadata persistence in this story beyond proving no side effects on validation failure.

### Architecture Guardrails

- Keep route handlers thin; use schemas/service layer for request validation and orchestration handoff.
- Use shared error envelope / validation contract patterns from existing Epic 1 implementation.
- Do not create backup object storage writes or metadata records when validation fails.
- Prepare interfaces for downstream classification + policy evaluation (Stories 2.2 and 2.3).

### Likely Files

- app/api/routes/backups.py
- app/schemas/backups.py
- app/services/backup_service.py
- app/schemas/common.py
- tests/integration/api/test_backups_validation.py

### Testing Requirements

- Malformed payload returns validation error contract and non-success status
- Well-formed payload proceeds to next pipeline stage (can use mocked service handoff)
- Validation failure produces no metadata/object write side effects
- Field naming and error payload shape remain contract-consistent

### Previous Story / Implementation Intelligence

- Reuse Epic 1 auth, RBAC, error handling, and health-tested app wiring. Protected backup endpoints should compose with existing auth/authz dependencies.
- Epic 1 stories are already marked done in sprint-status.yaml; reuse established auth/RBAC/admin patterns.
- Keep backup orchestration in app/services/backup_service.py and persistence in repositories to preserve architecture boundaries.

### Latest Tech Information (researched 2026-02-26)

- FastAPI PyPI latest observed (2026-02-26): 0.133.1 (released Feb 25, 2026)
- SQLAlchemy PyPI latest observed: 2.0.47 (released Feb 24, 2026)
- Alembic PyPI latest observed: 1.18.4 (released Feb 10, 2026)
- Pydantic PyPI latest observed: 2.12.5 (released Nov 26, 2025)
- pydantic-settings PyPI latest observed: 2.13.1 (released Feb 19, 2026)
- Uvicorn PyPI latest observed: 0.41.0 (released Feb 16, 2026)

### References

- _bmad-output/planning-artifacts/epics-and-stories/epic-2-submit-and-persist-encrypted-backups.md
- _bmad-output/planning-artifacts/architecture.md
- _bmad-output/planning-artifacts/prd.md
- _bmad-output/implementation-artifacts/1-3-authenticate-protected-api-requests-using-provisioned-api-keys.md
- _bmad-output/implementation-artifacts/1-4-enforce-role-based-authorization-for-protected-operations.md
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
