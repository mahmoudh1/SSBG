---
stepsCompleted:
  - 1
  - 2
  - 3
  - 4
  - 5
  - 6
  - 7
  - 8
inputDocuments:
  - docs/SSBG_ARCHITECTURE.md
  - docs/PRD.md
  - _bmad-output/planning-artifacts/prd.md
workflowType: 'architecture'
project_name: 'SSBG'
user_name: '7egazy'
date: '2026-02-26'
lastStep: 8
status: 'complete'
completedAt: '2026-02-26'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**
The PRD defines 18 functional requirements spanning authentication, authorization, classification-aware policy evaluation, encryption before storage, per-backup key management, metadata persistence, MFA for sensitive operations, incident-level restore restrictions, integrity verification, time-limited restore access, tamper-evident auditing, alerting, incident-state management, crypto-shredding, key rotation, admin security APIs, and health/readiness endpoints.

Architecturally, this implies a security-centric backend with explicit component boundaries for auth, policy, crypto, metadata, audit, monitoring, incident orchestration, and admin operations. It also requires consistent enforcement points across backup, restore, alerting, and destruction workflows.

**Non-Functional Requirements:**
The PRD defines 10 NFRs emphasizing encryption/key-control assurance, tamper-detection effectiveness, fail-secure behavior, observability coverage, reproducible deployment, API responsiveness for control-plane operations, detection latency, error contract consistency, and demo-environment availability.

These NFRs directly shape architectural decisions for dependency boundaries, audit validation design, observability, API contract discipline, and deployment/runtime topology.

**Scale & Complexity:**
This is a high-complexity security platform MVP despite a compact deployment topology because core workflows combine cryptography, policy enforcement, tamper-evident auditing, and incident response.

- Primary domain: self-hosted security platform / backend API
- Complexity level: high
- Estimated architectural components: 10-14 logical components

### Technical Constraints & Dependencies

- Self-hosted, owner-controlled infrastructure (sovereign deployment model)
- Docker Compose-based MVP deployment
- Owner-controlled key lifecycle (generate/store/rotate/destroy)
- Fail-secure behavior when dependencies or controls are unavailable
- API-first MVP with stable contracts and documented error semantics
- High auditability and traceability expectations for security events
- Existing technical direction in `docs/SSBG_ARCHITECTURE.md` (FastAPI + PostgreSQL + MinIO)

### Cross-Cutting Concerns Identified

- Authentication and role-based authorization consistency across protected endpoints
- MFA enforcement for restore and crypto-shred workflows
- Shared policy evaluation before protected actions
- Incident-level restrictions affecting restore/admin behavior
- Tamper-evident audit logging and chain validation
- Monitoring and alert generation coupled to security events
- Encryption/key lifecycle integrity across backup/restore/rotation/destruction
- Fail-secure error handling during dependency outages
- Operational observability, health/readiness, and reproducibility

## Starter Template Evaluation

### Primary Technology Domain

API/backend security platform (self-hosted, Dockerized) based on PRD scope and existing architecture.

### Starter Options Considered

1. FastAPI official minimal setup (build custom project structure)
- Pros: Maximum control, minimal abstraction, easy alignment with security-specific architecture
- Cons: More manual setup work (testing, linting, migrations, folder layout)

2. `tiangolo/full-stack-fastapi-template`
- Pros: Maintained reference stack, batteries included, deployment patterns available
- Cons: Includes frontend and additional components beyond MVP scope, opinionated full-stack defaults not needed for API-only MVP

3. Community cookiecutter FastAPI templates
- Pros: Faster setup than manual scaffold
- Cons: Maintenance quality varies; may encode assumptions conflicting with SSBG security boundaries

### Selected Starter: Custom Minimal FastAPI Foundation

**Rationale for Selection:**
SSBG is an API-first security product with strict architectural boundaries and no MVP frontend. A custom FastAPI foundation avoids unnecessary full-stack assumptions while preserving clear control over crypto, audit, policy, and incident-response modules.

**Initialization Command:**

```bash
python -m venv .venv
. .venv/bin/activate  # Windows PowerShell: .\.venv\Scripts\Activate.ps1
pip install fastapi uvicorn[standard] sqlalchemy asyncpg alembic pydantic-settings boto3 cryptography pytest pytest-asyncio httpx ruff mypy
```

**Architectural Decisions Provided by Starter:**

**Language & Runtime:**
- Python 3.11.x runtime baseline
- FastAPI application entrypoint with generated OpenAPI

