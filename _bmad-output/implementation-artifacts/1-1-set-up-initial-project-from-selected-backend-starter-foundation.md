# Story 1.1: Set Up Initial Project from Selected Backend Starter Foundation

Status: done

## Story

As a platform developer,
I want the backend project initialized from the selected FastAPI foundation,
so that the team can implement features on a consistent base.

## Acceptance Criteria

1. Given an empty implementation repository, when the setup story is completed, then the backend project structure matches the architecture-defined layout and toolchain conventions.
2. Given the initialized project, when local checks run, then linting/type-checking/test commands execute successfully with baseline placeholders.
3. Given the generated configuration files, when a developer opens the project, then `.env.example` and Compose references exist for required services.

## Tasks / Subtasks

- [x] Scaffold root files and folders to match architecture layout (AC: 1, 3)
- [x] Add FastAPI app bootstrap in `app/main.py` and register placeholder routes (AC: 1)
- [x] Add config/settings scaffolding in `app/core/config.py` using `pydantic-settings` (AC: 1, 3)
- [x] Add DB/session + Alembic scaffolding (`app/infrastructure/db/*`, `alembic/*`) (AC: 1)
- [x] Configure `ruff`, `mypy`, `pytest`, `pytest-asyncio` in `pyproject.toml` (AC: 2)
- [x] Add baseline smoke test(s) and commands that pass locally (AC: 2)
- [x] Add Docker Compose references for gateway, PostgreSQL, MinIO and `.env.example` (AC: 3)

## Dev Notes

### Scope

Foundation only. Do not implement business logic for backup/restore/admin features beyond placeholders that keep imports/tests/tooling coherent.

### Architecture Guardrails

- Python runtime baseline: `3.11.x`
- Framework: FastAPI monolithic gateway MVP
- Keep module boundaries from architecture (`api`, `services`, `repositories`, `infrastructure`, `domain`, `schemas`)
- Use `/api/v1/*` route namespace
- Routers stay thin; future business logic goes in services
- Use async-ready DB setup (`SQLAlchemy 2.x` + `asyncpg`) to avoid rework

### File Targets (minimum scaffolding)

- `app/main.py`
- `app/core/config.py`
- `app/api/dependencies.py`
- `app/api/error_handlers.py`
- `app/api/routes/health.py`
- `app/api/routes/backups.py`
- `app/api/routes/restores.py`
- `app/api/routes/audit.py`
- `app/api/routes/admin/keys.py`
- `app/api/routes/admin/policies.py`
- `app/services/auth_service.py`
- `app/services/policy_service.py`
- `app/services/audit_service.py`
- `app/repositories/api_keys_repository.py`
- `app/infrastructure/db/session.py`
- `tests/conftest.py`

### Testing Requirements

- Add at least one passing smoke test (app import/startup)
- Baseline `ruff`, `mypy`, and `pytest` commands must run successfully
- Keep baseline tests independent of live infra unless explicitly documented

### Previous Story / Git Intelligence

- No previous implementation stories in Epic 1 (this is the first context file)
- No `.git` repository detected; git intelligence unavailable

### Latest Tech Information (researched 2026-02-26)

- Python 3.11 docs track shows `3.11.14`
- FastAPI PyPI latest observed: `0.133.1`
- SQLAlchemy PyPI latest observed: `2.0.47`
- Alembic PyPI latest observed: `1.18.4`
- Uvicorn PyPI latest observed: `0.41.0`
- Pydantic PyPI latest observed: `2.12.5`
- `pydantic-settings` PyPI latest observed: `2.13.1`
- PostgreSQL docs line: `16.12`
- Docker Compose GitHub releases show `v5.0.0` (major); verify compatibility before adopting
- MinIO release notes index shows newer 2025 releases than architecture snapshot; pin a tested image tag (no floating `latest`)

### References

- `_bmad-output/planning-artifacts/epics-and-stories/epic-1-provision-and-secure-the-ssbg-platform.md` (Story 1.1)
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/planning-artifacts/prd.md`
- `https://pypi.org/project/fastapi/`
- `https://pypi.org/project/SQLAlchemy/`
- `https://pypi.org/project/alembic/`
- `https://pypi.org/project/uvicorn/`
- `https://pypi.org/project/pydantic/`
- `https://pypi.org/project/pydantic-settings/`
- `https://docs.python.org/3.11/`
- `https://www.postgresql.org/docs/16/`
- `https://github.com/docker/compose/releases`
- `https://dl.minio.io/aistor/minio/release/notes/`

## Dev Agent Record

### Agent Model Used

GPT-5 (Codex)

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created
- Story status set to `ready-for-dev`
- Scaffolded architecture-aligned backend foundation (root files, app package boundaries, tests, ops, scripts, docs runbooks placeholders)
- Added FastAPI app bootstrap with `/api/v1/*` placeholder routers and centralized exception handler registration
- Added `pydantic-settings` configuration scaffold plus async SQLAlchemy session factory and Alembic baseline files
- Configured `ruff`, `mypy`, `pytest`, and `pytest-asyncio` in `pyproject.toml`
- Added smoke tests for app route registration and `/api/v1/health/live`
- Added Compose baseline services for gateway, PostgreSQL, and MinIO plus `.env.example`
- Updated sprint tracking to `in-progress` during execution and completed story with status `review`
- Local validation passed: `python -m pytest`, `python -m ruff check .`, `python -m mypy app tests`

