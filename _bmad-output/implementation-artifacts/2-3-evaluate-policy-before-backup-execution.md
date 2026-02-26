# Story 2.3: Evaluate Policy Before Backup Execution

Status: ready-for-dev

## Story

As a security administrator,
I want policy decisions evaluated before backup execution,
so that denied operations are blocked with explicit reasons.

## Traceability

FR-04, UJ-02

## Acceptance Criteria

1. Given a protected backup request, when policy evaluation runs, then an explicit allow/deny result is produced.
2. Given a denied policy result, when the request is rejected, then the API returns a documented error code and reason category.
3. Given a policy result is produced, when processing continues or stops, then an audit event records the policy outcome.

## Tasks / Subtasks

- [ ] Extend policy_service with backup-policy evaluation returning explicit result objects (AC: 1)
- [ ] Integrate backup endpoint/service flow to enforce deny before encryption/storage steps (AC: 1, 2)
- [ ] Return documented error code + reason category for policy denies (AC: 2)
- [ ] Record audit event for allow/deny policy outcomes (AC: 3)
- [ ] Add tests for allow/deny policy paths and audit evidence (AC: 1, 2, 3)

## Dev Notes

### Scope

Pre-execution policy enforcement for backups. This is policy composition beyond RBAC and should produce explicit results/audit outcomes.

### Architecture Guardrails

- Do not collapse policy logic into route-level conditionals; keep in policy_service and service orchestration.
- Explicit allow/deny result objects should include reason category for error mapping and audit.
- Deny must occur before encryption/object storage writes.
- Audit both allows and denies where story requires policy outcome recording.

### Likely Files

- app/services/policy_service.py
- app/services/backup_service.py
- app/services/audit_service.py
- app/api/routes/backups.py
- tests/unit/services/test_policy_service_backup.py
- tests/integration/api/test_backup_policy_enforcement.py

### Testing Requirements

- Backup request produces explicit allow/deny decision result
- Denied result returns documented code and reason category
- Policy outcomes generate audit events
- Denied path stops before encryption/storage side effects

### Previous Story / Implementation Intelligence

- Reuse Epic 1 auth/RBAC and Story 2.2 classification metadata. Keep policy result format compatible with upcoming restore policy checks in Epic 3.
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
