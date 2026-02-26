# Story 1.2: Expose Health and Readiness Signals for Gateway and Dependencies

Status: done

## Story

As a platform administrator,
I want health and readiness endpoints,
so that I can verify service and dependency availability before operations.

## Acceptance Criteria

1. Given the gateway is running with healthy dependencies, when an authorized or public health check is requested (per design), then the API returns service status and dependency readiness details.
2. Given PostgreSQL or MinIO is unavailable, when readiness is requested, then the response indicates dependency failure without reporting a false healthy state.
3. Given health/readiness endpoints are called, when responses are returned, then the payload format is consistent with the API response/error contract.

## Tasks / Subtasks

- [x] Implement `/api/v1` health/readiness endpoints in `app/api/routes/health.py` (AC: 1, 2, 3)
- [x] Add dependency probes for PostgreSQL and MinIO via service/infrastructure helpers (AC: 1, 2)
- [x] Return contract-consistent success/error payloads (AC: 3)
- [x] Add tests for healthy and dependency-failure scenarios (AC: 1, 2, 3)

## Dev Notes

### Scope

Operational signals only. Do not couple this story to auth/policy feature behavior unless the design explicitly requires protected health endpoints.

### Architecture Guardrails

- Keep route handlers thin; probe logic belongs in service/helper layer
- Use `app/core/config.py` for dependency settings
- Readiness must not claim ready when PostgreSQL or MinIO is down (fail-clear / no false healthy state)
- Success payloads may be direct structured objects for simple health responses; errors must use shared error envelope
- Keep payload fields `snake_case`

### Likely Files

- `app/api/routes/health.py`
- `app/main.py`
- `app/core/config.py`
- `app/infrastructure/db/session.py`
- `app/infrastructure/storage/minio_client.py`
- `app/services/health_service.py` (recommended)
- `tests/integration/api/test_health.py`

### Testing Requirements

- Healthy gateway + dependencies returns healthy/ready status with dependency details
- PostgreSQL unavailable returns not-ready (no false-positive)
- MinIO unavailable returns not-ready (no false-positive)
- Unexpected errors map to shared error envelope
- Contract shape remains consistent across responses

### Previous Story / Git Intelligence

- Reuse Story 1.1 scaffolded paths and config patterns
- No `.git` repository detected; git intelligence unavailable

### Latest Tech Information (researched 2026-02-26)

- FastAPI PyPI latest observed: `0.133.1`
- Uvicorn PyPI latest observed: `0.41.0`
- SQLAlchemy PyPI latest observed: `2.0.47`
- Pydantic PyPI latest observed: `2.12.5`
- `pydantic-settings` PyPI latest observed: `2.13.1`
- PostgreSQL docs line: `16.12`

### References

- `_bmad-output/planning-artifacts/epics-and-stories/epic-1-provision-and-secure-the-ssbg-platform.md` (Story 1.2)
- `_bmad-output/planning-artifacts/prd.md` (`FR-18`, `UJ-01`)
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/implementation-artifacts/1-1-set-up-initial-project-from-selected-backend-starter-foundation.md`
- `https://pypi.org/project/fastapi/`
- `https://pypi.org/project/uvicorn/`
- `https://pypi.org/project/SQLAlchemy/`
- `https://pypi.org/project/pydantic/`
- `https://pypi.org/project/pydantic-settings/`
- `https://www.postgresql.org/docs/16/`
- `https://dl.minio.io/aistor/minio/release/notes/`

## Dev Agent Record

### Agent Model Used

GPT-5 (Codex)

### Completion Notes List

- Added health service with dependency probes for PostgreSQL and MinIO.
- Updated health endpoints to return envelope-style responses with request IDs.
- Added readiness tests for healthy and dependency-failure scenarios.
- Tests: `pytest`, `ruff`, `mypy`
- Code review fixes: added MinIO-not-ready and unexpected-error envelope tests; validated story/sprint tracking sync

## File List

- `app/api/routes/health.py`
- `app/services/health_service.py`
- `app/infrastructure/db/session.py`
- `app/infrastructure/storage/minio_client.py`
- `app/api/error_handlers.py`
- `tests/integration/api/test_health_smoke.py`
- `_bmad-output/implementation-artifacts/1-2-expose-health-and-readiness-signals-for-gateway-and-dependencies.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

## Change Log

- 2026-02-26: Implemented health/readiness endpoints, dependency probes, and baseline tests
- 2026-02-26: Code review fixes applied (MinIO failure coverage + unexpected error envelope test + tracking/documentation sync)

## Senior Developer Review (AI)

### Review Date

2026-02-26

### Outcome

Approve

### Findings Addressed

- [x] Added missing MinIO dependency-failure readiness test coverage
- [x] Added unexpected-error envelope test coverage for health endpoint path
- [x] Added missing File List and Change Log sections
- [x] Synced story/sprint statuses to terminal review state (`done`)
