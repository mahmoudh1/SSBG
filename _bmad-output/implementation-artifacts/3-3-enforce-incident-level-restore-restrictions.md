# Story 3.3: Enforce Incident-Level Restore Restrictions

Status: ready-for-dev

## Story

As a incident responder,
I want restore behavior restricted by incident level,
so that suspected abuse can be contained.

## Traceability

FR-09, FR-14, UJ-03/UJ-04

## Acceptance Criteria

1. Given a restore request during a quarantine-level incident state, when the request is evaluated, then it is transitioned to the documented pending/manual-review behavior.
2. Given the highest incident level is active, when a restore request is submitted, then restore completion is blocked.
3. Given incident restrictions are applied, when the request outcome is returned, then the response and audit trail reflect the restriction reason.

## Tasks / Subtasks

- [ ] Integrate incident-state checks into restore orchestration before completion (AC: 1, 2, 3)
- [ ] Implement documented quarantine/manual-review behavior result path (AC: 1)
- [ ] Block restore completion at highest incident level with explicit reason mapping (AC: 2, 3)
- [ ] Audit incident restriction outcomes with reason details (AC: 3)
- [ ] Add tests for quarantine-level pending behavior and highest-level block (AC: 1, 2, 3)

## Dev Notes

### Scope

Restore-side incident restriction enforcement using current incident-state source of truth. Epic 5 expands incident management breadth later.

### Architecture Guardrails

- Use dedicated incident service/source of truth; do not hardcode incident level constants in routes.
- Return explicit restriction reasons in response/audit trail using documented contract patterns.
- Quarantine/manual-review behavior should preserve later completion workflow boundaries.
- Keep dependency direction: restore enforcement consumes incident state; incident management is expanded later in Epic 5.

### Likely Files

- app/services/restore_service.py
- app/services/incident_service.py
- app/api/routes/restores.py
- app/services/audit_service.py
- app/repositories/incident_repository.py
- tests/integration/api/test_restore_incident_restrictions.py

### Testing Requirements

- Quarantine-level incident yields pending/manual-review behavior
- Highest incident level blocks restore completion
- Responses and audit trail include restriction reason
- No success token issued when restrictions deny/block completion

### Previous Story / Implementation Intelligence

- Compose on top of Story 3.2 auth/MFA/policy gates. Reuse explicit policy/deny result and audit patterns from Epic 2 and Epic 1.
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
