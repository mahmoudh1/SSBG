# Epic 2: Submit and Persist Encrypted Backups

**Epic Goal:** Enable backup operators to submit backup payloads that are encrypted before storage and fully tracked in metadata and audit records.

**User Value:** Operators can store protected backups with verifiable metadata and audit evidence.

**Depends On:** Epic 1

## Story 2.1 Accept Backup Requests and Validate Base Request Contract

**User Story:** As a backup operator, I want the backup endpoint to validate request structure so malformed requests are rejected consistently.

**Traceability:** FR-04 (precondition for policy pipeline), FR-17 (operational API), UJ-02

**Dependencies:** Epic 1 complete

**Acceptance Criteria:**
- Given a malformed backup request, when it reaches the backup endpoint, then the API returns validation errors using the documented contract.
- Given a well-formed request, when validation passes, then processing continues to classification and policy evaluation.
- Given request validation fails, when the response is returned, then no backup object or metadata record is created.

## Story 2.2 Require and Persist Classification Metadata for Accepted Backups

**User Story:** As a security administrator, I want each accepted backup labeled with classification metadata so policy and audit workflows can enforce classification-aware behavior.

**Traceability:** FR-03, FR-07, UJ-02

**Dependencies:** Story 2.1

**Acceptance Criteria:**
- Given a backup request missing required classification, when policy/config requires classification, then the request is rejected or normalized according to documented rules.
- Given an accepted backup request, when metadata is persisted, then classification is stored and retrievable.
- Given later policy evaluation occurs, when restore logic reads metadata, then the stored classification is available for decisions.

## Story 2.3 Evaluate Policy Before Backup Execution

**User Story:** As a security administrator, I want policy decisions evaluated before backup execution so denied operations are blocked with explicit reasons.

**Traceability:** FR-04, UJ-02

**Dependencies:** Story 2.2, Epic 1 authorization stories

**Acceptance Criteria:**
- Given a protected backup request, when policy evaluation runs, then an explicit allow/deny result is produced.
- Given a denied policy result, when the request is rejected, then the API returns a documented error code and reason category.
- Given a policy result is produced, when processing continues or stops, then an audit event records the policy outcome.

## Story 2.4 Encrypt Backup Payloads Before Object Storage and Track Key Version

**User Story:** As a backup operator, I want backup payloads encrypted before object-storage persistence so stored data is unreadable without the correct key material.

**Traceability:** FR-05, FR-06, UJ-02

**Dependencies:** Story 2.3

**Acceptance Criteria:**
- Given an allowed backup request, when backup persistence occurs, then the payload is encrypted before it is written to object storage.
- Given encryption succeeds, when metadata is created, then a key-version identifier is stored for the backup.
- Given encryption fails, when backup processing terminates, then the request returns failure and no successful backup status is recorded.

## Story 2.5 Persist Backup Metadata, Lifecycle Status, and Audit Evidence

**User Story:** As an auditor or operator, I want backup metadata and lifecycle status recorded so backups can be tracked, restored, and reviewed later.

**Traceability:** FR-07, FR-12, UJ-02/UJ-05

**Dependencies:** Story 2.4

**Acceptance Criteria:**
- Given an accepted backup, when processing completes, then the API returns a stable backup identifier tied to persisted metadata.
- Given lifecycle state changes, when backup status transitions occur, then updated status values are stored.
- Given backup processing succeeds or fails at key checkpoints, when events occur, then audit entries are recorded for the operation.
