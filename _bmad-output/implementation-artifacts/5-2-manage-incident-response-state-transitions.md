# Story 5.2: Manage Incident Response State Transitions

Status: done

## Story

As a incident responder,
I want to view and change incident response levels,
so that the system enforces the correct security posture.

## Traceability

FR-14, FR-17, UJ-04

## Acceptance Criteria

1. Given an authorized responder, when the current incident level is requested, then the system returns the current level and relevant metadata.
2. Given an authorized responder initiates an allowed transition, when the transition is applied, then the new incident level is persisted and audited.
3. Given an invalid or unauthorized transition request, when it is processed, then the system denies the request with a documented error response.

## Tasks / Subtasks

- [x] Implement incident level read/update APIs for authorized responders (AC: 1, 2)
- [x] Persist incident transitions with metadata and audit events (AC: 2)
- [x] Validate transition rules and deny invalid/unauthorized requests (AC: 3)
- [x] Add tests for read, valid transitions, invalid transitions, and authorization failures (AC: 1, 2, 3)

## Dev Notes

### Scope

Provide controlled incident-state management with authorization, validation, and auditability.

### Architecture Guardrails

- Use dedicated incident service/repository as source of truth.
- Authorization checks are mandatory before transitions.
- Transition rules should be explicit and test-covered (no implicit edge behavior).
- Every applied transition must produce audit evidence.

### Likely Files

- app/api/routes/admin/incident.py
- app/services/incident_service.py
- app/repositories/incident_repository.py
- app/services/audit_service.py
- tests/integration/api/test_incident_state_transitions.py

### Testing Requirements

- Authorized responder can read current incident level
- Allowed transition persists and is audited
- Invalid transition denied with documented error
- Unauthorized request denied

### Previous Story / Implementation Intelligence

- Builds on auth/RBAC from Epic 1 and restore-side incident enforcement baseline from Epic 3.
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

- Post-review fixes: added migration coverage for alert/incident tables, made incident latest-state retrieval deterministic, and hardened monitoring idempotency to dedupe within rule windows using persisted security-event counts.
- Ultimate context engine analysis completed - comprehensive developer guide created
- Story status set to ready-for-dev
- Implemented incident state persistence model/repository with transition metadata (`level`, `changed_by_key_id`, `reason`, `changed_at`).
- Added `IncidentService` transition engine with explicit allowed transitions and documented invalid-transition reasons.
- Implemented admin incident APIs (`GET /api/v1/admin/incident`, `PUT /api/v1/admin/incident`) with documented error contract for invalid transitions.
- Added audit evidence for incident state reads and successful level changes.
- Added integration tests for authorized read/update, invalid transition denial, and unauthorized RBAC denial.
- Validation passed: `python -m pytest ...incident...`, `python -m ruff check ...`, `python -m mypy app tests/...`.

## File List

- `app/api/dependencies.py`
- `app/api/routes/admin/alerts.py`
- `app/api/routes/admin/incident.py`
- `app/core/enums.py`
- `app/infrastructure/db/models/__init__.py`
- `app/infrastructure/db/models/alert.py`
- `app/infrastructure/db/models/incident_state.py`
- `app/repositories/alerts_repository.py`
- `app/repositories/incident_repository.py`
- `app/schemas/admin.py`
- `app/services/incident_service.py`
- `app/services/monitoring_service.py`
- `app/services/restore_service.py`
- `alembic/versions/20260228_0002_add_alerts_and_incident_state_tables.py`
- `tests/integration/workflows/test_monitoring_alert_creation.py`
- `tests/integration/api/test_incident_state_transitions.py`
- `tests/integration/api/test_restore_incident_enforcement_consistency.py`
- `tests/integration/api/test_admin_alert_review.py`
- `_bmad-output/implementation-artifacts/5-2-manage-incident-response-state-transitions.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

## Change Log

- 2026-02-28: Implemented Story 5.2 incident state transition management APIs with validation and auditability.
- 2026-02-28: Applied Epic 5 code-review remediation for migration completeness, deterministic incident-state retrieval, and window-consistent monitoring idempotency

