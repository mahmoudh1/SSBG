# Story 6.2: Execute Crypto-Shredding with Role, MFA, and Explicit Confirmation

Status: review

## Story

As a incident responder/super admin,
I want crypto-shredding to require privileged role, MFA, and explicit confirmation,
so that irreversible destruction cannot be triggered accidentally.

## Traceability

FR-04, FR-06, FR-08, FR-15, UJ-06

## Acceptance Criteria

1. Given a crypto-shred request missing privileged role, MFA, or confirmation input, when processed, then the request is denied.
2. Given a valid crypto-shred request, when execution completes, then the target key version is marked destroyed and affected backups are updated to irreversible status.
3. Given crypto-shredding succeeds, when future restore attempts target affected backups, then they fail with the documented irreversible error.
4. Given crypto-shredding executes, when the workflow completes, then start/completion audit events and incident-state effects are recorded.

## Tasks / Subtasks

- [x] Implement crypto-shred command flow with strict prechecks: role, MFA, explicit confirmation (AC: 1)
- [x] Mark target key version as destroyed and update affected backup lifecycle/status fields atomically where possible (AC: 2)
- [x] Enforce restore-deny behavior with irreversible error for affected backups (AC: 3)
- [x] Emit audit events for start, deny reasons, completion, and incident-state side effects (AC: 4)
- [x] Add tests for missing-factor denies, successful execution, irreversible restore failures, and audit trail completeness (AC: 1, 2, 3, 4)

## Dev Notes

### Scope

Deliver irreversible crypto-shred execution with multi-factor authorization and explicit confirmation safety controls.

### Architecture Guardrails

- Crypto-shred is irreversible: require all preconditions and explicit confirmation before execution.
- Use transaction-safe updates for key status + affected backup status transitions where supported.
- Restore checks must prioritize irreversible status and return documented error consistently.
- Audit start and completion separately; include deny-path events for failed prechecks.

### Likely Files

- app/services/key_management_service.py
- app/services/auth_service.py
- app/services/policy_service.py
- app/services/incident_service.py
- app/services/restore_service.py
- app/repositories/key_versions_repository.py
- app/repositories/backups_repository.py
- app/services/audit_service.py
- app/api/routes/admin/keys.py
- tests/integration/workflows/test_crypto_shred.py

### Testing Requirements

- Missing role/MFA/confirmation denies request
- Successful crypto-shred marks key destroyed and backups irreversible
- Subsequent restore attempts for affected backups return irreversible error
- Start/completion/deny audit events are recorded with incident effects

### Previous Story / Implementation Intelligence

- Depends on Story 6.1 key lifecycle foundation and incident/audit frameworks from Epics 4-5.
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
- Implemented crypto-shred command execution in `KeyManagementService` with strict prechecks for super-admin role, explicit confirmation, and MFA.
- Added key destruction + backup irreversible status update flow (`mark_destroyed`, `mark_irreversible_by_key_version`) with incident-effect escalation to lockdown.
- Added restore fail-fast behavior for shredded backups via `RestoreIrreversible` and API contract mapping (`RESTORE_IRREVERSIBLE`, HTTP 410).
- Added crypto-shred admin API endpoint at `/api/v1/admin/keys/versions/{version_id}/crypto-shred`.
- Added workflow and API tests covering denied prechecks, successful shred execution, irreversible restore failures, and documented response contracts.
- Validation passed: `python -m pytest ...`, `python -m ruff check ...`, `python -m mypy ...`.

## File List

- `app/services/key_management_service.py`
- `app/repositories/backups_repository.py`
- `app/services/restore_service.py`
- `app/api/routes/restores.py`
- `app/api/routes/admin/keys.py`
- `app/api/dependencies.py`
- `app/core/enums.py`
- `app/infrastructure/db/models/backup_metadata.py`
- `app/schemas/admin.py`
- `tests/integration/workflows/test_crypto_shred.py`
- `tests/integration/api/test_admin_crypto_shred.py`
- `tests/integration/api/test_restore_mfa_policy.py`
- `_bmad-output/implementation-artifacts/6-2-execute-crypto-shredding-with-role-mfa-and-explicit-confirmation.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

## Change Log

- 2026-02-28: Implemented Story 6.2 crypto-shred flow with role/MFA/confirmation prechecks, irreversible backup state propagation, and restore deny contract.
