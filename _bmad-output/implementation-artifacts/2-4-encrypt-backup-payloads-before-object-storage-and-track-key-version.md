# Story 2.4: Encrypt Backup Payloads Before Object Storage and Track Key Version

Status: ready-for-dev

## Story

As a backup operator,
I want backup payloads encrypted before object-storage persistence,
so that stored data is unreadable without the correct key material.

## Traceability

FR-05, FR-06, UJ-02

## Acceptance Criteria

1. Given an allowed backup request, when backup persistence occurs, then the payload is encrypted before it is written to object storage.
2. Given encryption succeeds, when metadata is created, then a key-version identifier is stored for the backup.
3. Given encryption fails, when backup processing terminates, then the request returns failure and no successful backup status is recorded.

## Tasks / Subtasks

- [ ] Implement backup encryption workflow in backup_service using architecture crypto adapters (AC: 1, 2, 3)
- [ ] Persist ciphertext to MinIO/object storage only after successful encryption (AC: 1)
- [ ] Record key-version identifier in backup metadata creation path (AC: 2)
- [ ] Handle encryption/storage failures with fail-secure response and no false success state (AC: 3)
- [ ] Add tests for encryption success/failure and key-version tracking (AC: 1, 2, 3)

## Dev Notes

### Scope

Execute the crypto boundary for backup writes and key-version tracking. No plaintext persistence to object storage is allowed.

### Architecture Guardrails

- Use architecture crypto adapters and storage wrapper paths; avoid ad hoc crypto code in routes.
- Never write accepted backup plaintext to object storage or temporary insecure locations.
- Record key-version identifier on successful metadata creation for downstream restore/crypto-shred workflows.
- Failure paths must not mark backups successful without explicit lifecycle handling.

### Likely Files

- app/services/backup_service.py
- app/infrastructure/crypto/aes_gcm.py
- app/infrastructure/crypto/ecies_wrapper.py
- app/infrastructure/crypto/key_store_fs.py
- app/infrastructure/storage/minio_client.py
- app/repositories/backups_repository.py
- tests/unit/services/test_backup_encryption.py
- tests/integration/workflows/test_backup_encrypt_store.py

### Testing Requirements

- Ciphertext is written instead of plaintext to storage path
- Successful backup metadata includes key_version identifier
- Encryption failure returns failure and no successful backup status
- Storage failure does not produce false success outcome

### Previous Story / Implementation Intelligence

- Depends on Story 2.3 allow/deny policy gating. Reuse Epic 1 admin key/policy setup APIs and current key version provisioning patterns.
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
