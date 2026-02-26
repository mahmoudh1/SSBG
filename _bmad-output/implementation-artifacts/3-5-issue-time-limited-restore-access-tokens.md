# Story 3.5: Issue Time-Limited Restore Access Tokens

Status: ready-for-dev

## Story

As a restore requester,
I want successful restores to provide time-limited access,
so that restored data access is constrained.

## Traceability

FR-11, UJ-03

## Acceptance Criteria

1. Given a successful restore, when the response is returned, then it includes expiration metadata for the restore access mechanism.
2. Given a restore access token expires, when it is used, then access is denied.
3. Given TTL configuration is changed, when new restore tokens are issued, then expiration reflects the configured value.

## Tasks / Subtasks

- [ ] Implement restore access token issuance with explicit TTL and expiration metadata (AC: 1, 3)
- [ ] Expose token expiration metadata in restore success response contract (AC: 1)
- [ ] Validate token expiry on use and deny expired access (AC: 2)
- [ ] Read TTL from configuration and apply to newly issued tokens (AC: 3)
- [ ] Add tests for token issuance, expiry denial, and TTL config changes (AC: 1, 2, 3)

## Dev Notes

### Scope

Finalize restore response with constrained time-limited access after successful restore execution and integrity checks.

### Architecture Guardrails

- Only issue tokens after all prior restore gates pass (auth, MFA, policy, incident restrictions, decrypt/integrity).
- Token expiration must be explicit and configurable via central settings.
- Expired token use must deny access and avoid ambiguous partial success responses.
- Keep token mechanism and validation logic separate from route handlers for maintainability/testability.

### Likely Files

- app/services/restore_service.py
- app/core/config.py
- app/schemas/restores.py
- app/api/routes/restores.py
- app/services/auth_service.py
- tests/integration/api/test_restore_ttl_tokens.py

### Testing Requirements

- Successful restore response includes expiration metadata
- Expired token is denied on use
- Changing TTL config changes newly issued token expiration
- Token issuance does not bypass previous restore checks

### Previous Story / Implementation Intelligence

- Build on Story 3.4 successful restore execution and integrity verification. Reuse Epic 1 config/error patterns and Epic 2 metadata identifiers.
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
