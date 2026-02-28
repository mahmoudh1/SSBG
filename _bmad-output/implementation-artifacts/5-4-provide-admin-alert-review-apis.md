# Story 5.4: Provide Admin Alert Review APIs

Status: done

## Story

As a security administrator,
I want authorized APIs to review and acknowledge alerts,
so that I can manage incident response operations.

## Traceability

FR-17, UJ-04

## Acceptance Criteria

1. Given an authorized admin, when alert review endpoints are called, then alert data is returned in a consistent format.
2. Given alert acknowledgment or status updates are performed, when the action completes, then the change is persisted and auditable.
3. Given an unauthorized caller, when alert admin endpoints are called, then access is denied.

## Tasks / Subtasks

- [x] Implement authorized alert review/list endpoints and response schema (AC: 1, 3)
- [x] Implement alert acknowledgment/status update endpoints with persistence (AC: 2)
- [x] Audit alert review/update/acknowledge actions (AC: 2)
- [x] Enforce auth/RBAC for all alert admin endpoints (AC: 3)
- [x] Add tests for authorized review, update persistence, auditing, and unauthorized denial (AC: 1, 2, 3)

## Dev Notes

### Scope

Expose secure admin APIs for alert review and lifecycle management.

### Architecture Guardrails

- Reuse admin auth/RBAC dependencies and avoid route-local security shortcuts.
- Alert status updates should be explicit state transitions with clear allowed values.
- Audit all review/update actions for traceability.
- Keep response shape stable for operational tooling.

### Likely Files

- app/api/routes/admin/alerts.py
- app/services/monitoring_service.py
- app/repositories/alerts_repository.py
- app/services/audit_service.py
- app/schemas/admin.py
- tests/integration/api/test_admin_alert_review.py

### Testing Requirements

- Authorized admin can review alerts in consistent format
- Alert acknowledgment/status updates persist and are audited
- Unauthorized caller denied
- Response and error contracts remain consistent

### Previous Story / Implementation Intelligence

- Builds on Story 5.1 alert generation and Epic 1 admin auth/authorization.
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
- Implemented admin alert review endpoints: `GET /api/v1/admin/alerts` and `PUT /api/v1/admin/alerts/{alert_id}/status`.
- Added consistent alert response contract and explicit status update validation (`ALERT_STATUS_INVALID`, `ALERT_NOT_FOUND`).
- Reused admin RBAC guard (`require_permission('admin')`) for all alert admin operations with standard deny contract.
- Added audit events for alert review and status updates (`alert_reviewed`, `alert_status_updated`).
- Added integration tests for authorized alert review/update persistence and unauthorized denial paths.
- Validation passed: `python -m pytest ...alerts...`, `python -m ruff check ...`, `python -m mypy app tests/...`.

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
- `_bmad-output/implementation-artifacts/5-4-provide-admin-alert-review-apis.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

## Change Log

- 2026-02-28: Implemented Story 5.4 authorized admin alert review and status-update APIs with audit evidence.
- 2026-02-28: Applied Epic 5 code-review remediation for migration completeness, deterministic incident-state retrieval, and window-consistent monitoring idempotency

