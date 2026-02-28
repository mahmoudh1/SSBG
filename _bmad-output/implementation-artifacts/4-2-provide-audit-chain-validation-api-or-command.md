# Story 4.2: Provide Audit Chain Validation API or Command

Status: done

## Story

As a auditor,
I want an audit validation capability,
so that I can detect whether any stored audit entries were modified.

## Traceability

FR-12, UJ-05

## Acceptance Criteria

1. Given valid audit chain data, when validation runs, then the system reports a valid machine-readable result.
2. Given a tampered audit entry in test scenarios, when validation runs, then the system reports invalid status and identifies the failure point or equivalent evidence.
3. Given validation completes, when results are returned, then the output format is documented and consistent.

## Tasks / Subtasks

- [x] Implement audit chain validator service and output schema (AC: 1, 3)
- [x] Expose validation capability via API endpoint and/or command-line script path (AC: 1, 2, 3)
- [x] Return machine-readable valid/invalid result including first-failure evidence pointer (AC: 2, 3)
- [x] Add tests for valid chain, tampered entry, and output consistency (AC: 1, 2, 3)

## Dev Notes

### Scope

Provide deterministic audit integrity verification capability for operators/auditors.

### Architecture Guardrails

- Validation logic should be deterministic and independent from live write path side effects.
- Machine-readable output must stay stable for operational automation and audits.
- Tamper detection should identify failure point or equivalent evidence without ambiguous output.
- Keep validation interfaces aligned between API and script if both are provided.

### Likely Files

- app/services/audit_service.py
- app/api/routes/audit.py
- scripts/verify_audit_chain.py
- app/schemas/audit.py
- tests/integration/api/test_audit_validation.py

### Testing Requirements

- Valid chain returns valid machine-readable result
- Tampered chain returns invalid with failure point/evidence
- Response/output format remains consistent
- Validation path does not mutate audit records

### Previous Story / Implementation Intelligence

- Builds on Story 4.1 chain fields and append behavior.
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

- Post-review fixes: added transactional rollback-safe audit append retries, persisted auth-failure deny events in chain, extended chain hash validation to include created_at, and removed fixed-chain validation window.
- Ultimate context engine analysis completed - comprehensive developer guide created
- Story status set to ready-for-dev
- Added `AuditChainValidationResult`/`AuditChainFailure` schemas for stable machine-readable validation output.
- Implemented deterministic chain validator in `AuditService` that detects sequence, link, and hash mismatches.
- Replaced audit validation placeholder route with real `/api/v1/audit/chain/validate` endpoint using shared response envelope.
- Added CLI validator script `scripts/verify_audit_chain.py` for operational command-line verification.
- Added API integration tests for valid-chain response, tamper detection with failure pointer, and non-mutating output consistency.
- Validation passed: `python -m pytest ...audit...`, `python -m ruff check ...`, `python -m mypy app tests/...`.

## File List

- `app/api/routes/audit.py`
- `app/infrastructure/db/models/audit_log_entry.py`
- `app/repositories/audit_repository.py`
- `app/schemas/audit.py`
- `app/services/audit_service.py`
- `scripts/verify_audit_chain.py`
- `tests/integration/api/test_audit_validation.py`
- `tests/integration/api/test_audit_review_authorization.py`
- `tests/integration/workflows/test_audit_chain_append.py`
- `alembic/versions/20260228_0001_add_audit_chain_fields.py`
- `_bmad-output/implementation-artifacts/4-2-provide-audit-chain-validation-api-or-command.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

## Change Log

- 2026-02-28: Implemented Story 4.2 audit chain validation API + script with deterministic tamper evidence output.
- 2026-02-28: Applied Epic 4 code-review remediation for retry rollback safety, deny-event chain coverage, created_at hash coverage, and full-chain validation scan

