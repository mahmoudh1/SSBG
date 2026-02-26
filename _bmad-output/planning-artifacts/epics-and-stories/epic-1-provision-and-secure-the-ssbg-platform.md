# Epic 1: Provision and Secure the SSBG Platform

**Epic Goal:** Enable a platform administrator to deploy a working SSBG instance, verify service health, and provision secure access for operators and admins.

**User Value:** A new deployment becomes operational and can safely accept authenticated requests.

**Depends On:** None

## Story 1.1 Set Up Initial Project from Selected Backend Starter Foundation

**User Story:** As a platform developer, I want the backend project initialized from the selected FastAPI foundation so the team can implement features on a consistent base.

**Traceability:** Architecture starter decision, implementation handoff first priority

**Dependencies:** None

**Acceptance Criteria:**
- Given an empty implementation repository, when the setup story is completed, then the backend project structure matches the architecture-defined layout and toolchain conventions.
- Given the initialized project, when local checks run, then linting/type-checking/test commands execute successfully with baseline placeholders.
- Given the generated configuration files, when a developer opens the project, then `.env.example` and Compose references exist for required services.

## Story 1.2 Expose Health and Readiness Signals for Gateway and Dependencies

**User Story:** As a platform administrator, I want health and readiness endpoints so I can verify service and dependency availability before operations.

**Traceability:** FR-18, UJ-01

**Dependencies:** Story 1.1

**Acceptance Criteria:**
- Given the gateway is running with healthy dependencies, when an authorized or public health check is requested (per design), then the API returns service status and dependency readiness details.
- Given PostgreSQL or MinIO is unavailable, when readiness is requested, then the response indicates dependency failure without reporting a false healthy state.
- Given health/readiness endpoints are called, when responses are returned, then the payload format is consistent with the API response/error contract.

## Story 1.3 Authenticate Protected API Requests Using Provisioned API Keys

**User Story:** As an operator or administrator, I want protected API requests authenticated so only valid credentials can access SSBG operations.

**Traceability:** FR-01, UJ-01/UJ-02/UJ-03/UJ-04/UJ-06

**Dependencies:** Story 1.1

**Acceptance Criteria:**
- Given a protected endpoint request without credentials, when the request is processed, then the API returns an authentication error and non-success HTTP status.
- Given an invalid, expired, or revoked API key, when a protected endpoint is called, then access is denied and an auditable failure event is generated.
- Given a valid API key, when a protected endpoint is called, then request processing continues to authorization/policy checks.

## Story 1.4 Enforce Role-Based Authorization for Protected Operations

**User Story:** As a security administrator, I want role-based authorization enforced so users can perform only the operations permitted by their role.

**Traceability:** FR-02, UJ-03/UJ-04/UJ-06

**Dependencies:** Story 1.3

**Acceptance Criteria:**
- Given a backup-only role, when restore or admin endpoints are requested, then the API denies the request and records an auditable deny event.
- Given a privileged role with required permissions, when permitted endpoints are requested, then authorization succeeds and processing continues.
- Given authorization decisions are evaluated, when responses are returned, then denied responses use the documented error contract.

## Story 1.5 Provide Initial Admin Security Management APIs (API Keys and Basic Policy Records)

**User Story:** As a security administrator, I want administrative APIs for basic security setup so I can provision keys and baseline policy data for operations.

**Traceability:** FR-17, UJ-01

**Dependencies:** Story 1.3, Story 1.4

**Acceptance Criteria:**
- Given an authorized admin, when API key management actions are performed, then the system persists and returns expected metadata without exposing raw secrets after creation.
- Given an unauthorized caller, when admin security endpoints are requested, then access is denied.
- Given admin security actions occur, when requests complete, then audit events are recorded.