**Styling Solution:**
- Not applicable for MVP (API/CLI only)

**Build Tooling:**
- Python packaging + dependency pinning (exact lock mechanism deferred)
- Alembic for schema migrations

**Testing Framework:**
- `pytest` + `pytest-asyncio` for unit/integration testing
- `httpx` for API test client flows

**Code Organization:**
- Custom module-first backend structure (defined in Step 6)

**Development Experience:**
- FastAPI hot reload via Uvicorn in development
- Ruff + mypy for consistency and static checks

**Note:** Project initialization using this command is the first implementation story.

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- Runtime and framework: Python 3.11 + FastAPI
- Data stores: PostgreSQL (metadata/audit/policy state) + MinIO (encrypted objects)
- Crypto primitives and key lifecycle model (AES-256-GCM + ECC key wrapping + SHA-512 audit chaining)
- API contract pattern and error envelope
- Deployment topology (Docker Compose MVP)
- Module boundaries for auth/policy/crypto/audit/monitoring/incident handling

**Important Decisions (Shape Architecture):**
- Async DB access via SQLAlchemy 2.x + asyncpg
- Alembic migration workflow
- Structured logging and correlation IDs
- Rate limiting and security middleware placement
- Test organization and contract/integration test strategy

**Deferred Decisions (Post-MVP):**
- Web dashboard frontend stack
- Redis caching / queues
- Multi-site replication and secondary MinIO lineage
- External audit anchoring
- mTLS client authentication

### Data Architecture

- **Primary relational store:** PostgreSQL 16.x (metadata, policies, audit chain, alerts, incident state)
- **Object storage:** MinIO server (S3-compatible, encrypted payload objects and wrapped DEK artifacts)
- **ORM/data access:** SQLAlchemy 2.x (async engine/session) with repository boundary for persistence access
- **Driver:** `asyncpg` for PostgreSQL
- **Migrations:** Alembic migration scripts (versioned, reviewed, applied at startup only in controlled modes)
- **Caching:** No Redis in MVP; prefer deterministic DB queries and indexes first
- **Validation strategy:** Pydantic request/response schemas at API boundary; domain validation in service layer

### Authentication & Security

- **Authentication:** API key authentication for all protected endpoints (hashed at rest, revocation + expiry support)
- **MFA:** Required for restore and crypto-shred operations (MVP placeholder token validation per PRD scope)
- **Authorization:** RBAC + policy engine evaluation, classification-aware and incident-state-aware
- **Crypto model:** AES-256-GCM for payload encryption, ECC-based key wrapping using SECP384R1-compatible implementation, SHA-512 for checksums/hash chaining
- **Key custody:** Keys stored only in owner-controlled filesystem path mounted into gateway container
- **Security middleware:** Auth -> MFA (when required) -> authorization/policy -> handler orchestration
- **Fail-secure default:** dependency failures or unknown policy states return deny/quarantine behavior for protected operations

### API & Communication Patterns

- **External API style:** REST JSON under `/api/v1/*`
- **OpenAPI docs:** FastAPI-generated docs enabled in non-production; production exposure configurable
- **Error contract:** Stable error envelope with machine-readable code and human-readable message
- **Response pattern:** JSON object wrappers for non-trivial responses (`data`, `meta`, optional `error`)
- **Internal communication:** In-process module/service calls (monolithic gateway MVP), no distributed messaging in MVP
- **Rate limiting:** Application middleware / dependency layer with policy-aware thresholds for sensitive endpoints
- **Audit and monitoring hooks:** emitted from service layer events after business decision outcomes are finalized

### Frontend Architecture

- MVP is API/CLI only; no frontend starter selected.
- Future web dashboard remains a separate client app consuming existing REST contracts.

### Infrastructure & Deployment

- **Deployment:** Docker Compose (gateway + postgres + minio)
- **Gateway runtime:** Uvicorn serving FastAPI app in single service container (horizontal scaling deferred)
- **Configuration:** environment-variable based settings using `pydantic-settings`; `.env.example` maintained
- **Observability:** structured logs, health/readiness endpoints, audit/alert records in PostgreSQL
- **CI/CD (MVP baseline):** lint, type check, unit tests, integration tests, image build
- **Scaling strategy (MVP):** vertical scaling + hardening first, then selective extraction if needed post-MVP

### Version Verification Notes (Step 3/4)

