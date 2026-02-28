# Story 6.1: Rotate Active Key Version Without Re-Encrypting Existing Backups

Status: review

## Story

As a security administrator,
I want to rotate the active key version,
so that future backups use new key material while existing backups remain restorable.

## Traceability

FR-16, UJ-01/UJ-06

## Acceptance Criteria

1. Given a new key version is registered, when rotation is completed, then new backups use the new active key version.
2. Given older backups reference previous non-destroyed key versions, when restore is attempted, then they remain restorable.
3. Given key rotation occurs, when the operation completes, then an audit event is recorded.

## Tasks / Subtasks

- [x] Implement key version registration and active-version switch flow in key management service (AC: 1)
- [x] Ensure backup encryption path uses currently active key version for new backups (AC: 1)
- [x] Preserve restore compatibility for backups bound to prior non-destroyed versions (AC: 2)
- [x] Record key rotation audit event with actor, from_version, to_version, and timestamp (AC: 3)
- [x] Add tests for rotation behavior, new backup key version usage, and old backup restorability (AC: 1, 2, 3)

## Dev Notes

### Scope

Introduce safe key rotation behavior without retroactive re-encryption of existing backups.

### Architecture Guardrails

- Never re-encrypt historical backups during rotation in this story.
- Keep active key version selection centralized in key management service/config source of truth.
- Ensure restore logic resolves per-backup key version metadata, not global latest key.
- Audit every rotation and deny invalid transitions/fallback behaviors fail-secure.

### Likely Files

- app/services/key_management_service.py
- app/repositories/key_versions_repository.py
- app/infrastructure/db/models/key_version.py
- app/services/backup_service.py
- app/services/restore_service.py
- app/services/audit_service.py
- app/api/routes/admin/keys.py
- tests/integration/workflows/test_key_rotation.py

### Testing Requirements

- New backups after rotation reference new active key version
- Old backups tied to prior non-destroyed versions remain restorable
- Rotation emits audit event with expected metadata
- Invalid rotation request is denied/fail-secure

### Previous Story / Implementation Intelligence

- Builds on Epic 2 key-version tracking and Epic 3 restore behavior with per-backup metadata usage.
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
- Implemented key-version lifecycle persistence model/repository with active/destroyed state and rotation metadata.
- Added `KeyManagementService` for active-version seeding, secure rotation, and active key-material resolution.
- Updated backup encryption path to use active key material from key management service, preserving per-backup key version metadata.
- Added key-rotation audit event recording (`key_rotation`) with from/to version context.
- Added admin route support for key rotation and key-version listing under `/api/v1/admin/keys/versions/*`.
- Added workflow and API tests validating rotation behavior, new-backup key usage, old-backup restorability, invalid rotation denial, and RBAC denial.
- Validation passed: `python -m pytest ...key_rotation...`, `python -m ruff check ...`, `python -m mypy app tests/...`.

## File List

- `app/infrastructure/db/models/key_version.py`
- `app/infrastructure/db/models/__init__.py`
- `app/repositories/key_versions_repository.py`
- `app/services/key_management_service.py`
- `app/services/backup_service.py`
- `app/services/audit_service.py`
- `app/api/dependencies.py`
- `app/api/routes/admin/keys.py`
- `app/schemas/admin.py`
- `tests/integration/workflows/test_key_rotation.py`
- `tests/integration/api/test_admin_key_rotation.py`
- `_bmad-output/implementation-artifacts/6-1-rotate-active-key-version-without-re-encrypting-existing-backups.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

## Change Log

- 2026-02-28: Implemented Story 6.1 key rotation lifecycle flow with backup-path integration and restore compatibility preservation.
