# Story 5.3: Apply Incident-Level Restrictions Across Restore Workflows

Status: done

## Story

As a incident responder,
I want incident levels enforced in restore workflows,
so that the system automatically restricts risky operations.

## Traceability

FR-09, FR-14, UJ-03/UJ-04

## Acceptance Criteria

1. Given a restricted incident level is active, when a restore request is evaluated, then the system applies the documented restriction behavior.
2. Given incident level changes, when subsequent restore requests occur, then enforcement behavior reflects the latest persisted level.
3. Given restrictions are enforced, when outcomes are returned, then the reason is auditable and visible in the error/response contract.

## Tasks / Subtasks

- [x] Unify incident restriction enforcement across restore endpoints/workflows (AC: 1, 2, 3)
- [x] Ensure enforcement always uses latest persisted incident level (AC: 2)
- [x] Return documented contract with explicit restriction reason (AC: 3)
- [x] Audit restriction outcomes for observability and investigations (AC: 3)
- [x] Add tests for dynamic level changes and corresponding enforcement behavior (AC: 1, 2, 3)

## Dev Notes

### Scope

Ensure consistent, up-to-date incident restrictions across all restore workflow paths.

### Architecture Guardrails

- Do not duplicate incident enforcement logic in multiple routes; centralize in restore/incident services.
- Always fetch/use latest persisted incident level for each request.
- Restriction reasons must be explicit in response/audit outputs.
- Preserve fail-secure behavior for unknown/invalid incident state reads.

### Likely Files

- app/services/restore_service.py
- app/services/incident_service.py
- app/api/routes/restores.py
- app/services/audit_service.py
- tests/integration/api/test_restore_incident_enforcement_consistency.py

### Testing Requirements

- Restricted levels apply expected restore behavior
- Changing incident level updates subsequent request enforcement
- Restriction outcomes include auditable/visible reason
- Unknown incident state fails secure

### Previous Story / Implementation Intelligence

- Extends Epic 3 incident restriction behavior with full incident-state transition integration from Story 5.2.
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
- Unified restore incident enforcement around `IncidentService.get_current_level()` and preserved centralized restriction handling in `RestoreService`.
- Ensured each restore request uses latest persisted incident state via async incident service lookup.
- Added fail-secure behavior for unknown/invalid incident state reads, returning documented restriction reason `incident_state_unavailable`.
- Kept restriction outcomes visible in response contract (`RESTORE_RESTRICTED` + `reason_category`) and auditable through restore event entries.
- Added integration tests for dynamic incident-level changes across successive restore requests and unknown-state fail-secure behavior.
- Validation passed: `python -m pytest ...restore...`, `python -m ruff check ...`, `python -m mypy app tests/...`.

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
- `_bmad-output/implementation-artifacts/5-3-apply-incident-level-restrictions-across-restore-workflows.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

## Change Log

- 2026-02-28: Implemented Story 5.3 dynamic incident-level restore enforcement with fail-secure unknown-state handling.
- 2026-02-28: Applied Epic 5 code-review remediation for migration completeness, deterministic incident-state retrieval, and window-consistent monitoring idempotency