The following versions were checked from official sources during this workflow and should be pinned or constrained during implementation setup:

- Python 3.11 documentation track: 3.11.13 docs currently published
- FastAPI latest release observed: 0.128.0
- PostgreSQL 16 documentation track: 16.11 docs currently published
- MinIO release notes latest entry observed: `RELEASE.2025-04-03T14-56-28Z`
- Docker Compose plugin: verify latest 2.x release at implementation time (GitHub releases; search result indicated 2.40.3)

### Decision Impact Analysis

**Implementation Sequence:**
1. Bootstrap repo and environment/config conventions
2. Define core domain models and DB schema migrations
3. Implement auth + RBAC + policy pipeline
4. Implement backup/restore orchestration with crypto boundary
5. Implement audit chain and monitoring/alerts
6. Implement incident state + crypto-shred controls
7. Add contract/integration/e2e-style API tests and hardening

**Cross-Component Dependencies:**
- Policy decisions depend on auth, MFA, incident state, and classification metadata
- Restore depends on metadata, object storage, key access, audit, and monitoring
- Crypto-shredding affects restore behavior and incident-state constraints
- Audit chain is cross-cutting and must be callable from all security-sensitive services

## Implementation Patterns & Consistency Rules

### Pattern Categories Defined

**Critical Conflict Points Identified:** 12+ areas where AI agents could make incompatible choices without explicit rules.

### Naming Patterns

**Database Naming Conventions:**
- Tables: `snake_case` plural (`api_keys`, `backup_metadata`, `audit_log_entries`)
- Columns: `snake_case` (`created_at`, `key_version_id`)
- Primary keys: `id` unless domain-specific ID is externally exposed
- Foreign keys: `<referenced_entity>_id`
- Indexes: `idx_<table>_<column[_column]>`
- Unique constraints: `uq_<table>_<column[_column]>`

**API Naming Conventions:**
- Endpoint paths: lowercase, kebab-free nouns with plural collections (e.g. `/api/v1/backups`, `/api/v1/admin/alerts`)
- Path params: `{backup_id}` style in docs; FastAPI variables use `backup_id`
- Query params and JSON fields: `snake_case`
- Headers: standard headers as-is; custom headers use existing PRD/architecture names (`X-API-Key`, `X-MFA-Token`)

**Code Naming Conventions:**
- Python modules/files: `snake_case.py`
- Classes: `PascalCase`
- Functions/variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Async functions that perform I/O may use verb-first names (`fetch_backup_metadata`, `write_audit_entry`)

### Structure Patterns

**Project Organization:**
- Organize by architectural capability/module (`auth`, `policy`, `crypto`, `backups`, `restores`, `audit`, `monitoring`, `incident`, `admin`)
- Shared infrastructure code lives in `app/core` and `app/infrastructure`
- API routers live in `app/api/routes`, grouped by feature domain
- Tests grouped by level (`tests/unit`, `tests/integration`, `tests/contracts`) and mirrored by module

**File Structure Patterns:**
- Settings/config in `app/core/config.py`
- Dependency injection wiring in `app/api/dependencies.py` and module-specific dependency helpers
- DB models separated from API schemas
- Alembic migrations only under `alembic/versions/`

### Format Patterns

**API Response Formats:**
- Success (resource/action): `{ "data": ..., "meta": {...} }` where metadata is useful
- Success (simple health): direct structured object allowed (`{ "status": "ok", ... }`)
- Error: `{ "error": { "code": "AUTH_INVALID", "message": "...", "details": {...}, "correlation_id": "..." } }`
- All timestamps in API payloads are ISO 8601 UTC strings (`YYYY-MM-DDTHH:MM:SSZ`)

**Data Exchange Formats:**
- JSON field names: `snake_case`
- Booleans: JSON `true` / `false`
- Nulls explicit when semantically meaningful; omit optional fields when absent by default
- Enumerations serialized as uppercase snake case (`CRYPTO_SHREDDED`, `LEVEL_3`)

### Communication Patterns

**Internal Event Patterns (In-Process):**
- Event names: `<domain>.<action>` (`backup.created`, `restore.denied`, `audit.validation_failed`)
- Event payloads include `event_id`, `occurred_at`, `actor_id` (if available), `correlation_id`, and domain-specific fields
- Service-layer events are domain facts; adapters convert them to audit entries or alerts

