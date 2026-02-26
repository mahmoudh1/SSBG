# Story 3.2: Require MFA and Policy Authorization Before Restore Execution

Status: done

## Story

As a security administrator,
I want MFA and policy checks enforced before restore execution,
so that unauthorized restores are blocked.

## Traceability

FR-04, FR-08, UJ-03

## Acceptance Criteria

1. Given a restore request without MFA evidence, when restore authorization is evaluated, then the system denies the request.
2. Given an invalid MFA token, when validation runs, then the request is denied and the MFA outcome is auditable.
3. Given valid authentication/MFA and an allow policy result, when checks pass, then restore processing can proceed.

## Tasks / Subtasks

- [x] Implement restore-side MFA validation gate and request dependency path (AC: 1, 2, 3)
- [x] Compose restore authz/policy evaluation with existing auth/RBAC and policy service patterns (AC: 1, 3)
- [x] Audit MFA outcomes and restore policy outcomes (AC: 2, 3)
- [x] Return documented deny errors for missing/invalid MFA and policy deny cases (AC: 1, 2)
- [x] Add tests for missing MFA, invalid MFA, and allow path continuation (AC: 1, 2, 3)

## Dev Notes

### Scope

Enforce MFA + policy gating for restores before any data retrieval/decryption success path execution.

### Architecture Guardrails

- Follow architecture order: Auth -> MFA (when required) -> Authorization/Policy -> handler orchestration.
- MFA outcome must be auditable (success/failure) without leaking secrets/tokens.
- Do not bypass policy service with route-level special cases.
- Allow path should only hand off to later restore processing steps; no token issuance here.

### Likely Files

- app/api/dependencies.py
- app/services/auth_service.py
- app/services/policy_service.py
- app/services/restore_service.py
- app/api/routes/restores.py
- app/services/audit_service.py
- tests/integration/api/test_restore_mfa_policy.py

### Testing Requirements

- Missing MFA denied
- Invalid MFA denied and auditable
- Valid auth/MFA + allow policy proceeds
- Deny responses use documented error contract

### Previous Story / Implementation Intelligence

- Reuse Epic 1 authentication/RBAC and Epic 2 policy-result/audit patterns. Story 3.1 provides validated request + metadata loading entrypoint.
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

- Post-review fixes: enforced MFA before metadata existence checks, bound restore token use to issuing principal, added token-store expiry cleanup, and fail-secure handling for invalid metadata classification.
- Ultimate context engine analysis completed - comprehensive developer guide created
- Story status set to ready-for-dev
- Added MFA token validation path for restores with auditable allow/deny outcomes
- Added restore policy evaluation + audit recording before restore execution continuation
- Updated restore route error mapping for missing/invalid MFA and restore policy deny responses
- Added integration tests for missing MFA, invalid MFA, allow path continuation, and restore policy deny
- Validation passed: `python -m pytest tests/integration/api/test_restore_request_validation.py tests/integration/api/test_restore_mfa_policy.py`, `python -m ruff check ...`, `python -m mypy app tests/...`

## File List

- `app/api/dependencies.py`
- `app/api/routes/restores.py`
- `app/core/config.py`
- `app/core/enums.py`
- `app/infrastructure/crypto/key_store_fs.py`
- `app/schemas/restores.py`
- `app/services/audit_service.py`
- `app/services/auth_service.py`
- `app/services/incident_service.py`
- `app/services/policy_service.py`
- `app/services/restore_service.py`
- `app/services/restore_access_token_service.py`
- `tests/integration/api/test_restore_request_validation.py`
- `tests/integration/api/test_restore_mfa_policy.py`
- `tests/integration/api/test_restore_incident_restrictions.py`
- `tests/integration/workflows/test_restore_integrity.py`
- `tests/integration/api/test_restore_ttl_tokens.py`
- `_bmad-output/implementation-artifacts/3-2-require-mfa-and-policy-authorization-before-restore-execution.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

## Change Log

- 2026-02-26: Implemented Story 3.2 restore MFA + policy authorization gating and audit outcomes
- 2026-02-26: Applied code-review remediation for MFA ordering, token principal binding, metadata-classification fail-secure handling, and token-store expiry cleanup


