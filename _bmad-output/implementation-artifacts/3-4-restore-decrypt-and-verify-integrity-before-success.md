# Story 3.4: Restore, Decrypt, and Verify Integrity Before Success

Status: ready-for-dev

## Story

As a restore requester,
I want restored data integrity verified before success is returned,
so that I can trust recovered data.

## Traceability

FR-10, UJ-03

## Acceptance Criteria

1. Given a permitted restore request, when encrypted data is retrieved and decrypted, then the system validates integrity before returning success.
2. Given encrypted data or metadata integrity validation fails, when verification runs, then the restore fails with a documented integrity error and no success token is issued.
3. Given restore succeeds, when the operation completes, then an auditable completion event is recorded.

## Tasks / Subtasks

- [ ] Implement restore data retrieval + decrypt pipeline in restore_service using storage/crypto adapters (AC: 1, 2, 3)
- [ ] Validate integrity before success response/token issuance (AC: 1, 2)
- [ ] Return documented integrity error and block success on validation failure (AC: 2)
- [ ] Audit successful restore completion and integrity-failure outcomes (AC: 3)
- [ ] Add tests for successful decrypt/integrity pass and tamper/integrity-failure paths (AC: 1, 2, 3)

## Dev Notes

### Scope

Core restore execution: retrieve encrypted payload, decrypt, and verify integrity before any success response is finalized.

### Architecture Guardrails

- Reuse the same crypto/key-version metadata assumptions introduced in Epic 2 Story 2.4 and 2.5.
- Integrity verification must happen before success/token issuance.
- Do not leak plaintext or crypto internals in error responses.
- Fail-secure on missing key material, storage failures, or integrity mismatch.

### Likely Files

- app/services/restore_service.py
- app/infrastructure/storage/minio_client.py
- app/infrastructure/crypto/aes_gcm.py
- app/infrastructure/crypto/ecies_wrapper.py
- app/infrastructure/crypto/key_store_fs.py
- app/repositories/backups_repository.py
- app/services/audit_service.py
- tests/integration/workflows/test_restore_integrity.py

### Testing Requirements

- Permitted restore retrieves/decrypts and verifies integrity before success
- Integrity mismatch returns documented error and no success token
- Restore completion is audited on success
- Crypto/storage dependency failures are fail-secure

### Previous Story / Implementation Intelligence

- Depends on Epic 2 encrypted backup payloads, key-version tracking, and metadata persistence. Compose after Story 3.2/3.3 gates.
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