### Debug Log

- 2026-02-26: Installed missing local tooling packages (`pytest`, `ruff`, `mypy`, `alembic`, `asyncpg`) to run required validation commands in this environment
- 2026-02-26: Fixed lint import ordering and missing type annotations discovered by validation runs
- 2026-02-26: Code review follow-up fixed Alembic runtime dependency gap by adding `psycopg` to `pyproject.toml`

## File List

- `.env.example`
- `.gitignore`
- `README.md`
- `alembic.ini`
- `docker-compose.yml`
- `pyproject.toml`
- `alembic/env.py`
- `alembic/script.py.mako`
- `alembic/versions/.gitkeep`
- `app/__init__.py`
- `app/main.py`
- `app/api/__init__.py`
- `app/api/dependencies.py`
- `app/api/error_handlers.py`
- `app/api/middleware/__init__.py`
- `app/api/middleware/auth.py`
- `app/api/middleware/correlation_id.py`
- `app/api/middleware/rate_limit.py`
- `app/api/routes/__init__.py`
- `app/api/routes/audit.py`
- `app/api/routes/backups.py`
- `app/api/routes/health.py`
- `app/api/routes/restores.py`
- `app/api/routes/admin/__init__.py`
- `app/api/routes/admin/alerts.py`
- `app/api/routes/admin/incident.py`
- `app/api/routes/admin/keys.py`
- `app/api/routes/admin/policies.py`
- `app/core/__init__.py`
- `app/core/config.py`
- `app/core/constants.py`
- `app/core/enums.py`
- `app/core/logging.py`
- `app/domain/__init__.py`
- `app/domain/auth/__init__.py`
- `app/domain/audit/__init__.py`
- `app/domain/backups/__init__.py`
- `app/domain/incident/__init__.py`
- `app/domain/keys/__init__.py`
- `app/domain/monitoring/__init__.py`
- `app/domain/policy/__init__.py`
- `app/domain/restores/__init__.py`
- `app/infrastructure/__init__.py`
- `app/infrastructure/crypto/__init__.py`
- `app/infrastructure/crypto/aes_gcm.py`
- `app/infrastructure/crypto/ecies_wrapper.py`
- `app/infrastructure/crypto/hashing.py`
- `app/infrastructure/crypto/key_store_fs.py`
- `app/infrastructure/db/__init__.py`
- `app/infrastructure/db/base.py`
- `app/infrastructure/db/session.py`
- `app/infrastructure/db/models/__init__.py`
- `app/infrastructure/db/models/alert.py`
- `app/infrastructure/db/models/api_key.py`
- `app/infrastructure/db/models/audit_log_entry.py`
- `app/infrastructure/db/models/backup_metadata.py`
- `app/infrastructure/db/models/incident_state.py`
- `app/infrastructure/db/models/key_version.py`
- `app/infrastructure/db/models/restore_request.py`
- `app/infrastructure/observability/__init__.py`
- `app/infrastructure/observability/metrics.py`
- `app/infrastructure/storage/__init__.py`
- `app/infrastructure/storage/minio_client.py`
- `app/repositories/__init__.py`
- `app/repositories/alerts_repository.py`
- `app/repositories/api_keys_repository.py`
- `app/repositories/audit_repository.py`
- `app/repositories/backups_repository.py`
- `app/repositories/incident_repository.py`
- `app/repositories/key_versions_repository.py`
- `app/repositories/restores_repository.py`
- `app/schemas/__init__.py`
- `app/schemas/admin.py`
- `app/schemas/audit.py`
- `app/schemas/auth.py`
- `app/schemas/backups.py`
- `app/schemas/common.py`
- `app/schemas/restores.py`
- `app/services/__init__.py`
- `app/services/audit_service.py`
- `app/services/auth_service.py`
- `app/services/backup_service.py`
- `app/services/incident_service.py`
- `app/services/key_management_service.py`
- `app/services/monitoring_service.py`
- `app/services/policy_service.py`
- `app/services/restore_service.py`
- `app/workers/(reserved_for_future_async_jobs)`
- `docs/runbooks/crypto-shred.md`
- `docs/runbooks/deployment.md`
- `docs/runbooks/key-rotation.md`
- `ops/compose/docker-compose.dev.yml`
- `ops/compose/docker-compose.prod.yml`
- `scripts/dev_bootstrap.ps1`
- `scripts/seed_demo_data.py`
- `scripts/verify_audit_chain.py`
- `tests/conftest.py`
- `tests/integration/api/test_health_smoke.py`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/1-1-set-up-initial-project-from-selected-backend-starter-foundation.md`

## Change Log

- 2026-02-26: Implemented Story 1.1 backend foundation scaffold (FastAPI bootstrap, settings, DB/Alembic scaffolding, tooling config, smoke tests, Compose/.env baseline)
- 2026-02-26: Code review fixes applied (Alembic `psycopg` dependency alignment)

## Senior Developer Review (AI)

### Review Date

2026-02-26

### Outcome

Approve

### Findings Addressed

- [x] Added missing `psycopg` dependency required by Alembic sync URL (`postgresql+psycopg`)

### Notes

- Story 1.1 reviewed with Epic 1 batch code review pass; no remaining HIGH/MEDIUM issues after validation rerun.