**State Management Patterns (Backend):**
- Transaction boundaries belong to application services, not API routers
- Repositories return domain entities/records; routers never query DB directly
- Incident level reads/writes go through a dedicated incident service
- Policy evaluation returns explicit allow/deny result objects, not booleans only

### Process Patterns

**Error Handling Patterns:**
- Domain errors raised as typed exceptions or result objects mapped centrally to API error envelope
- Security denials are auditable before returning API response (where safe and feasible)
- Dependency failures map to fail-secure responses (`503`/deny/quarantine depending on operation)
- Never leak key material, raw secrets, or stack traces in API responses

**Loading/Execution Patterns (Backend):**
- Request-level correlation ID generated or propagated at middleware
- Long-running backup/restore operations use explicit service orchestration steps with audit checkpoints
- Retry behavior only for idempotent infrastructure operations and must be bounded/logged

### Enforcement Guidelines

**All AI Agents MUST:**
- Follow the naming and response format patterns exactly
- Keep routers thin and enforce business rules in services/policy modules
- Write/update tests for any behavior change in touched modules
- Preserve fail-secure behavior when introducing new integrations
- Add audit hooks for new security-relevant actions

**Pattern Enforcement:**
- Ruff + mypy + test suite in CI
- PR review checklist references this architecture doc
- Pattern violations logged in code review and corrected before merge
- Any intentional deviation requires a documented architecture decision update

### Pattern Examples

**Good Examples:**
- `app/services/restore_service.py` calls `policy_service.evaluate_restore(...)` before object retrieval
- `POST /api/v1/backups` returns `{ "data": {"backup_id": "..."}, "meta": {"status": "accepted"} }`
- `idx_backup_metadata_created_at` for time-based restore/audit queries

**Anti-Patterns:**
- Router accessing SQLAlchemy session directly for core restore logic
- Mixed `camelCase` and `snake_case` JSON fields in the same API
- Writing plaintext payloads to temporary disk files outside approved secure flow
- Returning raw exception strings from crypto libraries to API clients

## Project Structure & Boundaries

### Complete Project Directory Structure

```text
ssbg/
+-- README.md
+-- .gitignore
+-- .env.example
+-- docker-compose.yml
+-- pyproject.toml
+-- alembic.ini
+-- docs/
¦   +-- PRD.md
¦   +-- SSBG_ARCHITECTURE.md
¦   +-- validation-report-2026-02-26.md
¦   +-- runbooks/
¦       +-- deployment.md
¦       +-- key-rotation.md
¦       +-- crypto-shred.md
+-- scripts/
¦   +-- dev_bootstrap.ps1
¦   +-- seed_demo_data.py
¦   +-- verify_audit_chain.py
+-- alembic/
¦   +-- env.py
¦   +-- script.py.mako
¦   +-- versions/
¦       +-- <timestamp>_initial_schema.py
+-- app/
¦   +-- main.py
¦   +-- api/
¦   ¦   +-- dependencies.py
¦   ¦   +-- error_handlers.py
¦   ¦   +-- middleware/
¦   ¦   ¦   +-- auth.py
¦   ¦   ¦   +-- correlation_id.py
¦   ¦   ¦   +-- rate_limit.py
¦   ¦   +-- routes/
¦   ¦       +-- health.py
¦   ¦       +-- backups.py
¦   ¦       +-- restores.py
¦   ¦       +-- audit.py
¦   ¦       +-- admin/
¦   ¦           +-- alerts.py
¦   ¦           +-- incident.py
¦   ¦           +-- keys.py
¦   ¦           +-- policies.py
¦   +-- core/
¦   ¦   +-- config.py
¦   ¦   +-- logging.py
¦   ¦   +-- enums.py
¦   ¦   +-- constants.py
¦   +-- domain/
¦   ¦   +-- auth/
¦   ¦   +-- backups/
¦   ¦   +-- restores/
¦   ¦   +-- policy/
¦   ¦   +-- audit/
¦   ¦   +-- monitoring/
¦   ¦   +-- incident/
¦   ¦   +-- keys/
¦   +-- services/
¦   ¦   +-- auth_service.py
¦   ¦   +-- backup_service.py
¦   ¦   +-- restore_service.py
¦   ¦   +-- policy_service.py
¦   ¦   +-- audit_service.py
¦   ¦   +-- monitoring_service.py
¦   ¦   +-- incident_service.py
¦   ¦   +-- key_management_service.py
¦   +-- schemas/
¦   ¦   +-- common.py
¦   ¦   +-- auth.py
¦   ¦   +-- backups.py
¦   ¦   +-- restores.py
¦   ¦   +-- audit.py
¦   ¦   +-- admin.py
¦   +-- repositories/
¦   ¦   +-- api_keys_repository.py
¦   ¦   +-- backups_repository.py
¦   ¦   +-- restores_repository.py
¦   ¦   +-- audit_repository.py
¦   ¦   +-- alerts_repository.py
¦   ¦   +-- incident_repository.py
¦   ¦   +-- key_versions_repository.py
¦   +-- infrastructure/
¦   ¦   +-- db/
¦   ¦   ¦   +-- base.py
¦   ¦   ¦   +-- session.py
¦   ¦   ¦   +-- models/
¦   ¦   ¦       +-- api_key.py
¦   ¦   ¦       +-- backup_metadata.py
¦   ¦   ¦       +-- restore_request.py
¦   ¦   ¦       +-- audit_log_entry.py
¦   ¦   ¦       +-- alert.py
¦   ¦   ¦       +-- incident_state.py
¦   ¦   ¦       +-- key_version.py
¦   ¦   +-- storage/
¦   ¦   ¦   +-- minio_client.py
¦   ¦   +-- crypto/
¦   ¦   ¦   +-- aes_gcm.py
¦   ¦   ¦   +-- ecies_wrapper.py
¦   ¦   ¦   +-- hashing.py
¦   ¦   ¦   +-- key_store_fs.py
¦   ¦   +-- observability/
¦   ¦       +-- metrics.py
¦   +-- workers/
¦       +-- (reserved_for_future_async_jobs)
+-- tests/
¦   +-- unit/
¦   ¦   +-- services/
¦   ¦   +-- policy/
¦   ¦   +-- crypto/
¦   +-- integration/
¦   ¦   +-- api/
¦   ¦   +-- repositories/
¦   ¦   +-- workflows/
¦   +-- contracts/
¦   ¦   +-- api_error_contracts/
¦   +-- fixtures/
¦   ¦   +-- keys/
¦   ¦   +-- payloads/
¦   ¦   +-- db_seed/
¦   +-- conftest.py
+-- ops/
    +-- compose/
    ¦   +-- docker-compose.dev.yml
    ¦   +-- docker-compose.prod.yml
    +-- postgres/
    +-- minio/
```

