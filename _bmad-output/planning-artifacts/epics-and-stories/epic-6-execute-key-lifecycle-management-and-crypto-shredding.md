# Epic 6: Execute Key Lifecycle Management and Crypto-Shredding

**Epic Goal:** Enable administrators to rotate key versions safely and execute irreversible crypto-shredding with strong authorization controls.

**User Value:** The organization can manage key lifecycle and perform verified irreversible destruction when required.

**Depends On:** Epics 1-5

## Story 6.1 Rotate Active Key Version Without Re-Encrypting Existing Backups

**User Story:** As a security administrator, I want to rotate the active key version so future backups use new key material while existing backups remain restorable.

**Traceability:** FR-16, UJ-01/UJ-06

**Dependencies:** Epic 2 backup key-version tracking, Epic 1 admin auth/authorization stories

**Acceptance Criteria:**
- Given a new key version is registered, when rotation is completed, then new backups use the new active key version.
- Given older backups reference previous non-destroyed key versions, when restore is attempted, then they remain restorable.
- Given key rotation occurs, when the operation completes, then an audit event is recorded.

## Story 6.2 Execute Crypto-Shredding with Role, MFA, and Explicit Confirmation

**User Story:** As an incident responder/super admin, I want crypto-shredding to require privileged role, MFA, and explicit confirmation so irreversible destruction cannot be triggered accidentally.

**Traceability:** FR-04, FR-06, FR-08, FR-15, UJ-06

**Dependencies:** Story 6.1, Epic 5 incident state management, Epic 4 audit foundations

**Acceptance Criteria:**
- Given a crypto-shred request missing privileged role, MFA, or confirmation input, when processed, then the request is denied.
- Given a valid crypto-shred request, when execution completes, then the target key version is marked destroyed and affected backups are updated to irreversible status.
- Given crypto-shredding succeeds, when future restore attempts target affected backups, then they fail with the documented irreversible error.
- Given crypto-shredding executes, when the workflow completes, then start/completion audit events and incident-state effects are recorded.

## Story 6.3 Provide Admin APIs for Key Lifecycle and Crypto-Shred Review

**User Story:** As a security administrator, I want authorized APIs to review key versions and destruction outcomes so I can manage and audit key lifecycle operations.

**Traceability:** FR-17, UJ-06

**Dependencies:** Story 6.1, Story 6.2, Epic 1 admin auth/authorization stories

**Acceptance Criteria:**
- Given an authorized admin, when key lifecycle endpoints are called, then key version metadata and statuses are returned without exposing sensitive key material.
- Given crypto-shred outcomes are queried, when results are returned, then affected scope and status information is available for review.
- Given an unauthorized caller, when key lifecycle admin endpoints are called, then access is denied.
