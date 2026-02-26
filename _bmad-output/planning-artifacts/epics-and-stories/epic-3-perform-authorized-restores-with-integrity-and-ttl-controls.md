# Epic 3: Perform Authorized Restores with Integrity and TTL Controls

**Epic Goal:** Enable authorized users to request restores with MFA, incident-aware restrictions, integrity verification, and time-limited access.

**User Value:** Authorized data recovery is possible while preserving strict security controls.

**Depends On:** Epics 1-2

## Story 3.1 Accept Restore Requests and Load Backup Metadata

**User Story:** As a restore requester, I want the restore API to validate restore requests and load backup metadata so restore processing can begin safely.

**Traceability:** FR-07, FR-17, UJ-03

**Dependencies:** Epic 2 complete

**Acceptance Criteria:**
- Given an invalid restore request, when the API validates input, then it returns a documented validation error.
- Given a valid restore request, when metadata lookup runs, then the system loads the referenced backup metadata or returns a not-found error.
- Given metadata lookup fails, when the response is returned, then no restore token is issued.

## Story 3.2 Require MFA and Policy Authorization Before Restore Execution

**User Story:** As a security administrator, I want MFA and policy checks enforced before restore execution so unauthorized restores are blocked.

**Traceability:** FR-04, FR-08, UJ-03

**Dependencies:** Story 3.1, Epic 1 auth/authorization stories

**Acceptance Criteria:**
- Given a restore request without MFA evidence, when restore authorization is evaluated, then the system denies the request.
- Given an invalid MFA token, when validation runs, then the request is denied and the MFA outcome is auditable.
- Given valid authentication/MFA and an allow policy result, when checks pass, then restore processing can proceed.

## Story 3.3 Enforce Incident-Level Restore Restrictions

**User Story:** As an incident responder, I want restore behavior restricted by incident level so suspected abuse can be contained.

**Traceability:** FR-09, FR-14, UJ-03/UJ-04

**Dependencies:** Story 3.2

**Acceptance Criteria:**
- Given a restore request during a quarantine-level incident state, when the request is evaluated, then it is transitioned to the documented pending/manual-review behavior.
- Given the highest incident level is active, when a restore request is submitted, then restore completion is blocked.
- Given incident restrictions are applied, when the request outcome is returned, then the response and audit trail reflect the restriction reason.

**Implementation Note:** This story establishes restore-side incident restriction enforcement using the current incident-state source of truth. Epic 5 expands incident management and monitoring behaviors without changing the dependency direction.

## Story 3.4 Restore, Decrypt, and Verify Integrity Before Success

**User Story:** As a restore requester, I want restored data integrity verified before success is returned so I can trust recovered data.

**Traceability:** FR-10, UJ-03

**Dependencies:** Story 3.2 (and Story 3.3 if incident restrictions are in scope for the same slice)

**Acceptance Criteria:**
- Given a permitted restore request, when encrypted data is retrieved and decrypted, then the system validates integrity before returning success.
- Given encrypted data or metadata integrity validation fails, when verification runs, then the restore fails with a documented integrity error and no success token is issued.
- Given restore succeeds, when the operation completes, then an auditable completion event is recorded.

## Story 3.5 Issue Time-Limited Restore Access Tokens

**User Story:** As a restore requester, I want successful restores to provide time-limited access so restored data access is constrained.

**Traceability:** FR-11, UJ-03

**Dependencies:** Story 3.4

**Acceptance Criteria:**
- Given a successful restore, when the response is returned, then it includes expiration metadata for the restore access mechanism.
- Given a restore access token expires, when it is used, then access is denied.
- Given TTL configuration is changed, when new restore tokens are issued, then expiration reflects the configured value.