### Architectural Boundaries

**API Boundaries:**
- `app/api/routes/*` exposes only validated request/response schemas.
- Routers call services; they do not perform core crypto, policy, or persistence logic.
- Auth/MFA/rate-limit middleware and dependencies enforce entry controls before handlers.

**Component Boundaries:**
- `services/*` orchestrate use cases and transactions.
- `repositories/*` encapsulate persistence access.
- `infrastructure/*` encapsulates external systems and low-level adapters.
- `domain/*` holds business rules, enums, domain types, and policy logic primitives.

**Service Boundaries:**
- `policy_service` is a shared dependency for backup/restore/admin-sensitive operations.
- `audit_service` is callable from all security-sensitive workflows.
- `incident_service` is the source of truth for incident level transitions and restrictions.
- `key_management_service` owns key version lifecycle and crypto-shred side effects.

**Data Boundaries:**
- PostgreSQL stores metadata, policy state, alerts, and audit chain only.
- MinIO stores encrypted payloads and wrapped DEK artifacts; no plaintext backups.
- Filesystem-mounted key store contains owner-controlled key material only.

### Requirements to Structure Mapping

**Feature/FR Mapping:**
- Auth & RBAC (`FR-01`, `FR-02`, `FR-08`): `app/api/middleware/auth.py`, `app/services/auth_service.py`, `app/services/policy_service.py`, `app/repositories/api_keys_repository.py`
- Backup encryption flow (`FR-03` to `FR-07`): `app/api/routes/backups.py`, `app/services/backup_service.py`, `app/infrastructure/crypto/*`, `app/infrastructure/storage/minio_client.py`, `app/repositories/backups_repository.py`
- Restore flow + integrity + TTL (`FR-09` to `FR-11`): `app/api/routes/restores.py`, `app/services/restore_service.py`, `app/repositories/restores_repository.py`
- Audit validation (`FR-12`, `UJ-05`): `app/api/routes/audit.py`, `app/services/audit_service.py`, `app/repositories/audit_repository.py`, `scripts/verify_audit_chain.py`
- Monitoring + alerts + incident state (`FR-13`, `FR-14`): `app/services/monitoring_service.py`, `app/services/incident_service.py`, `app/api/routes/admin/alerts.py`, `app/api/routes/admin/incident.py`
- Crypto-shred + key lifecycle (`FR-15`, `FR-16`): `app/services/key_management_service.py`, `app/api/routes/admin/keys.py`, `app/repositories/key_versions_repository.py`
- Admin ops + readiness (`FR-17`, `FR-18`): `app/api/routes/admin/*`, `app/api/routes/health.py`

