# Story 2.5: Persist Backup Metadata, Lifecycle Status, and Audit Evidence

Status: ready-for-dev

## Story

As a an auditor or operator,
I want backup metadata and lifecycle status recorded,
so that backups can be tracked, restored, and reviewed later.

## Traceability

FR-07, FR-12, UJ-02/UJ-05

## Acceptance Criteria

1. Given an accepted backup, when processing completes, then the API returns a stable backup identifier tied to persisted metadata.
2. Given lifecycle state changes, when backup status transitions occur, then updated status values are stored.
3. Given backup processing succeeds or fails at key checkpoints, when events occur, then audit entries are recorded for the operation.

## Tasks / Subtasks

- [ ] Finalize backup metadata persistence model/repository for identifiers, storage refs, checksums, classification, key version, timestamps (AC: 1)
- [ ] Implement lifecycle status transitions and persistence updates (AC: 2)
- [ ] Emit audit entries for backup checkpoints (success/failure/deny as applicable) (AC: 3)
- [ ] Return stable backup identifier from API tied to persisted metadata (AC: 1)
- [ ] Add tests for metadata retrieval, status transitions, and audit evidence generation (AC: 1, 2, 3)

## Dev Notes

### Scope

Complete the backup processing slice with durable metadata, lifecycle tracking, and audit evidence suitable for later restore and audit-validation stories.

### Architecture Guardrails

- Follow architecture naming for metadata tables/columns and lifecycle enums.
- Audit entries should be tamper-evident-ready in format/invocation path (full chain validation arrives in Epic 4).
- Do not return backup success without persisted metadata identifier.
- Keep lifecycle updates in service/repository layer with explicit transitions.

### Likely Files

- app/services/backup_service.py
- app/repositories/backups_repository.py
- app/repositories/audit_repository.py
- app/services/audit_service.py
- app/infrastructure/db/models/backup_metadata.py
- app/infrastructure/db/models/audit_log_entry.py
- app/api/routes/backups.py
- tests/integration/workflows/test_backup_metadata_lifecycle.py

### Testing Requirements

- Accepted backup returns stable identifier tied to metadata
- Lifecycle status transitions persist correctly
- Audit entries recorded at key checkpoints
- Failure checkpoints still produce expected audit evidence without false success

### Previous Story / Implementation Intelligence

- Builds directly on Stories 2.1-2.4. Reuse existing audit service patterns from Epic 1 auth/RBAC deny auditing.
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
