# Story 5.1: Evaluate Monitoring Rules and Create Alerts

Status: done

## Story

As a security administrator,
I want suspicious behavior detection rules to generate alerts,
so that risky activity is surfaced quickly.

## Traceability

FR-13, UJ-03/UJ-04

## Acceptance Criteria

1. Given monitored events match configured suspicious patterns, when thresholds are crossed, then alert records are created with rule ID, severity, and timestamp.
2. Given no threshold breach occurs, when monitored events are processed, then no false alert is created for that rule.
3. Given an alert is created, when processing completes, then alert creation is auditable.

## Tasks / Subtasks

- [x] Implement monitoring rule evaluation service on restore/security event stream (AC: 1, 2)
- [x] Persist alert records with rule_id, severity, timestamp, and contextual metadata (AC: 1)
- [x] Avoid false positives where thresholds are not breached (AC: 2)
- [x] Emit audit event on alert creation (AC: 3)
- [x] Add tests for threshold crossing, non-crossing, and auditable alert creation (AC: 1, 2, 3)

## Dev Notes

### Scope

Detect suspicious activity by applying configurable rules to monitored events and creating alerts.

### Architecture Guardrails

- Rule evaluation should be deterministic and testable; avoid hidden state drift.
- Alert creation should be idempotent-safe for repeated event processing windows.
- Keep alert persistence in repositories/services, not route handlers.
- Audit alert creation consistently with existing tamper-evident pipeline.

### Likely Files

- app/services/monitoring_service.py
- app/repositories/alerts_repository.py
- app/infrastructure/db/models/alert.py
- app/services/audit_service.py
- tests/integration/workflows/test_monitoring_alert_creation.py

### Testing Requirements

- Threshold breach creates alert with expected fields
- No breach does not create false alert
- Alert creation is audited
- Rule evaluation handles repeated events safely

### Previous Story / Implementation Intelligence

- Uses restore/operation events from Epics 3 and audit foundation from Epic 4.
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
- Implemented alert persistence model/repository with rule/severity/status/timestamps, metadata, and dedupe key support.
- Added deterministic `MonitoringService` with threshold-based rule evaluation and idempotent-safe dedupe behavior by rule/actor/window bucket.
- Wired monitoring processing into restore restriction/failure outcomes via `RestoreService` using DI-provided monitoring service.
- Added auditable alert creation (`alert_created`) through existing tamper-evident audit pipeline.
- Added workflow tests for threshold breach creation, non-breach false-positive prevention, and repeated-event idempotency behavior.
- Validation passed: `python -m pytest tests/integration/workflows/test_monitoring_alert_creation.py`, `python -m ruff check ...`, `python -m mypy app tests/...`.

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
- `_bmad-output/implementation-artifacts/5-1-evaluate-monitoring-rules-and-create-alerts.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

## Change Log

- 2026-02-28: Implemented Story 5.1 monitoring rule evaluation, alert persistence, and auditable alert creation.
- 2026-02-28: Applied Epic 5 code-review remediation for migration completeness, deterministic incident-state retrieval, and window-consistent monitoring idempotency