**Cross-Cutting Concerns:**
- Error contract consistency (`NFR-09`): `app/api/error_handlers.py`, `app/schemas/common.py`
- Fail-secure behavior (`NFR-06`): service layer + middleware + dependency adapters
- Observability (`NFR-10`): `app/core/logging.py`, `app/infrastructure/observability/metrics.py`, audit/alerts repositories
- Deployment reproducibility (`NFR-08`): `docker-compose.yml`, `ops/compose/*`, `docs/runbooks/*`

### Integration Points

**Internal Communication:**
- Request -> middleware/dependencies -> route -> service orchestration -> repositories/adapters -> audit/monitoring hooks -> response mapping

**External Integrations:**
- PostgreSQL via async SQLAlchemy/asyncpg
- MinIO (S3 API) via `boto3`/S3-compatible client wrapper
- Host filesystem key storage via secure file adapter

**Data Flow:**
- Backup: API -> auth/policy -> encryption -> MinIO write -> metadata DB -> audit -> alert checks
- Restore: API -> auth/MFA/policy/incident -> metadata fetch -> MinIO read -> key unwrap -> decrypt/integrity verify -> restore token -> audit/alerts
- Crypto-shred: API -> auth/MFA/confirm -> key destroy adapter -> key version + backup status updates -> incident level set -> audit

### File Organization Patterns

**Configuration Files:**
- Root-level deployment/config examples (`.env.example`, `docker-compose.yml`)
- Runtime settings in `app/core/config.py`
- Migration config in `alembic.ini`

**Source Organization:**
- API entry/adapters in `app/api`
- Business orchestration in `app/services`
- Persistence abstraction in `app/repositories`
- External adapters in `app/infrastructure`

**Test Organization:**
- Unit tests isolated by service/module
- Integration tests cover repositories and API workflows against test infra
- Contract tests lock error/status behavior required by PRD

**Asset Organization:**
- No frontend assets in MVP backend repo
- Test payload fixtures under `tests/fixtures/payloads`

### Development Workflow Integration

**Development Server Structure:**
- `app/main.py` boots FastAPI app and middleware wiring
- Docker Compose supports local postgres/minio dependencies

**Build Process Structure:**
- CI runs lint/type/test before image build
- Alembic migrations versioned and reviewed with code changes

**Deployment Structure:**
- Compose files and runbooks support repeatable self-hosted deployment and demo setup

## Architecture Validation Results

### Coherence Validation

**Decision Compatibility:** PASS
- The selected MVP architecture (Python/FastAPI + PostgreSQL + MinIO + Docker Compose) is internally coherent and aligns with the existing `docs/SSBG_ARCHITECTURE.md` technical direction.
- Monolithic gateway boundaries match the PRD's need for tight policy/crypto/audit coupling.
- Async API + relational metadata + object storage is a sensible split for the defined backup/restore workflows.

**Pattern Consistency:** PASS (with BMAD alignment additions)
- The newly defined naming, response, and layering patterns close gaps that could cause AI-agent divergence.
- Existing architecture doc is rich technically but did not previously define implementation consistency rules for AI agents.

**Structure Alignment:** PASS
- Proposed project structure supports all major capabilities and keeps security-critical boundaries explicit.
- Clear separation between API adapters, orchestration services, repositories, and infra adapters reduces accidental coupling.

### Requirements Coverage Validation

**Feature Coverage:** PASS
- All 18 FRs have architectural support in the chosen modules and boundaries.
- Cross-cutting requirements (auth, policy, audit, incident state, monitoring) are explicitly modeled as shared services.

**Functional Requirements Coverage:** PASS
- Backup/restore, crypto lifecycle, audit validation, incident controls, and admin APIs are all represented.
- Health/readiness and operational concerns are included in routing and deployment structure.

