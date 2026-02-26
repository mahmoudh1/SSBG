# Story 2.2: Require and Persist Classification Metadata for Accepted Backups

Status: ready-for-dev

## Story

As a security administrator,
I want each accepted backup labeled with classification metadata,
so that policy and audit workflows can enforce classification-aware behavior.

## Traceability

FR-03, FR-07, UJ-02

## Acceptance Criteria

1. Given a backup request missing required classification, when policy/config requires classification, then the request is rejected or normalized according to documented rules.
2. Given an accepted backup request, when metadata is persisted, then classification is stored and retrievable.
3. Given later policy evaluation occurs, when restore logic reads metadata, then the stored classification is available for decisions.

## Tasks / Subtasks

- [ ] Define classification schema/enum and validation rules for backup requests/metadata (AC: 1, 2, 3)
- [ ] Implement classification normalization/rejection behavior from config/policy baseline rules (AC: 1)
- [ ] Persist classification in backup metadata model/repository and ensure retrieval path includes it (AC: 2, 3)
- [ ] Add tests for missing/normalized classifications and metadata retrieval (AC: 1, 2, 3)

## Dev Notes

### Scope

Introduce classification handling and persistence needed for later policy and restore decisions. Keep policy decision logic itself for Story 2.3.

### Architecture Guardrails

- Use architecture enum/serialization conventions (uppercase snake case values where enums are serialized).
- Classification must be stored in backup metadata for downstream restore/policy workflows.
- Do not hide normalization behavior; document and test the configured rule path.
- Keep metadata persistence in repositories/services, not routes.

### Likely Files

- app/schemas/backups.py
- app/core/enums.py
- app/services/backup_service.py
- app/repositories/backups_repository.py
- app/infrastructure/db/models/backup_metadata.py
- tests/integration/api/test_backup_classification.py

### Testing Requirements

- Missing classification rejected or normalized per documented rule
- Accepted backup metadata stores classification and retrieval returns it
- Classification field uses stable schema naming/enum values
- No regression to Story 2.1 validation contract

### Previous Story / Implementation Intelligence

- Build on Story 2.1 request validation flow and reuse Epic 1 auth/RBAC pipeline. Keep interfaces ready for Story 2.3 policy evaluation.
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