**Non-Functional Requirements Coverage:** PASS (MVP)
- Security, fail-secure behavior, observability, reproducibility, and contract consistency are architecturally supported.
- Performance and availability NFRs are addressed at architecture level but still require measurement/test plans during implementation.

### Implementation Readiness Validation

**Decision Completeness:** PASS
- Critical decisions are documented with rationale and impact.
- Deferred decisions are explicitly identified to prevent accidental scope creep.

**Structure Completeness:** PASS
- The project tree is concrete enough for AI agents to implement without inventing incompatible layouts.
- Integration points and ownership boundaries are defined.

**Pattern Completeness:** PASS
- Naming, structure, format, communication, and error-handling patterns are specified.
- Rules target likely AI-agent conflict points rather than over-prescribing internals.

### Gap Analysis Results

**Critical Gaps:**
- None blocking after this BMAD architecture document is created.

**Important Gaps (in `docs/SSBG_ARCHITECTURE.md` relative to BMAD format):**
- Missing BMAD workflow frontmatter and lifecycle state (not a BMAD workflow artifact)
- Missing explicit requirement-to-decision traceability matrix tied to PRD FR/NFR IDs
- Missing AI-agent consistency rules (naming/format/layering conventions)
- Missing a concrete implementation project tree and module ownership boundaries
- Missing explicit distinction between critical vs deferred decisions for implementation sequencing

**Nice-to-Have Gaps:**
- Convert major technology choices into ADR-style records for long-term change tracking
- Add version pin review table with refresh cadence to reduce documentation drift
- Add architecture-to-test strategy mapping (especially for crypto and audit tamper scenarios)

### Validation Issues Addressed

- Addressed BMAD alignment gap by producing `_bmad-output/planning-artifacts/architecture.md` as the canonical BMAD architecture workflow artifact.
- Preserved `docs/SSBG_ARCHITECTURE.md` as the detailed technical reference while adding BMAD-oriented decision, pattern, boundary, and validation layers.
- Reduced PRD/architecture drift risk by explicitly mapping FR/NFR areas to modules and boundaries.

### Architecture Completeness Checklist

**Requirements Analysis**
- [x] Project context thoroughly analyzed
- [x] Scale and complexity assessed
- [x] Technical constraints identified
- [x] Cross-cutting concerns mapped

**Architectural Decisions**
- [x] Critical decisions documented with rationale
- [x] Technology stack fully specified (MVP level)
- [x] Integration patterns defined
- [x] Security/fail-secure considerations addressed

**Implementation Patterns**
- [x] Naming conventions established
- [x] Structure patterns defined
- [x] Communication patterns specified
- [x] Error/process patterns documented

**Project Structure**
- [x] Complete directory structure defined
- [x] Component boundaries established
- [x] Integration points mapped
- [x] Requirements-to-structure mapping completed

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION (BMAD-aligned)

**Confidence Level:** High

**Key Strengths:**
- Strong PRD and technically mature reference architecture already existed
- Clear sovereign security model and crypto lifecycle boundaries
- BMAD alignment now adds implementation consistency and validation structure

**Areas for Future Enhancement:**
- ADR extraction for major design choices
- Formal performance/load test architecture validation
- Post-MVP frontend architecture document when dashboard work begins

### Implementation Handoff

**AI Agent Guidelines:**
- Follow the module boundaries and patterns in this document exactly.
- Treat `docs/SSBG_ARCHITECTURE.md` as detailed technical reference and this BMAD document as implementation governance.
- Preserve fail-secure behavior and auditability when implementing new functionality.
- Do not introduce frontend or distributed-system complexity into MVP stories unless architecture is updated.

**First Implementation Priority:**
Initialize the backend repository skeleton and Compose environment, then implement auth/policy pipeline and backup metadata schema as the first executable slice.

## Completion Summary & Handoff

Architecture workflow is complete. You now have a BMAD-aligned architecture artifact that:
- aligns to your PRD structure,
- preserves the technical depth of `docs/SSBG_ARCHITECTURE.md`,
- adds AI-agent consistency rules and project boundaries, and
- validates implementation readiness.

### Recommended Next BMAD Steps

1. Run implementation-readiness check (`IR`) after UX/epics are finalized (or to confirm current gaps formally).
2. Create epics/stories from the PRD if not already completed.
3. Start dev-story implementation with this architecture document as the source of truth.

I can also answer questions about any section of the architecture document or help convert your existing `docs/SSBG_ARCHITECTURE.md` into a BMAD-style structure directly if you want a single merged file later.
